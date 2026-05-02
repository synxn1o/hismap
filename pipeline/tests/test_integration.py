"""Integration test: run the 4-stage pipeline on actual test book files."""
from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from pipeline.models import IngestResult, SegmentResultV2, OutputResult
from pipeline.stages.s1_ingest import ingest
from pipeline.stages.s2_segment import segment
from pipeline.stages.s3_extract import extract


TEST_BOOK_DIR = Path(__file__).parent.parent.parent / "test_book"

# Segmentation mock: what _segment_by_llm expects from extract_json
SAMPLE_SEGMENTATION = json.dumps({
    "stories": [
        {
            "title": "Chapter 1 - The Beginning",
            "text": "Marco Polo set out from Venice on his great journey eastward. "
                    "He traveled through many lands and saw many wonders. "
                    "This is the beginning of his famous travels.",
            "continues_from_prev": False,
            "continues_to_next": True,
        },
        {
            "title": "Chapter 2 - The Middle Kingdom",
            "text": "After many months of travel, Marco Polo arrived at the court "
                    "of the great Khan. The Khan received him warmly and was fascinated "
                    "by the reports of distant lands.",
            "continues_from_prev": True,
            "continues_to_next": False,
        },
    ]
})

SAMPLE_EXTRACTION = json.dumps({
    "entries": [
        {
            "start_anchor": "Marco Polo set out from Venice",
            "end_anchor": "great journey eastward.",
            "is_content": True,
            "is_truncated": False,
            "story_metadata": {
                "title": "Chapter Title",
                "chapter_reference": "Chapter 1",
                "visit_date_approximate": "1271",
            },
            "excerpt": {
                "original": "Marco Polo set out from Venice on his great journey eastward.",
                "translation": "Marco Polo set out from Venice on his great journey eastward.",
            },
            "summary": {
                "chinese": "马可波罗从威尼斯出发东行。",
                "english": "Marco Polo set out from Venice on his great journey.",
            },
            "entities": {
                "locations": [
                    {
                        "name": "Beijing",
                        "modern_name": "Beijing",
                        "ancient_name": "Dadu",
                        "lat": 39.9042,
                        "lng": 116.4074,
                        "location_type": "city",
                        "one_line_summary": "Capital of Yuan Dynasty",
                    }
                ],
                "persons": ["Marco Polo"],
                "dates": ["1271"],
                "keywords": ["travel"],
            },
            "credibility": {
                "era_context": "13th century",
                "political_context": "Yuan Dynasty",
                "religious_context": "Mixed",
                "social_environment": "Trade",
                "credibility_score": 0.8,
                "notes": "First-hand account",
            },
            "annotations": [
                {
                    "source": "web_search",
                    "query": "test query",
                    "url": "https://example.com",
                    "snippet": "test snippet",
                }
            ],
        }
    ]
})


def _make_config() -> dict:
    """Minimal config for pipeline stages (LLM calls will be mocked)."""
    return {
        "llm": {"base_url": "http://localhost", "api_key": "test", "model": "test"},
        "ocr": {"base_url": "http://localhost", "api_key": "test", "model": "test"},
    }


def _make_mock_llm() -> AsyncMock:
    """Create a mock LLM client that returns sample data.

    - extract_json: returns segmentation format (used by s2_segment LLM fallback)
    - chat_with_tools: returns extraction format (used by s3_extract)
    """
    mock_llm = AsyncMock()
    mock_llm.chat_with_tools = AsyncMock(return_value=SAMPLE_EXTRACTION)
    mock_llm.extract_json = AsyncMock(return_value=SAMPLE_SEGMENTATION)
    return mock_llm


