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
