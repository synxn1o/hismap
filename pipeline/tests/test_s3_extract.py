from __future__ import annotations

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

from pipeline.models import ExtractedStory, SegmentInfo, SegmentResultV2


@pytest.fixture
def story_file(tmp_path):
    """Create a story JSON file for testing."""
    story = ExtractedStory(
        id="test-en-001",
        book_slug="test",
        language="en",
        sequence=1,
        title="Chapter 1",
        original_text="Marco Polo traveled to Beijing in 1271.",
        source_type="text",
        extracted=False,
    )
    path = tmp_path / "test-en-001.json"
    path.write_text(story.model_dump_json(indent=2))
    return str(path)


@pytest.fixture
def mock_llm():
    """Create a mock LLM client that returns structured extraction JSON."""
    llm = AsyncMock()
    llm.chat_with_tools = AsyncMock(return_value=json.dumps({
        "book_metadata": {
            "title": "The Travels of Marco Polo",
            "author": "Marco Polo",
            "dynasty": "Yuan",
            "era_start": 1271,
            "era_end": 1295,
            "author_biography": "Venetian merchant traveler",
        },
        "story_metadata": {
            "title": "Chapter 1",
            "chapter_reference": "Chapter 1",
            "visit_date_approximate": "1271",
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
            "persons": ["Kublai Khan"],
            "dates": ["1271"],
            "keywords": ["trade", "silk road"],
        },
        "translations": {
            "modern_chinese": None,
            "english": "Marco Polo traveled to Beijing in 1271.",
        },
        "credibility": {
            "era_context": "Late 13th century",
            "political_context": "Yuan Dynasty",
            "religious_context": "Religious tolerance",
            "social_environment": "Silk Road trade",
            "credibility_score": 0.85,
            "notes": "First-hand account",
        },
        "annotations": [
            {
                "source": "web_search",
                "query": "Marco Polo Beijing",
                "url": "https://en.wikipedia.org/wiki/Marco_Polo",
                "snippet": "Marco Polo departed Venice in 1271...",
            }
        ],
    }))
    return llm


@pytest.mark.asyncio
async def test_extract_single_story(story_file, mock_llm):
    """Test that extract processes a story file and updates it."""
    from pipeline.stages.s3_extract import extract

    segment = SegmentInfo(
        id="test-en-001",
        title="Chapter 1",
        file_path=story_file,
        original_text_preview="Marco Polo traveled...",
    )
    segment_result = SegmentResultV2(
        book_slug="test",
        language="en",
        segments=[segment],
    )

    result = await extract(segment_result, mock_llm)

    saved = json.loads(Path(story_file).read_text())
    assert saved["extracted"] is True
    assert saved["error"] is None
    assert saved["book_metadata"]["title"] == "The Travels of Marco Polo"
    assert len(saved["entities"]["locations"]) == 1
    assert saved["credibility"]["credibility_score"] == 0.85


@pytest.mark.asyncio
async def test_extract_skips_already_extracted(tmp_path, mock_llm):
    """Test that already-extracted stories are skipped."""
    from pipeline.stages.s3_extract import extract

    story = ExtractedStory(
        id="test-en-002",
        book_slug="test",
        language="en",
        sequence=2,
        title="Already Done",
        original_text="Some text",
        source_type="text",
        extracted=True,
    )
    path = tmp_path / "test-en-002.json"
    path.write_text(story.model_dump_json(indent=2))

    segment = SegmentInfo(
        id="test-en-002",
        title="Already Done",
        file_path=str(path),
        original_text_preview="Some text",
    )
    segment_result = SegmentResultV2(book_slug="test", language="en", segments=[segment])

    result = await extract(segment_result, mock_llm)

    mock_llm.chat_with_tools.assert_not_called()


@pytest.mark.asyncio
async def test_extract_handles_llm_failure(tmp_path, mock_llm):
    """Test that LLM failure is recorded in the JSON file."""
    from pipeline.stages.s3_extract import extract

    story = ExtractedStory(
        id="test-en-003",
        book_slug="test",
        language="en",
        sequence=3,
        title="Will Fail",
        original_text="Some text",
        source_type="text",
        extracted=False,
    )
    path = tmp_path / "test-en-003.json"
    path.write_text(story.model_dump_json(indent=2))

    mock_llm.chat_with_tools.side_effect = Exception("API error")
    mock_llm.extract_json = AsyncMock(side_effect=Exception("API error"))

    segment = SegmentInfo(
        id="test-en-003",
        title="Will Fail",
        file_path=str(path),
        original_text_preview="Some text",
    )
    segment_result = SegmentResultV2(book_slug="test", language="en", segments=[segment])

    result = await extract(segment_result, mock_llm)

    saved = json.loads(Path(path).read_text())
    assert saved["extracted"] is False
    assert saved["error"] is not None
    assert "API error" in saved["error"]


@pytest.mark.asyncio
async def test_extract_skips_non_content_stories(tmp_path, mock_llm):
    """S3 should skip extraction for stories marked is_content=False."""
    from pipeline.stages.s3_extract import extract

    story = ExtractedStory(
        id="test-en-004",
        book_slug="test",
        language="en",
        sequence=4,
        title="Table of Contents",
        original_text="Chapter 1... 1\nChapter 2... 15",
        source_type="text",
        extracted=False,
        is_content=False,
    )
    path = tmp_path / "test-en-004.json"
    path.write_text(story.model_dump_json(indent=2))

    segment = SegmentInfo(
        id="test-en-004",
        title="Table of Contents",
        file_path=str(path),
        original_text_preview="Chapter 1...",
    )
    segment_result = SegmentResultV2(book_slug="test", language="en", segments=[segment])

    result = await extract(segment_result, mock_llm)

    # LLM should NOT be called for non-content
    mock_llm.chat_with_tools.assert_not_called()
    # Story should be marked as extracted with non_content note
    saved = json.loads(path.read_text())
    assert saved["extracted"] is True
    assert saved["error"] == "non_content"
    assert result["skipped"] == 1


def test_combined_prompt_template_loads():
    """The combined extraction prompt template should load and format correctly."""
    from pathlib import Path

    prompt_path = Path(__file__).parent.parent / "config" / "prompts" / "extraction_combined.txt"
    assert prompt_path.exists(), f"Prompt not found at {prompt_path}"

    template = prompt_path.read_text()
    assert "{context}" in template
    assert "{text}" in template

    # Verify it formats without error
    formatted = template.format(context="Book: Test Book\nAuthor: Test", text="Some story text")
    assert "Test Book" in formatted
    assert "Some story text" in formatted
    assert "{context}" not in formatted
    assert "{text}" not in formatted


def test_combined_prompt_contains_required_sections():
    """The combined prompt should contain filter, segment, and extract instructions."""
    from pathlib import Path

    prompt_path = Path(__file__).parent.parent / "config" / "prompts" / "extraction_combined.txt"
    template = prompt_path.read_text()

    # Check for key instruction sections
    assert "is_content" in template
    assert "start_anchor" in template
    assert "end_anchor" in template
    assert "excerpt" in template
    assert "summary" in template
    assert "entries" in template
