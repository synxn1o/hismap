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

        try:
            raw = await llm.chat_with_tools(
                prompt=prompt,
                system="You are a historical text analysis expert.",
                tools=EXTRACTION_TOOLS,
                response_format={"type": "json_object"},
            )

            if raw.startswith("```"):
                lines = raw.split("\n")
                lines = [l for l in lines if not l.startswith("```")]
                raw = "\n".join(lines)

            extracted = json.loads(raw)

            story.book_metadata = extracted.get("book_metadata")
            story.story_metadata = extracted.get("story_metadata")
            story.entities = extracted.get("entities")
            story.translations = extracted.get("translations")
            story.credibility = extracted.get("credibility")
            story.annotations = extracted.get("annotations")
            story.extracted = True
            story.error = None

            stats["processed"] += 1

        except Exception as e:
            story.extracted = False
            story.error = str(e)[:500]
            stats["failed"] += 1

        story_path.write_text(story.model_dump_json(indent=2), encoding="utf-8")

    return stats
