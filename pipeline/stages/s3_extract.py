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
