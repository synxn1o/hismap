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
        "entries": [
            {
                "start_anchor": "Marco Polo traveled",
                "end_anchor": "to Beijing in 1271.",
                "is_content": True,
                "is_truncated": False,
                "story_metadata": {
                    "title": "Chapter 1",
                    "chapter_reference": "Chapter 1",
                    "visit_date_approximate": "1271",
                },
                "excerpt": {
                    "original": "Marco Polo traveled to Beijing.",
                    "translation": "Marco Polo traveled to Beijing.",
                },
                "summary": {
                    "chinese": "马可波罗前往北京。",
                    "english": "Marco Polo traveled to Beijing.",
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
            }
        ]
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
    assert saved["excerpt_original"] == "Marco Polo traveled to Beijing."
    assert saved["summary_english"] == "Marco Polo traveled to Beijing."
    assert saved["persons"] == ["Kublai Khan"]
    assert saved["dates"] == ["1271"]
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


def test_build_context_includes_all_items():
    """build_context should include all 7 context items."""
    from pipeline.stages.s3_extract import build_context

    story = ExtractedStory(
        id="test-en-001",
        book_slug="test",
        language="en",
        sequence=1,
        title="Chapter 1",
        original_text="Text",
        source_type="text",
        chapter_title="The Beginning",
        book_metadata={
            "title": "Travels",
            "author": "Marco Polo",
            "dynasty": "Yuan",
        },
    )

    segment_result = SegmentResultV2(
        book_slug="test",
        language="en",
        segments=[
            SegmentInfo(id="test-en-001", title="Chapter 1", file_path="/tmp/x.json", original_text_preview="Text"),
            SegmentInfo(id="test-en-002", title="Chapter 2", file_path="/tmp/y.json", original_text_preview="More"),
        ],
    )

    known_entities = [{"name": "Beijing", "lat": 39.9, "lng": 116.4}]
    book_summary = "A travelogue describing Marco Polo's journey."

    context = build_context(
        story=story,
        segment_result=segment_result,
        segment_index=0,
        known_entities=known_entities,
        book_summary=book_summary,
    )

    # Should contain all context items
    assert "Travels" in context  # book metadata
    assert "The Beginning" in context  # chapter title
    assert "Chapter 1 / 2" in context or "1 / 2" in context  # chapter position
    assert "Chapter 2" in context  # adjacent chapter
    assert "Beijing" in context  # known entities
    assert "travelogue" in context.lower() or "marco polo" in context.lower()  # book summary


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


@pytest.mark.asyncio
async def test_extract_uses_combined_prompt(tmp_path):
    """S3 should use the combined prompt and parse entries[] response."""
    from pipeline.stages.s3_extract import extract

    story = ExtractedStory(
        id="test-en-005",
        book_slug="test",
        language="en",
        sequence=1,
        title="Chapter 1",
        original_text="The journey from Constantinople to Beijing took many months.",
        source_type="text",
        is_content=True,
        extracted=False,
    )
    path = tmp_path / "test-en-005.json"
    path.write_text(story.model_dump_json(indent=2))

    segment = SegmentInfo(
        id="test-en-005",
        title="Chapter 1",
        file_path=str(path),
        original_text_preview="The journey...",
    )
    segment_result = SegmentResultV2(book_slug="test", language="en", segments=[segment])

    llm = AsyncMock()
    llm.chat_with_tools = AsyncMock(return_value=json.dumps({
        "entries": [
            {
                "start_anchor": "The journey from Constantinople",
                "end_anchor": "took many months.",
                "is_content": True,
                "is_truncated": False,
                "story_metadata": {
                    "title": "The Journey",
                    "chapter_reference": "Chapter 1",
                    "visit_date_approximate": "1271",
                },
                "excerpt": {
                    "original": "The journey from Constantinople to Beijing.",
                    "translation": "The journey from Constantinople to Beijing.",
                },
                "summary": {
                    "chinese": "描述从君士坦丁堡到北京的旅程。",
                    "english": "Describes the journey from Constantinople to Beijing.",
                },
                "entities": {
                    "locations": [
                        {
                            "name": "Constantinople",
                            "modern_name": "Istanbul",
                            "ancient_name": "Constantinople",
                            "lat": 41.0082,
                            "lng": 28.9784,
                            "location_type": "city",
                            "one_line_summary": "Byzantine capital",
                        }
                    ],
                    "persons": ["Marco Polo"],
                    "dates": ["1271"],
                    "keywords": ["travel", "silk road"],
                },
                "credibility": {
                    "era_context": "13th century",
                    "political_context": "Mongol Empire",
                    "credibility_score": 0.8,
                },
                "annotations": [],
            }
        ]
    }))

    result = await extract(segment_result, llm)

    saved = json.loads(path.read_text())
    assert saved["extracted"] is True
    assert saved["excerpt_original"] == "The journey from Constantinople to Beijing."
    assert saved["summary_chinese"] == "描述从君士坦丁堡到北京的旅程。"
    assert saved["summary_english"] == "Describes the journey from Constantinople to Beijing."
    assert saved["persons"] == ["Marco Polo"]
    assert saved["dates"] == ["1271"]
    assert result["processed"] == 1


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


def test_subdivide_prompt_template():
    """Subdivision prompt should load and format correctly."""
    from pathlib import Path

    prompt_path = Path(__file__).parent.parent / "config" / "prompts" / "extraction_subdivide.txt"
    assert prompt_path.exists()
    template = prompt_path.read_text()
    assert "{context}" in template
    assert "{text}" in template
    assert "start_anchor" in template
    assert "end_anchor" in template

    formatted = template.format(context="Test context", text="Test text")
    assert "Test context" in formatted


def test_book_summary_prompt_template():
    """Book summary prompt should load and format correctly."""
    from pathlib import Path

    prompt_path = Path(__file__).parent.parent / "config" / "prompts" / "book_summary.txt"
    assert prompt_path.exists()
    template = prompt_path.read_text()
    assert "{text}" in template
    assert "summary" in template

    formatted = template.format(text="Preface text here")
    assert "Preface text here" in formatted