@pytest.mark.asyncio
async def test_rtf_english_pipeline(tmp_path):
    """Run pipeline on English RTF with mocked LLM."""
    rtf_path = TEST_BOOK_DIR / "The Travels of Marco Polo_eng.rtf"
    if not rtf_path.exists():
        pytest.skip(f"Test file not found: {rtf_path}")

    config = _make_config()
    output_dir = str(tmp_path / "output")

    # Stage 1: Real ingest
    ingest_result = await ingest(str(rtf_path), config)
    assert ingest_result.book_slug, "book_slug should be derived from filename"
    assert ingest_result.detected_language != "unknown"
    assert len(ingest_result.raw_text) > 0

    # Truncate to 100k chars as requested
    if len(ingest_result.raw_text) > 100000:
        ingest_result = ingest_result.model_copy(
            update={"raw_text": ingest_result.raw_text[:100000]}
        )

    # Stage 2: Real segment
    mock_llm = _make_mock_llm()
    segment_result = await segment(ingest_result, output_dir=output_dir, llm=mock_llm)
    assert len(segment_result.segments) >= 1, "Should produce at least 1 segment"
    assert segment_result.book_slug == ingest_result.book_slug

    # Verify segment JSON files exist and are valid
    for seg in segment_result.segments:
        story_path = Path(seg.file_path)
        assert story_path.exists(), f"Segment file should exist: {seg.file_path}"
        story_data = json.loads(story_path.read_text(encoding="utf-8"))
        assert story_data["id"] == seg.id
        assert story_data["extracted"] is False  # not yet extracted

    # Stage 3: Extract with mocked LLM
    extract_stats = await extract(segment_result, mock_llm)
    assert extract_stats["processed"] >= 1
    assert extract_stats["failed"] == 0

    # Verify extracted data was written to JSON files
    for seg in segment_result.segments:
        story_data = json.loads(Path(seg.file_path).read_text(encoding="utf-8"))
        assert story_data["extracted"] is True
        assert story_data["entities"] is not None
        assert story_data["summary_english"] is not None or story_data["summary_chinese"] is not None


@pytest.mark.asyncio
async def test_rtf_chinese_pipeline(tmp_path):
    """Run pipeline on Chinese RTF with mocked LLM."""
    rtf_path = TEST_BOOK_DIR / "marco_polo_chs.rtf"
    if not rtf_path.exists():
        pytest.skip(f"Test file not found: {rtf_path}")

    config = _make_config()
    output_dir = str(tmp_path / "output")

    # Stage 1: Real ingest
    ingest_result = await ingest(str(rtf_path), config)
    assert ingest_result.book_slug, "book_slug should be derived from filename"
    assert len(ingest_result.raw_text) > 0

    # Truncate to 100k chars
    if len(ingest_result.raw_text) > 100000:
        ingest_result = ingest_result.model_copy(
            update={"raw_text": ingest_result.raw_text[:100000]}
        )

    # Stage 2: Real segment
    mock_llm = _make_mock_llm()
    segment_result = await segment(ingest_result, output_dir=output_dir, llm=mock_llm)
    assert len(segment_result.segments) >= 1, "Should produce at least 1 segment"

    # Verify segment JSON files
    for seg in segment_result.segments:
        story_path = Path(seg.file_path)
        assert story_path.exists()
        story_data = json.loads(story_path.read_text(encoding="utf-8"))
        assert story_data["id"] == seg.id

    # Stage 3: Extract with mocked LLM
    extract_stats = await extract(segment_result, mock_llm)
    assert extract_stats["processed"] >= 1
    assert extract_stats["failed"] == 0

    # Verify extraction results
    for seg in segment_result.segments:
        story_data = json.loads(Path(seg.file_path).read_text(encoding="utf-8"))
        assert story_data["extracted"] is True
        assert story_data["entities"] is not None


