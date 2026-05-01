from __future__ import annotations

import re
import uuid

from langdetect import detect

from pipeline.models import IngestResult, SegmentResult, TextSegment


def detect_language(text: str) -> str:
    """Detect language of text segment."""
    try:
        return detect(text)
    except Exception:
        return "unknown"


def segment_by_headings(text: str) -> list[dict]:
    """Split text by common heading patterns."""
    # Match patterns like: "Chapter 1", "第1章", "I.", "一、", numbered headings
    patterns = [
        r"(?:^|\n)(Chapter\s+\d+.*?)\n",
        r"(?:^|\n)(第\d+[章节篇].*?)\n",
        r"(?:^|\n)([IVX]+\.\s+.*?)\n",
        r"(?:^|\n)([一二三四五六七八九十]+[、.]\s+.*?)\n",
    ]

    segments = []
    last_pos = 0

    for pattern in patterns:
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        if len(matches) >= 2:  # At least 2 matches to be useful
            for i, match in enumerate(matches):
                start = match.start()
                if i > 0:
                    segment_text = text[last_pos:start].strip()
                    if segment_text:
                        segments.append({
                            "heading": matches[i - 1].group(1).strip(),
                            "text": segment_text,
                        })
                last_pos = start
            # Last segment
            segment_text = text[last_pos:].strip()
            if segment_text:
                segments.append({
                    "heading": matches[-1].group(1).strip(),
                    "text": segment_text,
                })
            break

    if not segments:
        # Fallback: split by double newlines (paragraph groups)
        paragraphs = re.split(r"\n\s*\n", text)
        # Group paragraphs into segments of ~500-2000 chars
        current = []
        current_len = 0
        for para in paragraphs:
            if current_len + len(para) > 2000 and current:
                segments.append({"heading": None, "text": "\n\n".join(current)})
                current = [para]
                current_len = len(para)
            else:
                current.append(para)
                current_len += len(para)
        if current:
            segments.append({"heading": None, "text": "\n\n".join(current)})

    return segments


async def segment(ingest_result: IngestResult) -> SegmentResult:
    """Stage 2: Segment text into logical entries."""
    raw_segments = segment_by_headings(ingest_result.raw_text)

    segments = []
    for i, seg in enumerate(raw_segments):
        lang = detect_language(seg["text"][:500])
        segments.append(TextSegment(
            segment_id=f"s{i + 1}",
            text=seg["text"],
            language=lang,
            heading=seg["heading"],
        ))

    return SegmentResult(segments=segments)
