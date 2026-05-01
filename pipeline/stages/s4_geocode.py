from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from pipeline.core.llm_client import LLMClient
from pipeline.models import (
    EntityResult,
    GeocodedEntry,
    GeocodedResult,
    LocationLink,
    ResolvedLocation,
)

PROMPTS_DIR = Path(__file__).parent.parent / "config" / "prompts"


async def geocode_locations(entity_result: EntityResult, llm: LLMClient) -> GeocodedResult:
    """Stage 4: Resolve location names to coordinates."""
    prompt_template = (PROMPTS_DIR / "geocoding.txt").read_text()

    # Collect all unique location names
    all_names = set()
    for entry in entity_result.entries:
        all_names.update(entry.locations_mentioned)

    # Resolve each location
    resolved: dict[str, ResolvedLocation] = {}

    for name in all_names:
        context = f"Book: {entity_result.book_meta.title if entity_result.book_meta else 'unknown'}"
        prompt = prompt_template.format(name=name, context=context)
        try:
            raw = await llm.extract_json(prompt)
            data = json.loads(raw)
            loc = ResolvedLocation(
                name=name,
                ancient_name=data.get("ancient_name", name),
                modern_name=data.get("modern_name"),
                latitude=data.get("latitude", 0.0),
                longitude=data.get("longitude", 0.0),
                location_type=data.get("location_type"),
                confidence=data.get("confidence", 0.0),
                source="llm_inference",
            )
            if loc.confidence > 0:
                resolved[name] = loc
        except (json.JSONDecodeError, ValidationError, KeyError):
            pass

    # Build geocoded entries
    geocoded_entries = []
    for entry in entity_result.entries:
        links = []
        for i, loc_name in enumerate(entry.locations_mentioned):
            links.append(LocationLink(
                location_name=loc_name,
                resolved_location=resolved.get(loc_name),
                location_order=i,
            ))
        geocoded_entries.append(GeocodedEntry(
            segment_id=entry.segment_id,
            title=entry.title,
            original_text=entry.original_text,
            location_links=links,
        ))

    return GeocodedResult(
        entries=geocoded_entries,
        locations=list(resolved.values()),
    )
