from __future__ import annotations

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

from pipeline.models import IngestResult, SegmentResultV2


def _make_ingest(raw_text: str, book_slug: str = "test-book", language: str = "en",
                 ocr_pages: list | None = None, file_type: str = "text") -> IngestResult:
    return IngestResult(
        source_file="/tmp/test.txt",
        file_type=file_type,
        raw_text=raw_text,
        page_count=1,
        ocr_method="direct",
        book_slug=book_slug,
        detected_language=language,
        ocr_pages=ocr_pages or [],
    )


class TestSegmentByHeadings:
    def test_splits_by_chapter_markers(self):
        from pipeline.stages.s2_segment import segment_by_headings

        text = "Chapter 1 - Introduction\n\nSome text here.\n\nChapter 2 - The Journey\n\nMore text."
        segments = segment_by_headings(text)
        assert len(segments) >= 2
        assert segments[0]["heading"] is not None

    def test_fallback_when_no_headings(self):
        from pipeline.stages.s2_segment import segment_by_headings

        text = "Just a bunch of paragraphs without any headings.\n\nAnother paragraph here."
        segments = segment_by_headings(text)
        assert len(segments) >= 1


class TestOCRStoriesMerge:
    def test_merges_continuing_stories(self):
        from pipeline.stages.s2_segment import merge_ocr_stories

        ocr_pages = [
            {
                "text": "Page 1",
                "stories": [
                    {"title": "Story A", "text": "Part 1", "continues_from_prev": False, "continues_to_next": True},
                    {"title": "Story B", "text": "Standalone", "continues_from_prev": False, "continues_to_next": False},
                ],
            },
            {
                "text": "Page 2",
                "stories": [
                    {"title": "Story A", "text": "Part 2", "continues_from_prev": True, "continues_to_next": False},
                ],
            },
        ]
        merged = merge_ocr_stories(ocr_pages)
        assert len(merged) == 2  # Story A (merged) + Story B
        assert merged[0]["title"] == "Story A"
        assert "Part 1" in merged[0]["text"]
        assert "Part 2" in merged[0]["text"]

    def test_no_merge_without_flags(self):
        from pipeline.stages.s2_segment import merge_ocr_stories

        ocr_pages = [
            {
                "text": "Page 1",
                "stories": [
                    {"title": "A", "text": "Text A", "continues_from_prev": False, "continues_to_next": False},
                ],
            },
            {
                "text": "Page 2",
                "stories": [
                    {"title": "B", "text": "Text B", "continues_from_prev": False, "continues_to_next": False},
                ],
            },
        ]
        merged = merge_ocr_stories(ocr_pages)
        assert len(merged) == 2


class TestSegmentIDAssignment:
    def test_id_format(self):
        from pipeline.stages.s2_segment import make_segment_id

        sid = make_segment_id("marco-polo", "chs", 1)
        assert sid == "marco-polo-chs-001"

    def test_id_pads_sequence(self):
        from pipeline.stages.s2_segment import make_segment_id

        assert make_segment_id("book", "en", 42) == "book-en-042"


class TestJSONFileSave:
    def test_saves_json_file(self):
        from pipeline.stages.s2_segment import save_segment_json
        from pipeline.models import ExtractedStory

        with tempfile.TemporaryDirectory() as tmpdir:
            story = ExtractedStory(
                id="test-en-001",
                book_slug="test",
                language="en",
                sequence=1,
                title="Chapter 1",
                original_text="Story text",
                source_type="text",
            )
            path = save_segment_json(story, tmpdir)
            assert Path(path).exists()
            saved = json.loads(Path(path).read_text())
            assert saved["id"] == "test-en-001"
            assert saved["extracted"] is False


@pytest.mark.asyncio
async def test_segment_text_path():
    """Test full segment function with text input (regex headings)."""
    from pipeline.stages.s2_segment import segment

    text = "Chapter 1 - Intro\n\nHello world.\n\nChapter 2 - Outro\n\nGoodbye."
    ingest_result = _make_ingest(text, language="en")

    with tempfile.TemporaryDirectory() as tmpdir:
        result = await segment(ingest_result, output_dir=tmpdir)
        assert result.book_slug == "test-book"
        assert len(result.segments) >= 2
        for seg in result.segments:
            assert Path(seg.file_path).exists()


@pytest.mark.asyncio
async def test_segment_ocr_path():
    """Test segment function with OCR pages."""
    from pipeline.stages.s2_segment import segment

    ocr_pages = [
        {
            "text": "Page 1",
            "stories": [
                {"title": "Tale 1", "text": "Once upon a time...", "continues_from_prev": False, "continues_to_next": False},
            ],
        },
    ]
    ingest_result = _make_ingest("", ocr_pages=ocr_pages, file_type="pdf_scanned")

    with tempfile.TemporaryDirectory() as tmpdir:
        result = await segment(ingest_result, output_dir=tmpdir)
        assert len(result.segments) == 1
        assert "Tale" in result.segments[0].title


@pytest.mark.asyncio
async def test_segment_by_llm_filters_non_content():
    """LLM fallback should exclude non-content stories from output."""
    from pipeline.stages.s2_segment import _segment_by_llm

    llm = AsyncMock()
    llm.extract_json = AsyncMock(return_value=json.dumps({
        "stories": [
            {"title": "Table of Contents", "text": "Chapter 1... 1\nChapter 2... 15", "is_content": False},
            {"title": "Chapter 1", "text": "The journey began in 1271.", "is_content": True},
            {"title": "Bibliography", "text": "See also: Smith 2020", "is_content": False},
        ]
    }))

    stories = await _segment_by_llm("Some text", llm)
    # Only content stories should remain
    assert len(stories) == 1
    assert stories[0]["title"] == "Chapter 1"
