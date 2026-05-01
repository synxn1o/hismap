from __future__ import annotations

import os
from pathlib import Path

import yaml
from openai import AsyncOpenAI

CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.yaml"


def load_config() -> dict:
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
        )
        self.model = llm_cfg["model"]
        self.max_tokens = llm_cfg.get("max_tokens", 4096)
        self.temperature = llm_cfg.get("temperature", 0.1)

    async def chat(self, prompt: str, system: str = "", max_tokens: int | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens or self.max_tokens,
            temperature=self.temperature,
        )
        return response.choices[0].message.content or ""

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
