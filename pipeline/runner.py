from __future__ import annotations

import json
from pathlib import Path

from pipeline.core.llm_client import LLMClient
from pipeline.models import IngestResult, OutputResult
from pipeline.stages.s1_ingest import ingest, make_book_slug
from pipeline.stages.s2_segment import segment
from pipeline.stages.s3_extract import extract
from pipeline.stages.s4_output import output_to_db


async def run_pipeline(
    file_path: str,
    config: dict | None = None,
    output_dir: str | None = None,
    skip_output: bool = False,
) -> dict:
    """Run the 4-stage pipeline on a single file.

    Args:
        file_path: Path to input file (.pdf/.txt/.md/.rtf)
        config: Config dict (loads from config.yaml if None)
        output_dir: Directory for story JSON files (default: pipeline/output/{book_slug})
        skip_output: If True, skip S4 DB output (dry-run mode)

    Returns a dict with all stage results.
    """
    if config is None:
        from pipeline.core.llm_client import load_config
        config = load_config()

    llm = LLMClient(config)
    results = {}

    # Resolve output_dir early so we can check for cached ingest
    book_slug = make_book_slug(file_path)
    if output_dir is None:
        output_dir = str(Path(__file__).parent / "output" / book_slug)
    out_path = Path(output_dir)
    ingest_cache = out_path / "_ingest.json"

    # Stage 1: Ingest (skip if cached)
    if ingest_cache.exists():
        print("[Stage 1/4] Loading cached ingest...")
        data = json.loads(ingest_cache.read_text(encoding="utf-8"))
        ingest_result = IngestResult(**data)
        print(f"  → {ingest_result.page_count} pages, {len(ingest_result.raw_text)} chars (cached)")
    else:
        print("[Stage 1/4] Ingesting file...")
        ingest_result = await ingest(file_path, config)

        # Book summary extraction (from preface)
        from pipeline.stages.book_summary import identify_preface, extract_book_summary
        preface_text, _ = identify_preface(ingest_result.raw_text)
        if preface_text and len(preface_text) > 100:
            print("[S1] Extracting book summary from preface...")
            book_summary = await extract_book_summary(preface_text, llm)
            ingest_result.metadata["book_summary"] = book_summary

        # Cache ingest result
        out_path.mkdir(parents=True, exist_ok=True)
        ingest_cache.write_text(ingest_result.model_dump_json(indent=2), encoding="utf-8")
        print(f"  → cached to {ingest_cache}")

        print(f"  → {ingest_result.page_count} pages, {len(ingest_result.raw_text)} chars, "
              f"method: {ingest_result.ocr_method}, lang: {ingest_result.detected_language}")

    results["ingest"] = ingest_result

    # Stage 2: Segment
    print("[Stage 2/4] Segmenting text...")
    segment_result = await segment(ingest_result, output_dir=output_dir, llm=llm)
    results["segment"] = segment_result
    print(f"  → {len(segment_result.segments)} segments, book_slug: {segment_result.book_slug}")

    # Stage 3: Extract (single LLM call per story)
    print("[Stage 3/4] Extracting data...")
    # Collect known entities from already-extracted stories (for context injection)
    known_entities = []
    for seg_info in segment_result.segments:
        story_path = Path(seg_info.file_path)
        if story_path.exists():
            data = json.loads(story_path.read_text(encoding="utf-8"))
            if data.get("entities"):
                for loc in data["entities"].get("locations", []):
                    if loc.get("name") and loc.get("lat") and loc.get("lng"):
                        known_entities.append(loc)

    book_summary = getattr(ingest_result, 'metadata', {}).get("book_summary") if hasattr(ingest_result, 'metadata') and ingest_result.metadata else None
    extract_stats = await extract(segment_result, llm, book_summary=book_summary, known_entities=known_entities, config=config)
    results["extract"] = extract_stats
    print(f"  → processed: {extract_stats['processed']}, "
          f"skipped: {extract_stats['skipped']}, failed: {extract_stats['failed']}")

    # Stage 4: Output to DB
    if skip_output:
        print("[Stage 4/4] DB output (skipped in dry-run)")
        results["output"] = OutputResult()
    else:
        print("[Stage 4/4] Writing to database...")
        from pipeline.core.db import make_engine, make_session_factory

        db_url = config.get("database", {}).get("url")
        if not db_url:
            print("  → No database URL configured, skipping output")
            results["output"] = OutputResult()
        else:
            engine = make_engine(db_url)
            session_factory = make_session_factory(engine)
            async with session_factory() as session:
                output_result = await output_to_db(segment_result, session)
            results["output"] = output_result
            print(f"  → books: {output_result.books}, entries: {output_result.entries}, "
                  f"locations: {output_result.locations}")
            await engine.dispose()

    print("Pipeline complete!")
    return results
