from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from pipeline.models import ExtractedStory, IngestResult, SegmentInfo, SegmentResultV2


def segment_by_headings(text: str) -> list[dict]:
    """Split text by common heading patterns. Returns list of {heading, text}."""
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
        if len(matches) >= 2:
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
            segment_text = text[last_pos:].strip()
            if segment_text:
                segments.append({
                    "heading": matches[-1].group(1).strip(),
                    "text": segment_text,
                })
            break

    if not segments:
        paragraphs = re.split(r"\n\s*\n", text)
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


def merge_ocr_stories(ocr_pages: list[dict]) -> list[dict]:
    """Merge stories across OCR pages using continues_from_prev/continues_to_next flags."""
    merged: list[dict] = []

    for page in ocr_pages:
        stories = page.get("stories", [])
        for story in stories:
            if story.get("continues_from_prev") and merged:
                # Find the matching story that has continues_to_next=True
                title = story.get("title", "")
                target = None
                for entry in merged:
                    if entry.get("continues_to_next") and entry.get("title") == title:
                        target = entry
                        break
                if target is None:
                    # Fallback: merge with last entry
                    target = merged[-1]
                target["text"] += "\n\n" + story.get("text", "")
                target["continues_to_next"] = story.get("continues_to_next", False)
            else:
                entry = {
                    "title": story.get("title", ""),
                    "text": story.get("text", ""),
                    "continues_to_next": story.get("continues_to_next", False),
                }
                if "is_content" in story:
                    entry["is_content"] = story["is_content"]
                merged.append(entry)

    return merged


def make_segment_id(book_slug: str, language: str, sequence: int) -> str:
    return f"{book_slug}-{language}-{sequence:03d}"


def save_segment_json(story: ExtractedStory, output_dir: str) -> str:
    """Save story as JSON file. Returns file path."""
    out_path = Path(output_dir) / f"{story.id}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(story.model_dump_json(indent=2), encoding="utf-8")
    return str(out_path)


async def segment(
    ingest_result: IngestResult,
    output_dir: str | None = None,
    llm=None,
) -> SegmentResultV2:
    """Stage 2: Segment text into stories, assign IDs, save JSON files.

    Three paths:
    A. Text with headings -> regex split
    B. Text without headings -> LLM fallback
    C. OCR results -> merge by continuation flags
    """
    book_slug = ingest_result.book_slug
    language = ingest_result.detected_language
    if output_dir is None:
        output_dir = str(Path(__file__).parent.parent / "output" / book_slug)

    raw_stories: list[dict] = []

    # Path C: OCR results
    if ingest_result.ocr_pages:
        raw_stories = merge_ocr_stories(ingest_result.ocr_pages)
        source_type = "ocr"
    else:
        # Path A: Try regex heading detection
        headings = segment_by_headings(ingest_result.raw_text)

        if len(headings) >= 2 and headings[0]["heading"] is not None:
            raw_stories = [{"title": h["heading"], "text": h["text"]} for h in headings]
            source_type = "text"
        elif llm is not None:
            # Path B: LLM fallback
            raw_stories = await _segment_by_llm(ingest_result.raw_text, llm)
            source_type = "text"
        else:
            raw_stories = [{"title": None, "text": h["text"]} for h in headings]
            source_type = "text"

    segments = []
    now = datetime.now(timezone.utc).isoformat()

    for i, story in enumerate(raw_stories):
        seq = i + 1
        sid = make_segment_id(book_slug, language, seq)
        title = story.get("title") or f"Segment {seq}"
        text = story.get("text", "")

        extracted = ExtractedStory(
            id=sid,
            book_slug=book_slug,
            language=language,
            sequence=seq,
            title=title,
            original_text=text,
            source_type=source_type,
            created_at=now,
            extracted=False,
        )

        file_path = save_segment_json(extracted, output_dir)

        segments.append(SegmentInfo(
            id=sid,
            title=title,
            file_path=file_path,
            original_text_preview=text[:200],
        ))

    return SegmentResultV2(
        book_slug=book_slug,
        language=language,
        segments=segments,
    )


async def _segment_by_llm(text: str, llm) -> list[dict]:
    """LLM fallback: split text into chunks, ask LLM to identify stories."""
    chunks = _split_into_chunks(text, max_chars=20000)
    all_stories = []

    for chunk in chunks:
        prompt = f"""Identify individual stories/narratives in this text.
Return JSON:
{{
  "stories": [
    {{
      "title": "story title",
      "text": "full story text",
      "is_content": true,
      "continues_from_prev": false,
      "continues_to_next": false
    }}
  ]
}}
Set is_content=false for non-narrative sections: table of contents, preface, index, bibliography, publisher info, translator's notes.
Use continues_from_prev/continues_to_next flags for stories that span chunk boundaries.

TEXT:
{chunk}"""
        try:
            raw = await llm.extract_json(prompt)
            data = json.loads(raw)
            all_stories.extend(data.get("stories", []))
        except Exception:
            all_stories.append({"title": None, "text": chunk, "is_content": True})

    merged = merge_ocr_stories([{"stories": all_stories}])

    # Filter out non-content stories
    return [s for s in merged if s.get("is_content", True)]


def _split_into_chunks(text: str, max_chars: int = 20000) -> list[str]:
    """Split text into chunks at paragraph boundaries."""
    paragraphs = re.split(r"\n\s*\n", text)
    chunks = []
    current = []
    current_len = 0

    for para in paragraphs:
        if current_len + len(para) > max_chars and current:
            chunks.append("\n\n".join(current))
            current = [para]
            current_len = len(para)
        else:
            current.append(para)
            current_len += len(para)

    if current:
        chunks.append("\n\n".join(current))

    return chunks or [text]
