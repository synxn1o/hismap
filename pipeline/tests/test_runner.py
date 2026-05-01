import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from pipeline.models import (
    IngestResult,
    SegmentResult,
    TextSegment,
    EntityResult,
    ExtractedEntry,
    GeocodedResult,
    GeocodedEntry,
    TranslatedResult,
    TranslatedEntry,
    AnalyzedResult,
    AnalyzedEntry,
    CredibilityReport,
    ScoredDimension,
)


@pytest.mark.asyncio
async def test_run_pipeline_dry_run():
    """Test pipeline stages are called in order with mocked LLM."""
    mock_ingest = IngestResult(
        source_file="test.txt", file_type="text", raw_text="马可·波罗到达泉州", page_count=1, ocr_method="direct"
    )
    mock_segment = SegmentResult(segments=[
        TextSegment(segment_id="s1", text="马可·波罗到达泉州", language="zh-cn")
    ])
    mock_entity = EntityResult(entries=[
        ExtractedEntry(
            segment_id="s1", title="泉州见闻",
            original_text="马可·波罗到达泉州",
            locations_mentioned=["泉州"], dates_mentioned=["1292"],
            persons_mentioned=["马可·波罗"], keywords=["泉州"],
        )
    ])

    dim = ScoredDimension(score=0.8, evidence="test")

    with (
        patch("pipeline.runner.ingest", return_value=mock_ingest),
        patch("pipeline.runner.segment", return_value=mock_segment),
        patch("pipeline.runner.extract_entities", return_value=mock_entity),
        patch("pipeline.runner.geocode_locations", return_value=GeocodedResult(entries=[
            GeocodedEntry(segment_id="s1", title="泉州见闻", original_text="马可·波罗到达泉州", location_links=[])
        ], locations=[])),
        patch("pipeline.runner.translate_entries", return_value=TranslatedResult(entries=[
            TranslatedEntry(segment_id="s1", title="泉州见闻", original_text="马可·波罗到达泉州", location_links=[])
        ])),
        patch("pipeline.runner.analyze_entries", return_value=AnalyzedResult(
            entries=[AnalyzedEntry(segment_id="s1", title="泉州见闻", original_text="马可·波罗到达泉州", location_links=[])],
            credibility_reports=[],
        )),
    ):
        from pipeline.runner import run_pipeline
        results = await run_pipeline("test.txt", {"llm": {"base_url": "x", "api_key": "x", "model": "x"}})

        assert "ingest" in results
        assert "analyzed" in results
        assert len(results["entity"].entries) == 1
