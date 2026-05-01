import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from pipeline.models import (
    IngestResult,
    SegmentResultV2,
    SegmentInfo,
    OutputResult,
)


@pytest.mark.asyncio
async def test_run_pipeline_dry_run():
    """Test pipeline stages are called in order with mocked LLM."""
    mock_ingest = IngestResult(
        source_file="test.txt",
        file_type="text",
        raw_text="Marco Polo traveled to Beijing.",
        page_count=1,
        ocr_method="direct",
        book_slug="test",
        detected_language="en",
    )
    mock_segment = SegmentResultV2(
        book_slug="test",
        language="en",
        segments=[
            SegmentInfo(
                id="test-en-001",
                title="Segment 1",
                file_path="/tmp/test-en-001.json",
                original_text_preview="Marco Polo traveled...",
            )
        ],
    )
    mock_extract_stats = {"processed": 1, "skipped": 0, "failed": 0}

    with (
        patch("pipeline.runner.ingest", return_value=mock_ingest) as m_ingest,
        patch("pipeline.runner.segment", return_value=mock_segment) as m_segment,
        patch("pipeline.runner.extract", return_value=mock_extract_stats) as m_extract,
    ):
        from pipeline.runner import run_pipeline
        results = await run_pipeline(
            "test.txt",
            config={"llm": {"base_url": "x", "api_key": "x", "model": "x"}},
            skip_output=True,
        )

        m_ingest.assert_called_once()
        m_segment.assert_called_once()
        m_extract.assert_called_once()

        assert "ingest" in results
        assert "segment" in results
        assert "extract" in results
        assert "output" in results
        assert results["extract"]["processed"] == 1
