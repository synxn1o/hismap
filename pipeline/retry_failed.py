"""Retry failed LLM extractions.

Scans an output directory for story JSON files where is_content=true
and error is not null, then re-runs the extraction pipeline on those files.

Usage:
    python -m pipeline.retry_failed [output_dir]

    output_dir: path to directory containing story JSON files
                default: pipeline/output/marco_polo_chs/
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from pipeline.core.llm_client import LLMClient, load_config
from pipeline.models import ExtractedStory, SegmentInfo, SegmentResultV2
from pipeline.stages.s3_extract import (
    _extract_single,
    _normalize_story_data,
    load_prompt,
)


def find_failed(output_dir: Path) -> list[tuple[Path, ExtractedStory]]:
    """Find story files where is_content=true and error is not null."""
    failed = []
    for p in sorted(output_dir.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if data.get("is_content") and data.get("error"):
                _normalize_story_data(data)
                story = ExtractedStory(**data)
                failed.append((p, story))
        except Exception as e:
            print(f"  [warn] skipping {p.name}: {e}")
    return failed


def build_segment_result(output_dir: Path) -> tuple[SegmentResultV2, list[dict]]:
    """Build SegmentResultV2 and known_entities from all files in the directory."""
    segments = []
    known_entities = []
    book_slug = ""
    language = ""

    for p in sorted(output_dir.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            _normalize_story_data(data)
            story = ExtractedStory(**data)
            if not book_slug:
                book_slug = story.book_slug
                language = story.language
            segments.append(SegmentInfo(
                id=story.id,
                title=story.title,
                file_path=str(p),
                original_text_preview=story.original_text[:200],
            ))
            # Collect known entities from already-extracted stories
            if data.get("entities"):
                for loc in data["entities"].get("locations", []):
                    if loc.get("name") and loc.get("lat") and loc.get("lng"):
                        known_entities.append(loc)
        except Exception:
            pass

    return SegmentResultV2(
        book_slug=book_slug,
        language=language,
        segments=segments,
    ), known_entities


async def retry_failed(output_dir: str | None = None) -> dict:
    """Retry extraction on all failed story files.

    Returns stats dict with processed/skipped/failed counts.
    """
    if output_dir is None:
        output_dir = str(Path(__file__).parent / "output" / "marco_polo_chs")
    out = Path(output_dir)

    if not out.exists():
        print(f"Directory not found: {out}")
        return {"processed": 0, "skipped": 0, "failed": 0}

    failed = find_failed(out)
    if not failed:
        print("No failed extractions found (is_content=true, error!=null).")
        return {"processed": 0, "skipped": 0, "failed": 0}

    print(f"Found {len(failed)} failed extraction(s):")
    for p, story in failed:
        print(f"  {p.name}: {(story.error or '')[:80]}")

    config = load_config()
    llm = LLMClient(config)
    prompt_template = load_prompt("extraction_combined")
    segment_result, known_entities = build_segment_result(out)

    # Build index of segment_index for each failed file
    seg_index_map = {s.file_path: i for i, s in enumerate(segment_result.segments)}

    stats = {"processed": 0, "skipped": 0, "failed": 0}

    for story_path, story in failed:
        seg_idx: int = seg_index_map.get(str(story_path), 0)
        print(f"\n  Retrying {story_path.name}...", end=" ", flush=True)

        # Reset extraction state
        story.extracted = False
        story.error = None

        ok = await _extract_single(
            story=story,
            story_path=story_path,
            seg_info=segment_result.segments[seg_idx],
            seg_idx=seg_idx,
            segment_result=segment_result,
            llm=llm,
            prompt_template=prompt_template,
            known_entities=known_entities,
            book_summary=None,
            config=config,
        )
        if ok:
            stats["processed"] += 1
        else:
            stats["failed"] += 1

    print(f"\n\nRetry complete: {stats['processed']} recovered, {stats['failed']} still failing")
    return stats


def main():
    output_dir = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(retry_failed(output_dir))


if __name__ == "__main__":
    main()
