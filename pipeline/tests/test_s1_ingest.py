import pytest
from pathlib import Path
import tempfile

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
