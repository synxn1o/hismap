from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from pipeline.core.llm_client import LLMClient
from pipeline.models import (
    BookMeta,
    AuthorMeta,
    EntityResult,
    ExtractedEntry,
    SegmentResult,
)

PROMPTS_DIR = Path(__file__).parent.parent / "config" / "prompts"


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.txt").read_text()


async def extract_entities(segment_result: SegmentResult, llm: LLMClient) -> EntityResult:
    """Stage 3: Extract entities from text segments using LLM."""
    entries = []
    book_meta = None
    author_meta = None

    # First pass: try to extract book/author metadata from first segment
    if segment_result.segments:
        first = segment_result.segments[0]
        meta_prompt = f"""Analyze this text and extract book/author metadata.

TEXT (first 2000 chars):
{first.text[:2000]}

Return JSON:
{{
  "book": {{
    "title": "book title",
    "author": "author name or null",
    "dynasty": "dynasty/era or null",
    "era_start": null,
    "era_end": null
  }},
  "author": {{
    "name": "author name",
    "dynasty": "dynasty or null",
    "birth_year": null,
    "death_year": null,
    "biography": "brief bio or null"
  }}
}}

Return ONLY valid JSON."""

        try:
            raw = await llm.extract_json(meta_prompt)
            data = json.loads(raw)
            if data.get("book"):
                book_meta = BookMeta(**data["book"])
            if data.get("author"):
                author_meta = AuthorMeta(**data["author"])
        except (json.JSONDecodeError, ValidationError):
            pass

    # Extract entries from each segment
    prompt_template = load_prompt("extraction")

    for seg in segment_result.segments:
        prompt = prompt_template.format(text=seg.text[:4000])
        try:
            raw = await llm.extract_json(prompt)
            data = json.loads(raw)
            entry = ExtractedEntry(
                segment_id=seg.segment_id,
                title=data.get("title", seg.heading or f"Segment {seg.segment_id}"),
                original_text=seg.text,
                locations_mentioned=data.get("locations_mentioned", []),
                dates_mentioned=data.get("dates_mentioned", []),
                persons_mentioned=data.get("persons_mentioned", []),
                keywords=data.get("keywords", []),
                visit_date_approximate=data.get("visit_date_approximate"),
            )
            entries.append(entry)
        except (json.JSONDecodeError, ValidationError) as e:
            # Create entry with raw text on failure
            entries.append(ExtractedEntry(
                segment_id=seg.segment_id,
                title=seg.heading or f"Segment {seg.segment_id}",
                original_text=seg.text,
                locations_mentioned=[],
                dates_mentioned=[],
                persons_mentioned=[],
                keywords=[],
            ))

    return EntityResult(
        book_meta=book_meta,
        author_meta=author_meta,
        entries=entries,
    )
