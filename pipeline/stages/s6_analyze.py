from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from pipeline.core.llm_client import LLMClient
from pipeline.models import (
    AnalyzedEntry,
    AnalyzedResult,
    CredibilityReport,
    ScoredDimension,
    TranslatedResult,
)

PROMPTS_DIR = Path(__file__).parent.parent / "config" / "prompts"


def _parse_scored_dim(data: dict) -> ScoredDimension:
    return ScoredDimension(
        score=data.get("score", 0.5),
        evidence=data.get("evidence", ""),
        flags=data.get("flags", []),
    )


async def analyze_entries(translated_result: TranslatedResult, llm: LLMClient, book_title: str = "", author_name: str = "") -> AnalyzedResult:
    """Stage 6: Add context annotations and credibility analysis."""
    prompt_template = (PROMPTS_DIR / "credibility.txt").read_text()
    analyzed = []
    reports = []

    for entry in translated_result.entries:
        prompt = prompt_template.format(
            text=entry.original_text[:3000],
            book_title=book_title,
            author_name=author_name,
        )

        era = ""
        political = ""
        religious = ""
        social = ""
        report = None

        try:
            raw = await llm.extract_json(prompt)
            data = json.loads(raw)
            era = data.get("era_context", "")
            political = data.get("political_context", "")
            religious = data.get("religious_context", "")
            social = data.get("social_environment", "")

            cred = data.get("credibility", {})
            if cred:
                report = CredibilityReport(
                    segment_id=entry.segment_id,
                    overall_score=cred.get("overall_score", 0.5),
                    firsthand=cred.get("firsthand", False),
                    personal_experience=_parse_scored_dim(cred.get("personal_experience", {})),
                    accuracy=_parse_scored_dim(cred.get("accuracy", {})),
                    exaggeration=_parse_scored_dim(cred.get("exaggeration", {})),
                    fantasy_elements=_parse_scored_dim(cred.get("fantasy_elements", {})),
                    source_reliability=_parse_scored_dim(cred.get("source_reliability", {})),
                    cross_references=cred.get("cross_references", []),
                    scholarly_notes=cred.get("scholarly_notes", ""),
                )
                reports.append(report)
        except (json.JSONDecodeError, ValidationError):
            pass

        analyzed.append(AnalyzedEntry(
            segment_id=entry.segment_id,
            title=entry.title,
            original_text=entry.original_text,
            location_links=entry.location_links,
            english_translation=entry.english_translation,
            modern_translation=entry.modern_translation,
            translation_source=entry.translation_source,
            era_context=era,
            political_context=political,
            religious_context=religious,
            social_environment=social,
        ))

    return AnalyzedResult(entries=analyzed, credibility_reports=reports)
