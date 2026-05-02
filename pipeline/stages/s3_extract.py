from __future__ import annotations

import json
from pathlib import Path

from pipeline.core.llm_client import LLMClient
from pipeline.models import ExtractedStory, SegmentResultV2

PROMPTS_DIR = Path(__file__).parent.parent / "config" / "prompts"

EXTRACTION_TOOLS = [
    {
        "type": "web_search",
        "max_keyword": 6,
        "force_search": False,
        "limit": 6,
    }
]


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.txt").read_text()


def build_context(
    story: ExtractedStory,
    segment_result: SegmentResultV2,
    segment_index: int,
    known_entities: list[dict] | None = None,
    book_summary: str | None = None,
) -> str:
    """Build context string for the combined extraction prompt."""
    parts = []

    # 1. Book summary
    if book_summary:
        parts.append(f"BOOK SUMMARY:\n{book_summary}")

    # 2. Book metadata
    if story.book_metadata:
        bm = story.book_metadata
        parts.append(f"BOOK METADATA:\nTitle: {bm.get('title', 'Unknown')}\nAuthor: {bm.get('author', 'Unknown')}\nDynasty/Era: {bm.get('dynasty', 'Unknown')}")

    # 3. Current chapter title
    if story.chapter_title:
        parts.append(f"CURRENT CHAPTER: {story.chapter_title}")

    # 4. Chapter position
    total = len(segment_result.segments)
    parts.append(f"CHAPTER POSITION: {segment_index + 1} / {total}")

    # 5. Adjacent chapter titles
    if segment_index > 0:
        prev_title = segment_result.segments[segment_index - 1].title
        parts.append(f"PREVIOUS CHAPTER: {prev_title}")
    if segment_index < total - 1:
        next_title = segment_result.segments[segment_index + 1].title
        parts.append(f"NEXT CHAPTER: {next_title}")

    # 6. Known entities
    if known_entities:
        entity_str = ", ".join(f"{e['name']} ({e.get('lat', '?')}, {e.get('lng', '?')})" for e in known_entities[:20])
        parts.append(f"KNOWN ENTITIES (for consistency):\n{entity_str}")

    # 7. Source language rules
    lang_rules = {
        "zh-classical": "Source is classical Chinese. Extract modern Chinese and English translations.",
        "zh-modern": "Source is modern Chinese. Extract English translation only.",
        "arabic": "Source is Arabic. Extract English translation only.",
        "en": "Source is English. No translation needed.",
    }
    lang = story.language
    parts.append(f"SOURCE LANGUAGE: {lang}\n{lang_rules.get(lang, 'Extract appropriate translations.')}")

    return "\n\n".join(parts)


async def extract(segment_result: SegmentResultV2, llm: LLMClient) -> dict:
    """Stage 3: Extract all data from each story via single LLM call.

    Reads each story's JSON file, calls LLM once per story with web_search tool,
    merges response back into the JSON, sets extracted=true.

    Returns stats dict: {processed, skipped, failed}.
    """
    prompt_template = load_prompt("extraction")
    stats = {"processed": 0, "skipped": 0, "failed": 0}

    for seg_info in segment_result.segments:
        story_path = Path(seg_info.file_path)
        if not story_path.exists():
            stats["failed"] += 1
            continue

        story_data = json.loads(story_path.read_text(encoding="utf-8"))
        story = ExtractedStory(**story_data)

        if story.extracted:
            stats["skipped"] += 1
            continue

        if not story.is_content:
            story.extracted = True
            story.error = "non_content"
            story_path.write_text(story.model_dump_json(indent=2), encoding="utf-8")
            stats["skipped"] += 1
            print(f"    [{seg_info.id}] skipped (non-content)")
            continue

        prompt = prompt_template.format(text=story.original_text)
        print(f"    [{seg_info.id}] extracting...", end=" ", flush=True)

        try:
            try:
                raw = await llm.chat_with_tools(
                    prompt=prompt,
                    system="You are a historical text analysis expert.",
                    tools=EXTRACTION_TOOLS,
                    response_format={"type": "json_object"},
                    max_tokens=8192,
                )
            except Exception:
                # Fallback: tools not supported by this API, use plain chat
                raw = await llm.extract_json(
                    prompt=prompt,
                    system="You are a historical text analysis expert. Be concise. Return ONLY valid JSON.",
                    max_tokens=8192,
                )

            if not raw or not raw.strip():
                raise ValueError("LLM returned empty response")

            if raw.startswith("```"):
                lines = raw.split("\n")
                lines = [l for l in lines if not l.startswith("```")]
                raw = "\n".join(lines)

            try:
                extracted = json.loads(raw)
            except json.JSONDecodeError:
                # Try to recover malformed/truncated JSON
                fixed = raw.rstrip()
                # Remove trailing comma
                if fixed.endswith(','):
                    fixed = fixed[:-1]
                # Remove trailing comma before ] or }
                import re
                fixed = re.sub(r',(\s*[\]}])', r'\1', fixed)
                # Close any open strings
                if fixed.count('"') % 2 != 0:
                    fixed += '"'
                # Close open arrays and objects
                open_brackets = fixed.count('[') - fixed.count(']')
                open_braces = fixed.count('{') - fixed.count('}')
                fixed += ']' * max(0, open_brackets)
                fixed += '}' * max(0, open_braces)
                extracted = json.loads(fixed)

            story.book_metadata = extracted.get("book_metadata")
            story.story_metadata = extracted.get("story_metadata")
            story.entities = extracted.get("entities")
            story.translations = extracted.get("translations")
            story.credibility = extracted.get("credibility")
            story.annotations = extracted.get("annotations")
            story.extracted = True
            story.error = None

            stats["processed"] += 1
            print("OK")

        except Exception as e:
            story.extracted = False
            story.error = str(e)[:500]
            stats["failed"] += 1
            print(f"FAIL: {story.error[:80]}")

        story_path.write_text(story.model_dump_json(indent=2), encoding="utf-8")

    return stats
