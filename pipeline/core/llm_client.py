from __future__ import annotations

import asyncio
import os
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv
from openai import AsyncOpenAI

CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.yaml"
ENV_PATH = Path(__file__).parent.parent / ".env"


def load_config() -> dict:
    # Load .env file if it exists
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH, override=True)
    with open(CONFIG_PATH) as f:
        raw = f.read()
    # Expand env vars
    for key, val in os.environ.items():
        raw = raw.replace(f"${{{key}}}", val)
    return yaml.safe_load(raw)


class LLMClient:
    def __init__(self, config: dict | None = None):
        if config is None:
            config = load_config()
        llm_cfg = config["llm"]
        self.client = AsyncOpenAI(
            base_url=llm_cfg["base_url"],
            api_key=llm_cfg["api_key"],
            timeout=httpx.Timeout(120.0, connect=30.0),
        )
        self.model = llm_cfg["model"]
        self.max_tokens = llm_cfg.get("max_tokens", 4096)
        self.temperature = llm_cfg.get("temperature", 0.1)

    async def chat(self, prompt: str, system: str = "", max_tokens: int | None = None, retries: int = 3) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async def _call():
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens or self.max_tokens,
                temperature=self.temperature,
            )
            return response.choices[0].message.content or ""

        for attempt in range(retries):
            try:
                return await asyncio.wait_for(_call(), timeout=90.0)
            except (asyncio.TimeoutError, Exception) as e:
                if attempt == retries - 1:
                    raise
                print(f"  [retry {attempt+1}/{retries}] {type(e).__name__}, retrying...", flush=True)
                await asyncio.sleep(2)
        return ""

    async def chat_with_tools(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
        response_format: dict | None = None,
        retries: int = 3,
    ) -> str:
        """Chat with optional tool use and JSON response format."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # Auto-set JSON response format when tools are provided
        if tools and response_format is None:
            response_format = {"type": "json_object"}

        async def _call():
            kwargs = dict(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens or self.max_tokens,
                temperature=self.temperature,
            )
            if tools:
                kwargs["tools"] = tools
            if response_format:
                kwargs["response_format"] = response_format
            response = await self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""

        for attempt in range(retries):
            try:
                return await asyncio.wait_for(_call(), timeout=120.0)
            except (asyncio.TimeoutError, Exception) as e:
                if attempt == retries - 1:
                    raise
                print(f"  [retry {attempt+1}/{retries}] {type(e).__name__}, retrying...", flush=True)
                await asyncio.sleep(2)
        return ""

    async def extract_json(self, prompt: str, system: str = "") -> str:
        """Chat and extract JSON from response, stripping markdown fences."""
        raw = await self.chat(prompt, system)
        # Strip markdown code fences
        if raw.startswith("```"):
            lines = raw.split("\n")
            # Remove first and last lines (fences)
            lines = [l for l in lines if not l.startswith("```")]
            raw = "\n".join(lines)
        return raw.strip()
