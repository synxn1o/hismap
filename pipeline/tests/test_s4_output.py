from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from pipeline.models import ExtractedStory, SegmentInfo, SegmentResultV2


@pytest.fixture
def story_files(tmp_path):
    """Create two story JSON files with extracted data."""
    stories = []
    for i, title in enumerate(["Chapter 1 - Arrival", "Chapter 2 - Departure"], 1):
        story = ExtractedStory(
            id=f"test-en-{i:03d}",
            book_slug="test",
            language="en",
            sequence=i,
            title=title,
            original_text=f"Story text {i}",
            source_type="text",
            extracted=True,
            book_metadata={
                "title": "Test Book",
                "author": "Test Author",
                "dynasty": "Ming",
                "era_start": 1400,
                "era_end": 1500,
                "author_biography": "A test author",
            },
            story_metadata={
                "title": title,
                "chapter_reference": f"Chapter {i}",
                "visit_date_approximate": "1405",
            },
            entities={
                "locations": [
                    {
                        "name": "Beijing",
                        "modern_name": "Beijing",
                        "ancient_name": "Dadu",
                        "lat": 39.9042,
                        "lng": 116.4074,
                        "location_type": "city",
                        "one_line_summary": "Capital city",
                    }
                ],
                "persons": ["Emperor"],
                "dates": ["1405"],
                "keywords": ["travel"],
            },
            translations={
                "modern_chinese": "现代中文翻译",
                "english": "English translation",
            },
            credibility={
                "era_context": "Ming Dynasty",
                "political_context": "Stable",
                "religious_context": "Buddhism",
                "social_environment": "Trade",
                "credibility_score": 0.8,
                "notes": "Reliable",
            },
            annotations=[
                {"source": "web_search", "query": "test", "url": "https://example.com", "snippet": "info"},
            ],
        )
        path = tmp_path / f"test-en-{i:03d}.json"
        path.write_text(story.model_dump_json(indent=2))
        stories.append(SegmentInfo(
            id=f"test-en-{i:03d}",
            title=title,
            file_path=str(path),
            original_text_preview=f"Story text {i}",
        ))
    return SegmentResultV2(book_slug="test", language="en", segments=stories)


@pytest.mark.asyncio
async def test_output_writes_to_db(story_files):
    """Test that output reads JSON files and writes to DB."""
    from pipeline.stages.s4_output import output_to_db

    mock_session = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.execute = AsyncMock()

    added_objects = []
    def track_add(obj):
        added_objects.append(obj)
    mock_session.add = MagicMock(side_effect=track_add)

    with patch("pipeline.stages.s4_output.Book") as MockBook, \
         patch("pipeline.stages.s4_output.Author") as MockAuthor, \
         patch("pipeline.stages.s4_output.Location") as MockLocation, \
         patch("pipeline.stages.s4_output.JournalEntry") as MockJournalEntry, \
         patch("pipeline.stages.s4_output.entry_authors") as mock_ea, \
         patch("pipeline.stages.s4_output.entry_locations") as mock_el:

        MockBook.return_value = MagicMock(id=1)
        MockAuthor.return_value = MagicMock(id=1)
        MockLocation.return_value = MagicMock(id=1)
        MockJournalEntry.return_value = MagicMock(id=1)

        result = await output_to_db(story_files, mock_session)

    assert result.books == 1
    assert result.authors == 1
    assert result.locations >= 1
    assert result.entries == 2
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_output_skips_non_content_stories(tmp_path):
    """S4 should not create JournalEntry for non-content stories."""
    from pipeline.stages.s4_output import output_to_db

    content_story = ExtractedStory(
        id="test-en-001",
        book_slug="test",
        language="en",
        sequence=1,
        title="Chapter 1",
        original_text="Journey text",
        source_type="text",
        extracted=True,
        is_content=True,
        book_metadata={"title": "Test Book", "author": "Author"},
        story_metadata={"title": "Chapter 1"},
        entities={"locations": [], "keywords": ["travel"]},
        translations={"modern_chinese": None, "english": "Journey text"},
        credibility={"era_context": "Medieval"},
    )
    non_content_story = ExtractedStory(
        id="test-en-002",
        book_slug="test",
        language="en",
        sequence=2,
        title="TOC",
        original_text="Chapter 1... 1",
        source_type="text",
        extracted=True,
        is_content=False,
    )

    content_path = tmp_path / "test-en-001.json"
    content_path.write_text(content_story.model_dump_json(indent=2))
    non_content_path = tmp_path / "test-en-002.json"
    non_content_path.write_text(non_content_story.model_dump_json(indent=2))

    segment_result = SegmentResultV2(
        book_slug="test",
        language="en",
        segments=[
            SegmentInfo(id="test-en-001", title="Chapter 1", file_path=str(content_path), original_text_preview="Journey"),
            SegmentInfo(id="test-en-002", title="TOC", file_path=str(non_content_path), original_text_preview="Chapter 1"),
        ],
    )

    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()

    with patch("pipeline.stages.s4_output.Book") as MockBook, \
         patch("pipeline.stages.s4_output.Author") as MockAuthor, \
         patch("pipeline.stages.s4_output.JournalEntry") as MockJE, \
         patch("pipeline.stages.s4_output.Location") as MockLoc:
        MockBook.return_value = MagicMock(id=1)
        MockAuthor.return_value = MagicMock(id=1)
        MockJE.return_value = MagicMock(id=1)
        MockLoc.return_value = MagicMock(id=1)

        result = await output_to_db(segment_result, session)

    # Only 1 entry should be created (the content story)
    assert result.entries == 1
