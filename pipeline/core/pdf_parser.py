from __future__ import annotations

import fitz  # PyMuPDF


def extract_text_from_pdf(pdf_path: str) -> tuple[str, int, bool]:
    """Extract text from PDF. Returns (text, page_count, is_scanned)."""
    doc = fitz.open(pdf_path)
    page_count = len(doc)
    text_parts = []
    total_chars = 0

    for page in doc:
        page_text = page.get_text()
        text_parts.append(page_text)
        total_chars += len(page_text.strip())

    doc.close()
    full_text = "\n\n".join(text_parts)

    # Heuristic: if very few chars per page, it's likely scanned
    avg_chars = total_chars / page_count if page_count > 0 else 0
    is_scanned = avg_chars < 50  # less than 50 chars per page = scanned

    return full_text, page_count, is_scanned


def extract_text_from_file(file_path: str) -> str:
    """Read plain text file."""
    with open(file_path, encoding="utf-8") as f:
        return f.read()
