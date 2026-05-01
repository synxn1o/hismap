from __future__ import annotations

from pipeline.core.llm_client import LLMClient
from pipeline.models import IngestResult, PipelineRun
from pipeline.stages.s1_ingest import ingest
from pipeline.stages.s2_segment import segment
from pipeline.stages.s3_extract import extract_entities
from pipeline.stages.s4_geocode import geocode_locations
from pipeline.stages.s5_translate import translate_entries
from pipeline.stages.s6_analyze import analyze_entries


async def run_pipeline(file_path: str, config: dict | None = None) -> dict:
    """Run the full pipeline on a single file.

    Returns a dict with all stage results.
    """
    if config is None:
        from pipeline.core.llm_client import load_config
        config = load_config()

    llm = LLMClient(config)
    results = {}

    # Stage 1: Ingest
    print("[Stage 1/7] Ingesting file...")
    ingest_result = await ingest(file_path, config)
    results["ingest"] = ingest_result
    print(f"  → {ingest_result.page_count} pages, {len(ingest_result.raw_text)} chars, method: {ingest_result.ocr_method}")

    # Stage 2: Segment
    print("[Stage 2/7] Segmenting text...")
    segment_result = await segment(ingest_result)
    results["segment"] = segment_result
    print(f"  → {len(segment_result.segments)} segments")

    # Stage 3: Extract entities
    print("[Stage 3/7] Extracting entities...")
    entity_result = await extract_entities(segment_result, llm)
    results["entity"] = entity_result
    print(f"  → {len(entity_result.entries)} entries extracted")
    if entity_result.book_meta:
        print(f"  → Book: {entity_result.book_meta.title}")

    # Stage 4: Geocode
    print("[Stage 4/7] Geocoding locations...")
    geocoded_result = await geocode_locations(entity_result, llm)
    results["geocoded"] = geocoded_result
    print(f"  → {len(geocoded_result.locations)} locations resolved")

    # Stage 5: Translate
    print("[Stage 5/7] Translating entries...")
    translated_result = await translate_entries(geocoded_result, llm)
    results["translated"] = translated_result

    # Stage 6: Analyze
    print("[Stage 6/7] Analyzing credibility...")
    book_title = entity_result.book_meta.title if entity_result.book_meta else ""
    author_name = entity_result.author_meta.name if entity_result.author_meta else ""
    analyzed_result = await analyze_entries(translated_result, llm, book_title, author_name)
    results["analyzed"] = analyzed_result
    print(f"  → {len(analyzed_result.credibility_reports)} credibility reports")

    # Stage 7: Output (skipped in dry-run — use s7_output.output_to_db directly)
    print("[Stage 7/7] Output to DB (skipped in dry-run)")

    print("Pipeline complete!")
    return results
