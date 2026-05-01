from __future__ import annotations

import re
from pathlib import Path

from langdetect import detect

from pipeline.core.pdf_parser import extract_text_from_file, extract_text_from_pdf
from pipeline.models import IngestResult


def make_book_slug(file_path: str) -> str:
    """Derive a normalized book slug from filename."""
    name = Path(file_path).stem.lower()
    # Keep unicode word chars (letters, digits, CJK), replace separators with hyphens
    slug = re.sub(r"[^\w]+", "-", name, flags=re.UNICODE).strip("-")
    return slug or "unknown"


def detect_language(text: str) -> str:
    """Detect language from first 1000 chars."""
    try:
        return detect(text[:1000])
    except Exception:
        return "unknown"


async def ingest(file_path: str, config: dict) -> IngestResult:
    """Stage 1: Ingest a file and extract raw text.

    Auto-detects: text files read directly, digital PDFs extract text,
    scanned PDFs go through structured OCR.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()
    book_slug = make_book_slug(file_path)

    if suffix == ".pdf":
        text, page_count, is_scanned = extract_text_from_pdf(file_path)

        if is_scanned:
            from pipeline.core.ocr import OCRClient

            ocr = OCRClient(config)
            ocr_pages = await ocr.ocr_pdf_structured(file_path)
            raw_text = "\n\n".join(
                page.get("text", "") for page in ocr_pages
            )
            lang = detect_language(raw_text)
            return IngestResult(
                source_file=file_path,
                file_type="pdf_scanned",
                raw_text=raw_text,
                page_count=page_count,
                ocr_method="vision_llm",
                book_slug=book_slug,
                detected_language=lang,
                ocr_pages=ocr_pages,
            )

        lang = detect_language(text)
        return IngestResult(
            source_file=file_path,
            file_type="pdf_digital",
            raw_text=text,
            page_count=page_count,
            ocr_method="direct",
            book_slug=book_slug,
            detected_language=lang,
        )

    elif suffix == ".rtf":
        from striprtf.striprtf import rtf_to_text

        raw = path.read_text(encoding="utf-8", errors="replace")
        text = rtf_to_text(raw)
        lang = detect_language(text)
        return IngestResult(
            source_file=file_path,
            file_type="text",
            raw_text=text,
            page_count=1,
            ocr_method="direct",
            book_slug=book_slug,
            detected_language=lang,
        )

    elif suffix in (".txt", ".md"):
        text = extract_text_from_file(file_path)
        lang = detect_language(text)
        return IngestResult(
            source_file=file_path,
            file_type="text",
            raw_text=text,
            page_count=1,
            ocr_method="direct",
            book_slug=book_slug,
            detected_language=lang,
        )

    else:
        raise ValueError(f"Unsupported file type: {suffix}")
