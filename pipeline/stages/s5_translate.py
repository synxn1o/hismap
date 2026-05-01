from __future__ import annotations

from pathlib import Path

from pipeline.core.llm_client import LLMClient
from pipeline.models import GeocodedResult, TranslatedEntry, TranslatedResult

PROMPTS_DIR = Path(__file__).parent.parent / "config" / "prompts"


async def translate_entries(geocoded_result: GeocodedResult, llm: LLMClient) -> TranslatedResult:
    """Stage 5: Translate entries to English and modern Chinese."""
    prompt_template = (PROMPTS_DIR / "translation.txt").read_text()
    translated = []

    for entry in geocoded_result.entries:
        english = None
        modern = None

        # Detect source language heuristic
        has_chinese = any("一" <= c <= "鿿" for c in entry.original_text[:200])

        if has_chinese:
            # Chinese → English
            prompt = prompt_template.format(
                source_lang="Classical Chinese",
                target_lang="English",
                text=entry.original_text[:4000],
            )
            english = await llm.chat(prompt)
            # Also modern Chinese
            prompt_modern = prompt_template.format(
                source_lang="Classical Chinese",
                target_lang="Modern Chinese (白话文)",
                text=entry.original_text[:4000],
            )
            modern = await llm.chat(prompt_modern)
        else:
            # English/other → Chinese
            prompt = prompt_template.format(
                source_lang="English",
                target_lang="Modern Chinese",
                text=entry.original_text[:4000],
            )
            modern = await llm.chat(prompt)

        translated.append(TranslatedEntry(
            segment_id=entry.segment_id,
            title=entry.title,
            original_text=entry.original_text,
            location_links=entry.location_links,
            english_translation=english,
            modern_translation=modern,
            translation_source="ai",
        ))

    return TranslatedResult(entries=translated)
