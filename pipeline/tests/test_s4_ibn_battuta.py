"""Test s4 output with the converted ibn_battuta_places_sample_10 data.

Runs output_to_db against the 10 ExtractedStory files produced by
test_book/convert_to_pipeline.py, verifying Book/Author/Location/Entry creation.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline.models import SegmentResultV2

SEGMENTS_FILE = Path(__file__).parent.parent / "output" / "ibn_battuta_segments.json"


def _make_model_mock(mock_cls):
    """Make mock_cls record constructor kwargs and return an object with those attrs."""
    def _factory(**kwargs):
        obj = MagicMock()
        for k, v in kwargs.items():
            setattr(obj, k, v)
        obj.id = 1
        return obj
    mock_cls.side_effect = _factory


@pytest.fixture
def ibn_battuta_segments():
    """Load the real SegmentResultV2 produced by convert_to_pipeline.py."""
    data = json.loads(SEGMENTS_FILE.read_text(encoding="utf-8"))
    seg_result = SegmentResultV2(**data)

    for seg in seg_result.segments:
        assert Path(seg.file_path).exists(), f"Missing story file: {seg.file_path}"

    return seg_result


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()

    added = []
    session.add = MagicMock(side_effect=added.append)

    return session, added


@pytest.mark.asyncio
async def test_s4_ibn_battuta_writes_10_entries(ibn_battuta_segments, mock_session):
    """Verify s4 creates 1 Book, 1 Author, 10 Locations, 10 JournalEntries."""
    from pipeline.stages.s4_output import output_to_db

    session, added = mock_session

    with patch("pipeline.stages.s4_output.Book") as MockBook, \
         patch("pipeline.stages.s4_output.Author") as MockAuthor, \
         patch("pipeline.stages.s4_output.Location") as MockLocation, \
         patch("pipeline.stages.s4_output.JournalEntry") as MockJournalEntry, \
         patch("pipeline.stages.s4_output.entry_authors"), \
         patch("pipeline.stages.s4_output.entry_locations"):

        _make_model_mock(MockBook)
        _make_model_mock(MockAuthor)
        _make_model_mock(MockLocation)
        _make_model_mock(MockJournalEntry)

        result = await output_to_db(ibn_battuta_segments, session)

    assert result.books == 1
    assert result.authors == 1
    assert result.locations == 10
    assert result.entries == 10
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_s4_ibn_battuta_location_names(ibn_battuta_segments, mock_session):
    """Verify the 10 locations include all expected place names."""
    from pipeline.stages.s4_output import output_to_db

    session, added = mock_session

    with patch("pipeline.stages.s4_output.Book") as MockBook, \
         patch("pipeline.stages.s4_output.Author") as MockAuthor, \
         patch("pipeline.stages.s4_output.Location") as MockLocation, \
         patch("pipeline.stages.s4_output.JournalEntry") as MockJournalEntry, \
         patch("pipeline.stages.s4_output.entry_authors"), \
         patch("pipeline.stages.s4_output.entry_locations"):

        _make_model_mock(MockBook)
        _make_model_mock(MockAuthor)
        _make_model_mock(MockLocation)
        _make_model_mock(MockJournalEntry)

        await output_to_db(ibn_battuta_segments, session)

    location_names = sorted(
        obj.name for obj in added
        if isinstance(getattr(obj, "latitude", None), float)
    )

    expected = sorted([
        "Tanjiers", "Misr (Caïro)", "Damascus", "Makdashu", "Kulwā",
        "Aden", "Zaila", "Mambasa", "Zafār", "Nazwā",
    ])
    assert location_names == expected


@pytest.mark.asyncio
async def test_s4_ibn_battuta_book_metadata(ibn_battuta_segments, mock_session):
    """Verify Book is created with Ibn Battuta metadata."""
    from pipeline.stages.s4_output import output_to_db

    session, added = mock_session

    with patch("pipeline.stages.s4_output.Book") as MockBook, \
         patch("pipeline.stages.s4_output.Author") as MockAuthor, \
         patch("pipeline.stages.s4_output.Location") as MockLocation, \
         patch("pipeline.stages.s4_output.JournalEntry") as MockJournalEntry, \
         patch("pipeline.stages.s4_output.entry_authors"), \
         patch("pipeline.stages.s4_output.entry_locations"):

        _make_model_mock(MockBook)
        _make_model_mock(MockAuthor)
        _make_model_mock(MockLocation)
        _make_model_mock(MockJournalEntry)

        await output_to_db(ibn_battuta_segments, session)

    book_obj = next(obj for obj in added if hasattr(obj, "source_text"))
    assert "Ibn Battuta" in book_obj.title or "Travels" in book_obj.title
    assert book_obj.author == "Ibn Battuta"