@pytest.mark.asyncio
async def test_pdf_pipeline_mocked_ocr(tmp_path):
    """Run pipeline on PDF with mocked OCR (15 pages) and mocked LLM."""
    pdf_path = TEST_BOOK_DIR / "伊本_白图泰游记.pdf"
    if not pdf_path.exists():
        pytest.skip(f"Test file not found: {pdf_path}")

    # Create mock OCR pages (15 pages)
    mock_ocr_pages = []
    for i in range(15):
        mock_ocr_pages.append({
            "text": f"Page {i + 1} text from Ibn Battuta's travels...",
            "stories": [
                {
                    "title": f"Story on page {i + 1}",
                    "text": f"This is story text from page {i + 1} of the travelogue...",
                    "continues_from_prev": i > 0,
                    "continues_to_next": i < 14,
                }
            ],
        })

    config = _make_config()
    output_dir = str(tmp_path / "output")

    # Stage 1: Ingest with mocked OCR
    # The actual PDF is digital (has embedded text), but we want to test the
    # scanned-PDF / OCR path. Mock extract_text_from_pdf to report it as scanned.
    mock_ocr_client = AsyncMock()
    mock_ocr_client.ocr_pdf_structured = AsyncMock(return_value=mock_ocr_pages)

    with (
        patch(
            "pipeline.stages.s1_ingest.extract_text_from_pdf",
            return_value=("", 15, True),
        ),
        patch("pipeline.core.ocr.OCRClient", return_value=mock_ocr_client),
    ):
        ingest_result = await ingest(str(pdf_path), config)

    assert ingest_result.file_type == "pdf_scanned"
    assert ingest_result.ocr_pages == mock_ocr_pages
    assert len(ingest_result.raw_text) > 0

    # Stage 2: Segment (uses OCR story merging)
    mock_llm = _make_mock_llm()
    segment_result = await segment(ingest_result, output_dir=output_dir, llm=mock_llm)
    assert len(segment_result.segments) >= 1, "Should produce segments from OCR pages"

    # Verify segment files
    for seg in segment_result.segments:
        story_path = Path(seg.file_path)
        assert story_path.exists()
        story_data = json.loads(story_path.read_text(encoding="utf-8"))
        assert story_data["id"] == seg.id
        assert story_data["source_type"] == "ocr"

    # Stage 3: Extract with mocked LLM
    extract_stats = await extract(segment_result, mock_llm)
    assert extract_stats["processed"] >= 1
    assert extract_stats["failed"] == 0

    # Verify extraction
    for seg in segment_result.segments:
        story_data = json.loads(Path(seg.file_path).read_text(encoding="utf-8"))
        assert story_data["extracted"] is True
        assert story_data["entities"] is not None


@pytest.mark.asyncio
async def test_full_pipeline_via_runner(tmp_path):
    """Run the full pipeline via run_pipeline with all stages mocked as needed."""
    rtf_path = TEST_BOOK_DIR / "The Travels of Marco Polo_eng.rtf"
    if not rtf_path.exists():
        pytest.skip(f"Test file not found: {rtf_path}")

    config = _make_config()
    output_dir = str(tmp_path / "output")
    mock_llm = _make_mock_llm()

    # Patch LLMClient in the runner so extract gets our mock
    with patch("pipeline.runner.LLMClient", return_value=mock_llm):
        from pipeline.runner import run_pipeline

        results = await run_pipeline(
            str(rtf_path),
            config=config,
            output_dir=output_dir,
            skip_output=True,
        )

    # Verify all stages ran
    assert "ingest" in results
    assert "segment" in results
    assert "extract" in results
    assert "output" in results

    # Verify S1
    ingest_r = results["ingest"]
    assert ingest_r.book_slug
    assert ingest_r.detected_language != "unknown"
    assert len(ingest_r.raw_text) > 0

    # Verify S2
    segment_r = results["segment"]
    assert len(segment_r.segments) >= 1
    for seg in segment_r.segments:
        assert Path(seg.file_path).exists()
        story_data = json.loads(Path(seg.file_path).read_text(encoding="utf-8"))
        assert story_data["id"] == seg.id

    # Verify S3
    extract_stats = results["extract"]
    assert extract_stats["processed"] >= 1

    # Verify extracted data in JSON files
    for seg in segment_r.segments:
        story_data = json.loads(Path(seg.file_path).read_text(encoding="utf-8"))
        if story_data["extracted"]:
            assert story_data["entities"] is not None

    # Verify S4 was skipped
    assert isinstance(results["output"], OutputResult)
