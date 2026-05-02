import pytest
import json
from pathlib import Path
import tempfile
from unittest.mock import AsyncMock

from pipeline.core.pdf_parser import extract_text_from_file


def test_extract_text_from_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("马可·波罗游记\n\n在这座城市里...")
        f.flush()
        text = extract_text_from_file(f.name)
        assert "马可·波罗" in text
    Path(f.name).unlink()


def test_ingest_assigns_book_slug():
    """Test that book_slug is derived from filename."""
    from pipeline.stages.s1_ingest import ingest

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Some text content for testing purposes.")
        f.flush()
        config = {"ocr": {"base_url": "x", "api_key": "x", "model": "x"}}
        import asyncio
        result = asyncio.run(ingest(f.name, config))
        assert result.book_slug != ""
        assert " " not in result.book_slug
    Path(f.name).unlink()


def test_ingest_detects_language():
    """Test that detected_language is set."""
    from pipeline.stages.s1_ingest import ingest

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("The quick brown fox jumps over the lazy dog. This is a test of language detection.")
        f.flush()
        config = {"ocr": {"base_url": "x", "api_key": "x", "model": "x"}}
        import asyncio
        result = asyncio.run(ingest(f.name, config))
        assert result.detected_language != "unknown"
    Path(f.name).unlink()


@pytest.mark.asyncio
async def test_extract_book_summary_from_preface():
    """Book summary extraction should summarize preface text."""
    from pipeline.stages.book_summary import extract_book_summary

    llm = AsyncMock()
    llm.extract_json = AsyncMock(return_value=json.dumps({
        "summary": "Marco Polo's travelogue describes his journey from Venice to the court of Kublai Khan.",
        "author_background": "Venetian merchant who spent 24 years in Asia",
        "journey_description": "Venice to China and back via maritime route",
        "time_period": "1271-1295",
        "significance": "One of the first European accounts of Asia",
    }))

    result = await extract_book_summary("Preface text about Marco Polo's travels...", llm)
    assert "Marco Polo" in result
    assert len(result) > 50


def test_identify_preface_pages():
    """Should identify preface/序言 pages from text content."""
    from pipeline.stages.book_summary import identify_preface

    # Text with preface indicators
    text = """序言

    本书记录了马可·波罗从威尼斯到元朝上都的旅程...

    第一章 从威尼斯出发

    1271年，我们离开了威尼斯..."""

    preface, remaining = identify_preface(text)
    assert "序言" in preface or "马可·波罗" in preface
    assert "第一章" in remaining or "1271年" in remaining
