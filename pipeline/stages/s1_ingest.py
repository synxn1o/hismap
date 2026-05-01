from __future__ import annotations

from pathlib import Path

from pipeline.core.pdf_parser import extract_text_from_file, extract_text_from_pdf
from pipeline.models import IngestResult


async def ingest(file_path: str, config: dict) -> IngestResult:
    """Stage 1: Ingest a file and extract raw text."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        text, page_count, is_scanned = extract_text_from_pdf(file_path)

        if is_scanned:
            from pipeline.core.ocr import OCRClient

            ocr = OCRClient(config)
            ocr_text = await ocr.ocr_pdf(file_path)
            return IngestResult(
                source_file=file_path,
                file_type="pdf_scanned",
                raw_text=ocr_text,
                page_count=page_count,
                ocr_method="openai_vision",
            )

        return IngestResult(
            source_file=file_path,
            file_type="pdf_digital",
            raw_text=text,
            page_count=page_count,
            ocr_method="direct",
        )

    elif suffix in (".txt", ".md"):
        text = extract_text_from_file(file_path)
        return IngestResult(
            source_file=file_path,
            file_type="text",
            raw_text=text,
            page_count=1,
            ocr_method="direct",
        )

    else:
        raise ValueError(f"Unsupported file type: {suffix}")
