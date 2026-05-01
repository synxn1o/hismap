from __future__ import annotations

from pathlib import Path

from pipeline.core.llm_client import LLMClient
from pipeline.models import OutputResult
from pipeline.stages.s1_ingest import ingest
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

    # Stage 1: Ingest
    print("[Stage 1/4] Ingesting file...")
    ingest_result = await ingest(file_path, config)
    results["ingest"] = ingest_result
    print(f"  → {ingest_result.page_count} pages, {len(ingest_result.raw_text)} chars, "
          f"method: {ingest_result.ocr_method}, lang: {ingest_result.detected_language}")

    # Stage 2: Segment
    print("[Stage 2/4] Segmenting text...")
    segment_result = await segment(ingest_result, output_dir=output_dir, llm=llm)
    results["segment"] = segment_result
    print(f"  → {len(segment_result.segments)} segments, book_slug: {segment_result.book_slug}")

    # Stage 3: Extract (single LLM call per story)
    print("[Stage 3/4] Extracting data...")
    extract_stats = await extract(segment_result, llm)
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
