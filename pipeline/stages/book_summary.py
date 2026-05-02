from __future__ import annotations

import json
import re
from pathlib import Path

from pipeline.core.llm_client import LLMClient

PROMPTS_DIR = Path(__file__).parent.parent / "config" / "prompts"

PREFACE_KEYWORDS = [
    "序言", "前言", "自序", "代序", "Preface", "Foreword", "Introduction",
    "preface", "foreword", "introduction", "PROLOGUE", "Prologue",
]


def identify_preface(text: str) -> tuple[str, str]:
    """Split text into preface and remaining content.

    Returns (preface_text, remaining_text). If no preface found, returns ("", text).
    """
    lines = text.split("\n")
    preface_end = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if any(kw.lower() in stripped.lower() for kw in PREFACE_KEYWORDS):
            # Found preface marker, collect until next chapter-like heading
            for j in range(i + 1, len(lines)):
                next_line = lines[j].strip()
                # Stop at chapter markers
                if re.match(r'^(第[一二三四五六七八九十\d]+[章节篇]|Chapter\s+\d+|[IVX]+\.)', next_line):
                    preface_end = j
                    break
            if preface_end == 0:
                # No chapter marker found, take up to 2000 chars
                preface_end = min(i + 50, len(lines))
            break

    if preface_end == 0:
        return "", text

    preface = "\n".join(lines[:preface_end]).strip()
    remaining = "\n".join(lines[preface_end:]).strip()
    return preface, remaining


async def extract_book_summary(preface_text: str, llm: LLMClient) -> str:
    """Extract a book summary from preface text using LLM.

    Returns a plain text summary string.
    """
    prompt_template = (PROMPTS_DIR / "book_summary.txt").read_text()
    prompt = prompt_template.format(text=preface_text)

    try:
        raw = await llm.extract_json(
            prompt=prompt,
            system="You are a literary analysis expert. Be concise. Return ONLY valid JSON.",
            max_tokens=2048,
        )
        data = json.loads(raw)
        return data.get("summary", preface_text[:500])
    except Exception:
        # Fallback: return first 500 chars of preface
        return preface_text[:500]
