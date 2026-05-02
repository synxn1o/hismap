"""Verification script: run pipeline step-by-step on a test book,
printing each stage's prompt and LLM output for manual inspection.

Usage:
    conda run -n hismap python pipeline/verify_pipeline.py [path_to_rtf]

Defaults to test_book/marco_polo_chs.rtf if no argument given.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.core.llm_client import LLMClient, load_config
from pipeline.stages.s1_ingest import ingest
from pipeline.stages.s2_segment import segment
from pipeline.stages.s3_extract import extract, build_context, load_prompt, get_extraction_tools
from pipeline.stages.book_summary import identify_preface, extract_book_summary
from pipeline.models import ExtractedStory


DIVIDER = "=" * 72
SUBDIVIDER = "-" * 72


def section(title: str):
    print(f"\n{DIVIDER}")
    print(f"  {title}")
    print(DIVIDER)


def subsection(title: str):
    print(f"\n  {SUBDIVIDER}")
    print(f"  {title}")
    print(f"  {SUBDIVIDER}")


def print_json(data, max_chars=2000):
    """Pretty-print JSON, truncating long values."""
    text = json.dumps(data, indent=2, ensure_ascii=False)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n  ... (truncated)"
    print(text)


async def main():
    file_path = sys.argv[1] if len(sys.argv) > 1 else "test_book/marco_polo_chs.rtf"
    file_path = str(Path(file_path).resolve())

    if not Path(file_path).exists():
        print(f"ERROR: File not found: {file_path}")
        sys.exit(1)

    config = load_config()
    llm = LLMClient(config)
    output_dir = "pipeline/output/verification"

    # ──────────────────────────────────────────────────────────────
    # STAGE 1: INGEST
    # ──────────────────────────────────────────────────────────────
    section("STAGE 1: INGEST")
    print(f"  Input: {file_path}")

    ingest_result = await ingest(file_path, config)

    print(f"  book_slug:    {ingest_result.book_slug}")
    print(f"  file_type:    {ingest_result.file_type}")
    print(f"  page_count:   {ingest_result.page_count}")
    print(f"  language:     {ingest_result.detected_language}")
    print(f"  raw_text:     {len(ingest_result.raw_text)} chars")
    print(f"  ocr_method:   {ingest_result.ocr_method}")

    subsection("First 500 chars of raw text:")
    print(ingest_result.raw_text[:500])

    # ──────────────────────────────────────────────────────────────
    # BOOK SUMMARY EXTRACTION
    # ──────────────────────────────────────────────────────────────
    section("BOOK SUMMARY: Identify preface + extract summary")

    preface_text, remaining = identify_preface(ingest_result.raw_text)
    if preface_text:
        print(f"  Preface found: {len(preface_text)} chars")
        subsection("Preface text (first 500 chars):")
        print(preface_text[:500])

        print("\n  Sending to LLM for summarization...")
        book_summary = await extract_book_summary(preface_text, llm)
        ingest_result.metadata["book_summary"] = book_summary

        subsection("Book summary result:")
        print(book_summary[:1000])
    else:
        print("  No preface detected — skipping book summary extraction")
        book_summary = None

    # ──────────────────────────────────────────────────────────────
    # STAGE 2: SEGMENT
    # ──────────────────────────────────────────────────────────────
    section("STAGE 2: SEGMENT")

    segment_result = await segment(ingest_result, output_dir=output_dir, llm=llm)
    print(f"  Segments produced: {len(segment_result.segments)}")

    for i, seg in enumerate(segment_result.segments):
        story_path = Path(seg.file_path)
        if story_path.exists():
            data = json.loads(story_path.read_text())
            print(f"\n  [{i+1}] {seg.id}")
            print(f"      title:            {data.get('title')}")
            print(f"      chapter_title:    {data.get('chapter_title')}")
            print(f"      is_content:       {data.get('is_content')}")
            print(f"      needs_subdivision:{data.get('needs_subdivision')}")
            print(f"      text length:      {len(data.get('original_text', ''))} chars")
            print(f"      text preview:     {data.get('original_text', '')[:120]}...")

    # ──────────────────────────────────────────────────────────────
    # STAGE 3: EXTRACT (show prompt + response for first 2 segments)
    # ──────────────────────────────────────────────────────────────
    section("STAGE 3: EXTRACT (showing first 2 segments in detail)")

    prompt_template = load_prompt("extraction_combined")

    # Collect known entities
    known_entities = []
    for seg_info in segment_result.segments:
        story_path = Path(seg_info.file_path)
        if story_path.exists():
            data = json.loads(story_path.read_text(encoding="utf-8"))
            s = ExtractedStory(**data)
            if s.entities:
                for loc in s.entities.get("locations", []):
                    if loc.get("name") and loc.get("lat") and loc.get("lng"):
                        known_entities.append(loc)

    shown = 0
    for seg_idx, seg_info in enumerate(segment_result.segments):
        story_path = Path(seg_info.file_path)
        if not story_path.exists():
            continue

        story_data = json.loads(story_path.read_text(encoding="utf-8"))
        story = ExtractedStory(**story_data)

        if story.extracted or not story.is_content:
            continue

        if shown >= 2:
            break
        shown += 1

        subsection(f"Segment [{seg_info.id}] — {story.title}")

        # Build context
        context = build_context(story, segment_result, seg_idx, known_entities, book_summary)

        print("\n  CONTEXT INJECTION:")
        print("  " + context.replace("\n", "\n  ")[:1500])

        prompt = prompt_template.format(context=context, text=story.original_text)

        subsection("FULL PROMPT sent to LLM:")
        print(f"  ({len(prompt)} chars)")
        print(prompt[:3000])
        if len(prompt) > 3000:
            print(f"\n  ... ({len(prompt) - 3000} more chars)")

        print("\n  Calling LLM...")
        try:
            raw = await llm.chat_with_tools(
                prompt=prompt,
                system="You are a historical text analysis expert.",
                tools=get_extraction_tools(config),
                response_format={"type": "json_object"},
                max_tokens=8192,
            )
        except Exception as e:
            print(f"  chat_with_tools failed ({e}), trying extract_json...")
            raw = await llm.extract_json(
                prompt=prompt,
                system="You are a historical text analysis expert. Be concise. Return ONLY valid JSON.",
                max_tokens=8192,
            )

        subsection("RAW LLM RESPONSE:")
        print(raw[:3000])
        if len(raw) > 3000:
            print(f"\n  ... ({len(raw) - 3000} more chars)")

        # Parse and show structured result
        try:
            # Clean markdown fences if present
            clean = raw
            if clean.startswith("```"):
                lines = clean.split("\n")
                lines = [l for l in lines if not l.startswith("```")]
                clean = "\n".join(lines)

            extracted = json.loads(clean)
            entries = extracted.get("entries", [])
            print(f"\n  PARSED: {len(entries)} entries")

            for j, entry in enumerate(entries):
                if entry.get("is_content", True):
                    subsection(f"Entry [{j}] — content entry:")
                    print(f"    story_metadata:     {json.dumps(entry.get('story_metadata'), ensure_ascii=False)}")
                    excerpt = entry.get("excerpt", {})
                    print(f"    excerpt.original:   {str(excerpt.get('original'))[:150]}")
                    print(f"    excerpt.translation:{str(excerpt.get('translation'))[:150]}")
                    summary = entry.get("summary", {})
                    print(f"    summary.chinese:    {str(summary.get('chinese'))[:150]}")
                    print(f"    summary.english:    {str(summary.get('english'))[:150]}")
                    entities = entry.get("entities", {})
                    print(f"    persons:            {entities.get('persons')}")
                    print(f"    dates:              {entities.get('dates')}")
                    print(f"    keywords:           {entities.get('keywords')}")
                    locs = entities.get("locations", [])
                    if locs:
                        print(f"    locations ({len(locs)}):")
                        for loc in locs[:5]:
                            print(f"      - {loc.get('name')} ({loc.get('lat')}, {loc.get('lng')}) {loc.get('location_type')}")
                    cred = entry.get("credibility", {})
                    print(f"    credibility.score:  {cred.get('credibility_score')}")
                    print(f"    credibility.era:    {str(cred.get('era_context'))[:100]}")
                else:
                    print(f"\n  Entry [{j}] — non-content (is_content=false)")

        except json.JSONDecodeError as e:
            print(f"\n  JSON parse error: {e}")

    # Now run the actual extract for all segments
    print(f"\n{DIVIDER}")
    print("  Running full S3 extract on all segments...")
    print(DIVIDER)

    extract_stats = await extract(segment_result, llm, book_summary=book_summary, known_entities=known_entities)

    print(f"\n  Results: processed={extract_stats['processed']}, skipped={extract_stats['skipped']}, failed={extract_stats['failed']}")

    # ──────────────────────────────────────────────────────────────
    # SUMMARY: Show all extracted entries
    # ──────────────────────────────────────────────────────────────
    section("EXTRACTION SUMMARY — All entries")

    for seg_info in segment_result.segments:
        story_path = Path(seg_info.file_path)
        if not story_path.exists():
            continue
        data = json.loads(story_path.read_text())
        if not data.get("is_content"):
            continue
        if not data.get("extracted"):
            continue

        print(f"\n  [{seg_info.id}] {data.get('title')}")
        print(f"    excerpt:    {str(data.get('excerpt_original'))[:120]}")
        print(f"    summary_zh: {str(data.get('summary_chinese'))[:120]}")
        print(f"    summary_en: {str(data.get('summary_english'))[:120]}")
        print(f"    persons:    {data.get('persons')}")
        locs = (data.get("entities") or {}).get("locations", [])
        if locs:
            print(f"    locations:  {[l['name'] for l in locs[:5]]}")

    print(f"\n{DIVIDER}")
    print("  Verification complete.")
    print(f"  Output files in: {output_dir}/")
    print(DIVIDER)


if __name__ == "__main__":
    asyncio.run(main())
