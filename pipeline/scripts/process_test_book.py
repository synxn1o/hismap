"""Process test book files through the pipeline (no DB write).

Usage:
    conda run -n hismap python pipeline/scripts/process_test_book.py [--extract] [--llm-segment] [--ocr]

Modes:
    (default)       S1 ingest + S2 segment (regex headings, no LLM)
    --llm-segment   S1 ingest + S2 segment with LLM fallback (tests _segment_by_llm)
    --ocr           S1 ingest with structured OCR on PDF (tests ocr_pdf_structured)
    --extract       Also run S3 extraction (can combine with any above)
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.core.llm_client import LLMClient, load_config
from pipeline.stages.s1_ingest import ingest
from pipeline.stages.s2_segment import segment
from pipeline.stages.s3_extract import extract

TEST_BOOK_DIR = ROOT / "test_book"
OUTPUT_DIR = ROOT / "pipeline" / "output"
MAX_TEXT_CHARS = 100_000


async def test_regex_segment(config: dict):
    """Default: S1 + S2 with regex heading detection on RTF."""
    rtf_files = sorted(TEST_BOOK_DIR.glob("*.rtf"))
    if not rtf_files:
        print("No RTF files found")
        return

    file_path = rtf_files[0]
    print(f"\n{'='*60}")
    print(f"REGEX SEGMENT: {file_path.name}")
    print(f"{'='*60}")

    ingest_result = await ingest(str(file_path), config)
    print(f"  book_slug: {ingest_result.book_slug}")
    print(f"  language: {ingest_result.detected_language}")
    print(f"  raw_text: {len(ingest_result.raw_text)} chars")

    if len(ingest_result.raw_text) > MAX_TEXT_CHARS:
        ingest_result = ingest_result.model_copy(
            update={"raw_text": ingest_result.raw_text[:MAX_TEXT_CHARS]}
        )

    output_dir = str(OUTPUT_DIR / ingest_result.book_slug)
    segment_result = await segment(ingest_result, output_dir=output_dir)
    print(f"  segments: {len(segment_result.segments)}")
    for seg in segment_result.segments[:10]:
        print(f"    {seg.id}: {seg.title}")
    if len(segment_result.segments) > 10:
        print(f"    ... and {len(segment_result.segments) - 10} more")


async def test_llm_segment(config: dict):
    """Test LLM segment fallback: strip headings, pass text to S2 with LLM."""
    rtf_files = sorted(TEST_BOOK_DIR.glob("*.rtf"))
    if not rtf_files:
        print("No RTF files found")
        return

    file_path = rtf_files[0]
    print(f"\n{'='*60}")
    print(f"LLM SEGMENT FALLBACK: {file_path.name}")
    print(f"{'='*60}")

    ingest_result = await ingest(str(file_path), config)
    print(f"  book_slug: {ingest_result.book_slug}")
    print(f"  language: {ingest_result.detected_language}")
    print(f"  raw_text: {len(ingest_result.raw_text)} chars")

    # Truncate to first 30k chars for faster LLM test
    test_chars = 30_000
    if len(ingest_result.raw_text) > test_chars:
        print(f"  Truncating to {test_chars} chars for LLM segment test")
        ingest_result = ingest_result.model_copy(
            update={"raw_text": ingest_result.raw_text[:test_chars]}
        )

    llm = LLMClient(config)
    output_dir = str(OUTPUT_DIR / ingest_result.book_slug / "llm_segment")
    print(f"  Calling S2 segment with LLM fallback...")
    segment_result = await segment(ingest_result, output_dir=output_dir, llm=llm)
    print(f"  segments: {len(segment_result.segments)}")
    for seg in segment_result.segments[:10]:
        print(f"    {seg.id}: {seg.title}")
    if len(segment_result.segments) > 10:
        print(f"    ... and {len(segment_result.segments) - 10} more")


async def test_ocr_path(config: dict):
    """Test structured OCR path on PDF."""
    pdf_files = sorted(TEST_BOOK_DIR.glob("*.pdf"))
    if not pdf_files:
        print("No PDF files found")
        return

    file_path = pdf_files[0]
    print(f"\n{'='*60}")
    print(f"OCR PATH: {file_path.name}")
    print(f"{'='*60}")

    from pipeline.core.ocr import OCRClient
    import fitz

    ocr = OCRClient(config)

    # OCR first 5 pages only
    max_pages = 5
    doc = fitz.open(str(file_path))
    total_pages = len(doc)
    print(f"  PDF has {total_pages} pages, processing first {max_pages}")

    ocr_pages = []
    for i, page in enumerate(doc):
        if i >= max_pages:
            break
        pix = page.get_pixmap(dpi=ocr.dpi)
        import base64
        img_b64 = base64.b64encode(pix.tobytes("png")).decode()
        print(f"  OCR page {i+1}/{max_pages}...", end=" ", flush=True)
        result = await ocr.ocr_page_structured(img_b64)
        ocr_pages.append(result)
        stories = result.get("stories", [])
        print(f"→ {len(result.get('text', ''))} chars, {len(stories)} stories")
    doc.close()

    # Build IngestResult manually with OCR pages
    from pipeline.models import IngestResult
    from pipeline.stages.s1_ingest import make_book_slug, detect_language
    from langdetect import detect

    raw_text = "\n\n".join(p.get("text", "") for p in ocr_pages)
    ingest_result = IngestResult(
        source_file=str(file_path),
        file_type="pdf_scanned",
        raw_text=raw_text,
        page_count=len(ocr_pages),
        ocr_method="vision_llm",
        book_slug=make_book_slug(str(file_path)),
        detected_language=detect_language(raw_text),
        ocr_pages=ocr_pages,
    )

    print(f"\n  book_slug: {ingest_result.book_slug}")
    print(f"  language: {ingest_result.detected_language}")
    print(f"  ocr_pages: {len(ingest_result.ocr_pages)}")

    # S2 segment with OCR merge
    output_dir = str(OUTPUT_DIR / ingest_result.book_slug)
    segment_result = await segment(ingest_result, output_dir=output_dir)
    print(f"  segments: {len(segment_result.segments)}")
    for seg in segment_result.segments:
        print(f"    {seg.id}: {seg.title}")


async def run_extraction(segment_result, config: dict):
    """Run S3 extraction on a segment result."""
    print(f"\n  [S3] Extracting {len(segment_result.segments)} stories...")
    llm = LLMClient(config)
    stats = await extract(segment_result, llm)
    print(f"  processed: {stats['processed']}, skipped: {stats['skipped']}, failed: {stats['failed']}")

    if segment_result.segments:
        first = segment_result.segments[0]
        data = json.loads(Path(first.file_path).read_text())
        if data.get("book_metadata"):
            print(f"  book: {data['book_metadata'].get('title', '?')}")
        if data.get("entities", {}).get("locations"):
            locs = [l["name"] for l in data["entities"]["locations"]]
            print(f"  locations: {', '.join(locs[:5])}")


async def main():
    args = sys.argv[1:]
    do_extract = "--extract" in args
    do_llm_segment = "--llm-segment" in args
    do_ocr = "--ocr" in args

    config = load_config()

    if do_ocr:
        await test_ocr_path(config)
    elif do_llm_segment:
        await test_llm_segment(config)
    else:
        await test_regex_segment(config)

    if do_extract:
        # Re-run with extraction on whichever path was tested
        print("\n--- Running S3 extraction ---")
        rtf_files = sorted(TEST_BOOK_DIR.glob("*.rtf"))
        if rtf_files:
            ingest_result = await ingest(str(rtf_files[0]), config)
            if len(ingest_result.raw_text) > MAX_TEXT_CHARS:
                ingest_result = ingest_result.model_copy(
                    update={"raw_text": ingest_result.raw_text[:MAX_TEXT_CHARS]}
                )
            output_dir = str(OUTPUT_DIR / ingest_result.book_slug)
            segment_result = await segment(ingest_result, output_dir=output_dir, llm=LLMClient(config) if do_llm_segment else None)
            await run_extraction(segment_result, config)


if __name__ == "__main__":
    asyncio.run(main())
