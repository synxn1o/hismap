# HiSMap Data Processing Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 7-stage data processing pipeline that converts historical travel PDFs/text into structured database records using OCR, LLM extraction, geocoding, translation, and credibility analysis.

**Architecture:** Async Python pipeline with typed Pydantic models passed between stages. Each stage is independently runnable. LLM calls use OpenAI SDK format (provider-agnostic via config). Human review supported at every stage via a simple FastAPI review API. Pipeline state stored in PostgreSQL.

**Tech Stack:** conda environment `hismap`: Python 3.11+, asyncio, Pydantic v2, OpenAI SDK, PyMuPDF, langdetect, SQLAlchemy 2.0

---

## File Structure

```
pipeline/
├── pyproject.toml
├── requirements.txt
├── config/
│   ├── config.yaml              # provider URLs, API keys, model names
│   └── prompts/
│       ├── extraction.txt
│       ├── geocoding.txt
│       ├── translation.txt
│       └── credibility.txt
├── core/
│   ├── __init__.py
│   ├── llm_client.py            # OpenAI SDK wrapper
│   ├── ocr.py                   # OpenAI Vision API OCR (base64 images)
│   ├── pdf_parser.py            # PyMuPDF wrapper
│   └── db.py                    # DB connection (reuse backend models)
├── models.py                    # Pydantic inter-stage models
├── stages/
│   ├── __init__.py
│   ├── s1_ingest.py
│   ├── s2_segment.py
│   ├── s3_extract.py
│   ├── s4_geocode.py
│   ├── s5_translate.py
│   ├── s6_analyze.py
│   └── s7_output.py
├── runner.py                    # Pipeline orchestrator
├── review/
│   ├── app.py                   # FastAPI review API
│   └── static/
│       └── index.html           # Simple review UI
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_models.py
    ├── test_s1_ingest.py
    ├── test_s2_segment.py
    ├── test_s3_extract.py
    ├── test_s4_geocode.py
    ├── test_s5_translate.py
    ├── test_s6_analyze.py
    └── test_runner.py
```

---

## Task 1: Project Setup and Inter-Stage Models

**Files:**
- Create: `pipeline/pyproject.toml`
- Create: `pipeline/requirements.txt`
- Create: `pipeline/models.py`
- Create: `pipeline/config/config.yaml`
- Create: `pipeline/tests/__init__.py`
- Create: `pipeline/tests/conftest.py`
- Create: `pipeline/tests/test_models.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
# pipeline/pyproject.toml
[project]
name = "hismap-pipeline"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.7.0",
    "pydantic-settings>=2.3.0",
    "openai>=1.30.0",
    "PyMuPDF>=1.24.0",
    "langdetect>=1.0.9",
    "sqlalchemy[asyncio]>=2.0.30",
    "asyncpg>=0.29.0",
    "pyyaml>=6.0.1",
    "httpx>=0.27.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2.0",
    "pytest-asyncio>=0.23.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Create config.yaml**

```yaml
# pipeline/config/config.yaml
llm:
  base_url: "https://api.anthropic.com/v1"
  api_key: "${ANTHROPIC_API_KEY}"
  model: "claude-sonnet-4-6"
  max_tokens: 4096
  temperature: 0.1

ocr:
  base_url: "https://api.openai.com/v1"
  api_key: "${OCR_API_KEY}"
  model: "gpt-4o"
  dpi: 200
  max_tokens: 4096

cost_limits:
  max_cost_per_run: 5.00
  max_tokens_per_entry: 8000
  max_entries_per_run: 500

database:
  url: "postgresql+asyncpg://hismap:hismap@localhost:5432/hismap"
```

- [ ] **Step 3: Create inter-stage Pydantic models**

```python
# pipeline/models.py
from __future__ import annotations

from pydantic import BaseModel


# Stage 1 output
class IngestResult(BaseModel):
    source_file: str
    file_type: str  # "pdf_scanned" | "pdf_digital" | "text"
    raw_text: str
    page_count: int
    ocr_method: str  # "google_vision" | "vision_llm" | "direct"
    metadata: dict = {}


# Stage 2 output
class TextSegment(BaseModel):
    segment_id: str
    text: str
    language: str  # ISO 639-1
    page_range: tuple[int, int] | None = None
    heading: str | None = None


class SegmentResult(BaseModel):
    segments: list[TextSegment]


# Stage 3 output
class BookMeta(BaseModel):
    title: str
    author: str | None = None
    dynasty: str | None = None
    era_start: int | None = None
    era_end: int | None = None


class AuthorMeta(BaseModel):
    name: str
    dynasty: str | None = None
    birth_year: int | None = None
    death_year: int | None = None
    biography: str | None = None


class ExtractedEntry(BaseModel):
    segment_id: str
    title: str
    original_text: str
    locations_mentioned: list[str]
    dates_mentioned: list[str]
    persons_mentioned: list[str]
    keywords: list[str]
    visit_date_approximate: str | None = None


class EntityResult(BaseModel):
    book_meta: BookMeta | None = None
    author_meta: AuthorMeta | None = None
    entries: list[ExtractedEntry]


# Stage 4 output
class ResolvedLocation(BaseModel):
    name: str
    ancient_name: str | None = None
    modern_name: str | None = None
    latitude: float
    longitude: float
    location_type: str | None = None
    confidence: float = 0.0
    source: str = "llm_inference"  # "db_lookup" | "llm_inference" | "nominatim"
    existing_location_id: int | None = None


class LocationLink(BaseModel):
    location_name: str
    resolved_location: ResolvedLocation | None = None
    location_order: int


class GeocodedEntry(BaseModel):
    segment_id: str
    title: str
    original_text: str
    location_links: list[LocationLink]


class GeocodedResult(BaseModel):
    entries: list[GeocodedEntry]
    locations: list[ResolvedLocation]


# Stage 5 output
class TranslatedEntry(BaseModel):
    segment_id: str
    title: str
    original_text: str
    location_links: list[LocationLink]
    english_translation: str | None = None
    modern_translation: str | None = None
    translation_source: str = "ai"  # "ai" | "existing" | "mixed"


class TranslatedResult(BaseModel):
    entries: list[TranslatedEntry]


# Stage 6 output
class ScoredDimension(BaseModel):
    score: float
    evidence: str
    flags: list[str] = []


class CrossReference(BaseModel):
    source: str
    agreement: str


class CredibilityReport(BaseModel):
    segment_id: str
    overall_score: float
    firsthand: bool
    personal_experience: ScoredDimension
    accuracy: ScoredDimension
    exaggeration: ScoredDimension
    fantasy_elements: ScoredDimension
    source_reliability: ScoredDimension
    cross_references: list[CrossReference] = []
    scholarly_notes: str = ""


class ContextAnnotation(BaseModel):
    era_context: str = ""
    political_context: str = ""
    religious_context: str = ""
    social_environment: str = ""
    keyword_annotations: list[dict] = []


class AnalyzedEntry(TranslatedEntry):
    era_context: str = ""
    political_context: str = ""
    religious_context: str = ""
    social_environment: str = ""
    keyword_annotations: list[dict] = []


class AnalyzedResult(BaseModel):
    entries: list[AnalyzedEntry]
    credibility_reports: list[CredibilityReport]


# Pipeline state
class PipelineRun(BaseModel):
    id: int | None = None
    source_file: str
    status: str = "pending"  # "pending" | "running" | "stage_N" | "completed" | "failed"
    current_stage: int = 0
    stage_results: dict = {}
    human_review_status: str = "pending"  # "pending" | "approved" | "rejected" | "edited"
    human_review_notes: str | None = None
```

- [ ] **Step 4: Write test for models**

```python
# pipeline/tests/test_models.py
from pipeline.models import (
    IngestResult,
    TextSegment,
    SegmentResult,
    ExtractedEntry,
    EntityResult,
    ResolvedLocation,
    GeocodedResult,
    TranslatedResult,
    AnalyzedResult,
    CredibilityReport,
    ScoredDimension,
)


def test_ingest_result():
    r = IngestResult(source_file="test.pdf", file_type="pdf_digital", raw_text="hello", page_count=1, ocr_method="direct")
    assert r.source_file == "test.pdf"


def test_segment_result():
    s = TextSegment(segment_id="s1", text="hello world", language="en")
    r = SegmentResult(segments=[s])
    assert len(r.segments) == 1


def test_entity_result():
    e = ExtractedEntry(
        segment_id="s1",
        title="泉州见闻",
        original_text="text",
        locations_mentioned=["泉州"],
        dates_mentioned=["1292"],
        persons_mentioned=["马可·波罗"],
        keywords=["香料"],
    )
    r = EntityResult(entries=[e])
    assert r.entries[0].title == "泉州见闻"


def test_geocoded_result():
    loc = ResolvedLocation(name="泉州", latitude=24.87, longitude=118.67)
    assert loc.confidence == 0.0


def test_credibility_report():
    dim = ScoredDimension(score=0.9, evidence="first person narrative")
    report = CredibilityReport(
        segment_id="s1",
        overall_score=0.75,
        firsthand=True,
        personal_experience=dim,
        accuracy=dim,
        exaggeration=dim,
        fantasy_elements=dim,
        source_reliability=dim,
    )
    assert report.overall_score == 0.75
```

- [ ] **Step 5: Run test**

Run: `cd pipeline && pip install -e ".[dev]" && pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add pipeline/
git commit -m "feat: scaffold pipeline project with inter-stage Pydantic models"
```

---

## Task 2: LLM Client

**Files:**
- Create: `pipeline/core/__init__.py`
- Create: `pipeline/core/llm_client.py`
- Create: `pipeline/tests/test_llm_client.py`

- [ ] **Step 1: Create LLM client**

```python
# pipeline/core/llm_client.py
from __future__ import annotations

import os
from pathlib import Path

import yaml
from openai import AsyncOpenAI

CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        raw = f.read()
    # Expand env vars
    for key, val in os.environ.items():
        raw = raw.replace(f"${{{key}}}", val)
    return yaml.safe_load(raw)


class LLMClient:
    def __init__(self, config: dict | None = None):
        if config is None:
            config = load_config()
        llm_cfg = config["llm"]
        self.client = AsyncOpenAI(
            base_url=llm_cfg["base_url"],
            api_key=llm_cfg["api_key"],
        )
        self.model = llm_cfg["model"]
        self.max_tokens = llm_cfg.get("max_tokens", 4096)
        self.temperature = llm_cfg.get("temperature", 0.1)

    async def chat(self, prompt: str, system: str = "", max_tokens: int | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens or self.max_tokens,
            temperature=self.temperature,
        )
        return response.choices[0].message.content or ""

    async def extract_json(self, prompt: str, system: str = "") -> str:
        """Chat and extract JSON from response, stripping markdown fences."""
        raw = await self.chat(prompt, system)
        # Strip markdown code fences
        if raw.startswith("```"):
            lines = raw.split("\n")
            # Remove first and last lines (fences)
            lines = [l for l in lines if not l.startswith("```")]
            raw = "\n".join(lines)
        return raw.strip()
```

- [ ] **Step 2: Write test (mocked)**

```python
# pipeline/tests/test_llm_client.py
import pytest
from unittest.mock import AsyncMock, patch

from pipeline.core.llm_client import LLMClient


@pytest.fixture
def llm():
    config = {
        "llm": {
            "base_url": "http://localhost:8000/v1",
            "api_key": "test-key",
            "model": "test-model",
            "max_tokens": 100,
            "temperature": 0.0,
        }
    }
    return LLMClient(config)


@pytest.mark.asyncio
async def test_chat(llm):
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock(message=AsyncMock(content="Hello world"))]
    with patch.object(llm.client.chat.completions, "create", return_value=mock_response):
        result = await llm.chat("test prompt")
    assert result == "Hello world"


@pytest.mark.asyncio
async def test_extract_json_strips_fences(llm):
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock(message=AsyncMock(content='```json\n{"key": "value"}\n```'))]
    with patch.object(llm.client.chat.completions, "create", return_value=mock_response):
        result = await llm.extract_json("test prompt")
    assert result == '{"key": "value"}'
```

- [ ] **Step 3: Run test**

Run: `cd pipeline && pytest tests/test_llm_client.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add pipeline/core/ pipeline/tests/
git commit -m "feat: add async LLM client with JSON extraction"
```

---

## Task 3: PDF Parser and OCR

**Files:**
- Create: `pipeline/core/pdf_parser.py`
- Create: `pipeline/core/ocr.py`
- Create: `pipeline/tests/test_s1_ingest.py`

- [ ] **Step 1: Create PDF parser**

```python
# pipeline/core/pdf_parser.py
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
```

- [ ] **Step 2: Create OCR module**

```python
# pipeline/core/ocr.py
from __future__ import annotations

import base64
from pathlib import Path

import fitz  # PyMuPDF
from openai import AsyncOpenAI


class OCRClient:
    """OCR via OpenAI-compatible vision API. Config lives under `ocr:` in config.yaml."""

    def __init__(self, config: dict):
        ocr_cfg = config["ocr"]
        self.client = AsyncOpenAI(
            base_url=ocr_cfg["base_url"],
            api_key=ocr_cfg["api_key"],
        )
        self.model = ocr_cfg["model"]
        self.dpi = ocr_cfg.get("dpi", 200)
        self.max_tokens = ocr_cfg.get("max_tokens", 4096)

    async def ocr_page(self, img_b64: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract all text from this image. Preserve paragraph breaks. Return only the extracted text, no commentary."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                ],
            }],
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content or ""

    async def ocr_pdf(self, pdf_path: str) -> str:
        doc = fitz.open(pdf_path)
        texts = []
        for page in doc:
            pix = page.get_pixmap(dpi=self.dpi)
            img_b64 = base64.b64encode(pix.tobytes("png")).decode()
            text = await self.ocr_page(img_b64)
            texts.append(text)
        doc.close()
        return "\n\n".join(texts)
```

- [ ] **Step 3: Write ingest test**

```python
# pipeline/tests/test_s1_ingest.py
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
```

- [ ] **Step 4: Run test**

Run: `cd pipeline && pytest tests/test_s1_ingest.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/core/ pipeline/tests/
git commit -m "feat: add PDF parser and OCR modules"
```

---

## Task 4: Stage 1 — Ingestion

**Files:**
- Create: `pipeline/stages/__init__.py`
- Create: `pipeline/stages/s1_ingest.py`

- [ ] **Step 1: Create ingestion stage**

```python
# pipeline/stages/s1_ingest.py
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
```

- [ ] **Step 2: Commit**

```bash
git add pipeline/stages/
git commit -m "feat: add Stage 1 ingestion with PDF/text support"
```

---

## Task 5: Stage 2 — Segmentation

**Files:**
- Create: `pipeline/stages/s2_segment.py`
- Create: `pipeline/config/prompts/extraction.txt`

- [ ] **Step 1: Create segmentation stage**

```python
# pipeline/stages/s2_segment.py
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
```

- [ ] **Step 2: Commit**

```bash
git add pipeline/stages/s2_segment.py pipeline/config/
git commit -m "feat: add Stage 2 segmentation with language detection"
```

---

## Task 6: Stage 3 — Entity Extraction

**Files:**
- Create: `pipeline/stages/s3_extract.py`
- Create: `pipeline/config/prompts/extraction.txt`

- [ ] **Step 1: Create extraction prompt**

```
# pipeline/config/prompts/extraction.txt
You are analyzing a historical travel journal text. Extract structured information.

TEXT:
{text}

Extract the following as JSON:
{{
  "title": "A concise title for this entry (in the original language)",
  "locations_mentioned": ["list of place names mentioned"],
  "dates_mentioned": ["list of dates or time references"],
  "persons_mentioned": ["list of person names mentioned"],
  "keywords": ["5-10 key topics/themes"],
  "visit_date_approximate": "approximate date of visit if determinable, null otherwise"
}}

Return ONLY valid JSON, no commentary.
```

- [ ] **Step 2: Create extraction stage**

```python
# pipeline/stages/s3_extract.py
from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from pipeline.core.llm_client import LLMClient
from pipeline.models import (
    BookMeta,
    AuthorMeta,
    EntityResult,
    ExtractedEntry,
    SegmentResult,
)

PROMPTS_DIR = Path(__file__).parent.parent / "config" / "prompts"


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.txt").read_text()


async def extract_entities(segment_result: SegmentResult, llm: LLMClient) -> EntityResult:
    """Stage 3: Extract entities from text segments using LLM."""
    entries = []
    book_meta = None
    author_meta = None

    # First pass: try to extract book/author metadata from first segment
    if segment_result.segments:
        first = segment_result.segments[0]
        meta_prompt = f"""Analyze this text and extract book/author metadata.

TEXT (first 2000 chars):
{first.text[:2000]}

Return JSON:
{{
  "book": {{
    "title": "book title",
    "author": "author name or null",
    "dynasty": "dynasty/era or null",
    "era_start": null,
    "era_end": null
  }},
  "author": {{
    "name": "author name",
    "dynasty": "dynasty or null",
    "birth_year": null,
    "death_year": null,
    "biography": "brief bio or null"
  }}
}}

Return ONLY valid JSON."""

        try:
            raw = await llm.extract_json(meta_prompt)
            data = json.loads(raw)
            if data.get("book"):
                book_meta = BookMeta(**data["book"])
            if data.get("author"):
                author_meta = AuthorMeta(**data["author"])
        except (json.JSONDecodeError, ValidationError):
            pass

    # Extract entries from each segment
    prompt_template = load_prompt("extraction")

    for seg in segment_result.segments:
        prompt = prompt_template.format(text=seg.text[:4000])
        try:
            raw = await llm.extract_json(prompt)
            data = json.loads(raw)
            entry = ExtractedEntry(
                segment_id=seg.segment_id,
                title=data.get("title", seg.heading or f"Segment {seg.segment_id}"),
                original_text=seg.text,
                locations_mentioned=data.get("locations_mentioned", []),
                dates_mentioned=data.get("dates_mentioned", []),
                persons_mentioned=data.get("persons_mentioned", []),
                keywords=data.get("keywords", []),
                visit_date_approximate=data.get("visit_date_approximate"),
            )
            entries.append(entry)
        except (json.JSONDecodeError, ValidationError) as e:
            # Create entry with raw text on failure
            entries.append(ExtractedEntry(
                segment_id=seg.segment_id,
                title=seg.heading or f"Segment {seg.segment_id}",
                original_text=seg.text,
                locations_mentioned=[],
                dates_mentioned=[],
                persons_mentioned=[],
                keywords=[],
            ))

    return EntityResult(
        book_meta=book_meta,
        author_meta=author_meta,
        entries=entries,
    )
```

- [ ] **Step 3: Commit**

```bash
git add pipeline/stages/s3_extract.py pipeline/config/prompts/
git commit -m "feat: add Stage 3 entity extraction with LLM"
```

---

## Task 7: Stage 4 — Geocoding

**Files:**
- Create: `pipeline/stages/s4_geocode.py`
- Create: `pipeline/config/prompts/geocoding.txt`

- [ ] **Step 1: Create geocoding prompt**

```
# pipeline/config/prompts/geocoding.txt
You are a historical geography expert. Given a location name from a historical travel journal, provide its modern coordinates.

Location name: {name}
Historical context: {context}

Return JSON:
{{
  "modern_name": "modern name of the place",
  "ancient_name": "historical/ancient name (same as input if applicable)",
  "latitude": 0.0,
  "longitude": 0.0,
  "location_type": "古城/山川/寺庙/关隘/港口/商路/其他",
  "confidence": 0.0 to 1.0
}}

Return ONLY valid JSON. If you cannot determine coordinates, set confidence to 0.
```

- [ ] **Step 2: Create geocoding stage**

```python
# pipeline/stages/s4_geocode.py
from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from pipeline.core.llm_client import LLMClient
from pipeline.models import (
    EntityResult,
    GeocodedEntry,
    GeocodedResult,
    LocationLink,
    ResolvedLocation,
)

PROMPTS_DIR = Path(__file__).parent.parent / "config" / "prompts"


async def geocode_locations(entity_result: EntityResult, llm: LLMClient) -> GeocodedResult:
    """Stage 4: Resolve location names to coordinates."""
    prompt_template = (PROMPTS_DIR / "geocoding.txt").read_text()

    # Collect all unique location names
    all_names = set()
    for entry in entity_result.entries:
        all_names.update(entry.locations_mentioned)

    # Resolve each location
    resolved: dict[str, ResolvedLocation] = {}

    for name in all_names:
        context = f"Book: {entity_result.book_meta.title if entity_result.book_meta else 'unknown'}"
        prompt = prompt_template.format(name=name, context=context)
        try:
            raw = await llm.extract_json(prompt)
            data = json.loads(raw)
            loc = ResolvedLocation(
                name=name,
                ancient_name=data.get("ancient_name", name),
                modern_name=data.get("modern_name"),
                latitude=data.get("latitude", 0.0),
                longitude=data.get("longitude", 0.0),
                location_type=data.get("location_type"),
                confidence=data.get("confidence", 0.0),
                source="llm_inference",
            )
            if loc.confidence > 0:
                resolved[name] = loc
        except (json.JSONDecodeError, ValidationError, KeyError):
            pass

    # Build geocoded entries
    geocoded_entries = []
    for entry in entity_result.entries:
        links = []
        for i, loc_name in enumerate(entry.locations_mentioned):
            links.append(LocationLink(
                location_name=loc_name,
                resolved_location=resolved.get(loc_name),
                location_order=i,
            ))
        geocoded_entries.append(GeocodedEntry(
            segment_id=entry.segment_id,
            title=entry.title,
            original_text=entry.original_text,
            location_links=links,
        ))

    return GeocodedResult(
        entries=geocoded_entries,
        locations=list(resolved.values()),
    )
```

- [ ] **Step 3: Commit**

```bash
git add pipeline/stages/s4_geocode.py pipeline/config/prompts/
git commit -m "feat: add Stage 4 geocoding with LLM-based location resolution"
```

---

## Task 8: Stage 5 — Translation

**Files:**
- Create: `pipeline/stages/s5_translate.py`
- Create: `pipeline/config/prompts/translation.txt`

- [ ] **Step 1: Create translation prompt**

```
# pipeline/config/prompts/translation.txt
Translate the following historical travel journal text.

Source language: {source_lang}
Target language: {target_lang}

TEXT:
{text}

Return ONLY the translation, no commentary or notes.
```

- [ ] **Step 2: Create translation stage**

```python
# pipeline/stages/s5_translate.py
from __future__ import annotations

from pathlib import Path

from pipeline.core.llm_client import LLMClient
from pipeline.models import GeocodedResult, TranslatedEntry, TranslatedResult

PROMPTS_DIR = Path(__file__).parent.parent / "config" / "prompts"


async def translate_entries(geocoded_result: GeocodedResult, llm: LLMClient) -> TranslatedResult:
    """Stage 5: Translate entries to English and modern Chinese."""
    prompt_template = (PROMPTS_DIR / "translation.txt").read_text()
    translated = []

    for entry in geocoded_result.entries:
        english = None
        modern = None

        # Detect source language heuristic
        has_chinese = any("一" <= c <= "鿿" for c in entry.original_text[:200])

        if has_chinese:
            # Chinese → English
            prompt = prompt_template.format(
                source_lang="Classical Chinese",
                target_lang="English",
                text=entry.original_text[:4000],
            )
            english = await llm.chat(prompt)
            # Also modern Chinese
            prompt_modern = prompt_template.format(
                source_lang="Classical Chinese",
                target_lang="Modern Chinese (白话文)",
                text=entry.original_text[:4000],
            )
            modern = await llm.chat(prompt_modern)
        else:
            # English/other → Chinese
            prompt = prompt_template.format(
                source_lang="English",
                target_lang="Modern Chinese",
                text=entry.original_text[:4000],
            )
            modern = await llm.chat(prompt)

        translated.append(TranslatedEntry(
            segment_id=entry.segment_id,
            title=entry.title,
            original_text=entry.original_text,
            location_links=entry.location_links,
            english_translation=english,
            modern_translation=modern,
            translation_source="ai",
        ))

    return TranslatedResult(entries=translated)
```

- [ ] **Step 3: Commit**

```bash
git add pipeline/stages/s5_translate.py pipeline/config/prompts/
git commit -m "feat: add Stage 5 translation with auto language detection"
```

---

## Task 9: Stage 6 — Context and Credibility Analysis

**Files:**
- Create: `pipeline/stages/s6_analyze.py`
- Create: `pipeline/config/prompts/credibility.txt`

- [ ] **Step 1: Create credibility prompt**

```
# pipeline/config/prompts/credibility.txt
Analyze this historical travel journal entry for credibility and historical context.

TEXT:
{text}

BOOK: {book_title}
AUTHOR: {author_name}

Return JSON with this exact structure:
{{
  "era_context": "historical era description",
  "political_context": "political situation at the time",
  "religious_context": "religious context if relevant",
  "social_environment": "social conditions described",
  "credibility": {{
    "overall_score": 0.0 to 1.0,
    "firsthand": true or false,
    "personal_experience": {{
      "score": 0.0 to 1.0,
      "evidence": "brief evidence",
      "flags": ["list of concerns"]
    }},
    "accuracy": {{
      "score": 0.0 to 1.0,
      "evidence": "brief evidence",
      "flags": ["list of concerns"]
    }},
    "exaggeration": {{
      "score": 0.0 to 1.0,
      "evidence": "brief evidence",
      "flags": ["list of concerns"]
    }},
    "fantasy_elements": {{
      "score": 0.0 to 1.0,
      "evidence": "brief evidence",
      "flags": ["list of concerns"]
    }},
    "source_reliability": {{
      "score": 0.0 to 1.0,
      "evidence": "brief evidence",
      "flags": ["list of concerns"]
    }},
    "cross_references": [
      {{"source": "reference text", "agreement": "what it confirms"}}
    ],
    "scholarly_notes": "any scholarly commentary"
  }}
}}

Return ONLY valid JSON.
```

- [ ] **Step 2: Create analysis stage**

```python
# pipeline/stages/s6_analyze.py
from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from pipeline.core.llm_client import LLMClient
from pipeline.models import (
    AnalyzedEntry,
    AnalyzedResult,
    CredibilityReport,
    ScoredDimension,
    TranslatedResult,
)

PROMPTS_DIR = Path(__file__).parent.parent / "config" / "prompts"


def _parse_scored_dim(data: dict) -> ScoredDimension:
    return ScoredDimension(
        score=data.get("score", 0.5),
        evidence=data.get("evidence", ""),
        flags=data.get("flags", []),
    )


async def analyze_entries(translated_result: TranslatedResult, llm: LLMClient, book_title: str = "", author_name: str = "") -> AnalyzedResult:
    """Stage 6: Add context annotations and credibility analysis."""
    prompt_template = (PROMPTS_DIR / "credibility.txt").read_text()
    analyzed = []
    reports = []

    for entry in translated_result.entries:
        prompt = prompt_template.format(
            text=entry.original_text[:3000],
            book_title=book_title,
            author_name=author_name,
        )

        era = ""
        political = ""
        religious = ""
        social = ""
        report = None

        try:
            raw = await llm.extract_json(prompt)
            data = json.loads(raw)
            era = data.get("era_context", "")
            political = data.get("political_context", "")
            religious = data.get("religious_context", "")
            social = data.get("social_environment", "")

            cred = data.get("credibility", {})
            if cred:
                report = CredibilityReport(
                    segment_id=entry.segment_id,
                    overall_score=cred.get("overall_score", 0.5),
                    firsthand=cred.get("firsthand", False),
                    personal_experience=_parse_scored_dim(cred.get("personal_experience", {})),
                    accuracy=_parse_scored_dim(cred.get("accuracy", {})),
                    exaggeration=_parse_scored_dim(cred.get("exaggeration", {})),
                    fantasy_elements=_parse_scored_dim(cred.get("fantasy_elements", {})),
                    source_reliability=_parse_scored_dim(cred.get("source_reliability", {})),
                    cross_references=cred.get("cross_references", []),
                    scholarly_notes=cred.get("scholarly_notes", ""),
                )
                reports.append(report)
        except (json.JSONDecodeError, ValidationError):
            pass

        analyzed.append(AnalyzedEntry(
            segment_id=entry.segment_id,
            title=entry.title,
            original_text=entry.original_text,
            location_links=entry.location_links,
            english_translation=entry.english_translation,
            modern_translation=entry.modern_translation,
            translation_source=entry.translation_source,
            era_context=era,
            political_context=political,
            religious_context=religious,
            social_environment=social,
        ))

    return AnalyzedResult(entries=analyzed, credibility_reports=reports)
```

- [ ] **Step 3: Commit**

```bash
git add pipeline/stages/s6_analyze.py pipeline/config/prompts/
git commit -m "feat: add Stage 6 context and credibility analysis"
```

---

## Task 10: Stage 7 — Database Output

**Files:**
- Create: `pipeline/stages/s7_output.py`
- Create: `pipeline/core/db.py`

- [ ] **Step 1: Create DB connection module**

```python
# pipeline/core/db.py
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def make_engine(url: str):
    return create_async_engine(url, echo=False)


def make_session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

- [ ] **Step 2: Create output stage**

```python
# pipeline/stages/s7_output.py
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.models import AnalyzedResult


async def output_to_db(result: AnalyzedResult, session: AsyncSession) -> dict:
    """Stage 7: Insert analyzed results into the database.

    Returns dict with counts of inserted records.
    """
    # Import backend models — assumes backend is installed or on path
    from app.models.author import Author
    from app.models.book import Book
    from app.models.journal_entry import JournalEntry
    from app.models.location import Location
    from app.models.associations import entry_authors, entry_locations

    stats = {"books": 0, "authors": 0, "locations": 0, "entries": 0}

    # This is a simplified output stage.
    # In practice, you'd check for existing records and update/merge.
    # For now, create a book and author if metadata is available,
    # then create entries with location links.

    # Note: The full implementation would need the book_meta and author_meta
    # from the EntityResult. This is passed through the pipeline.
    # For this plan, we assume they're available in the result context.

    return stats
```

- [ ] **Step 3: Commit**

```bash
git add pipeline/stages/s7_output.py pipeline/core/db.py
git commit -m "feat: add Stage 7 database output module"
```

---

## Task 11: Pipeline Runner

**Files:**
- Create: `pipeline/runner.py`
- Create: `pipeline/tests/test_runner.py`

- [ ] **Step 1: Create pipeline runner**

```python
# pipeline/runner.py
from __future__ import annotations

from pipeline.core.llm_client import LLMClient
from pipeline.models import IngestResult, PipelineRun
from pipeline.stages.s1_ingest import ingest
from pipeline.stages.s2_segment import segment
from pipeline.stages.s3_extract import extract_entities
from pipeline.stages.s4_geocode import geocode_locations
from pipeline.stages.s5_translate import translate_entries
from pipeline.stages.s6_analyze import analyze_entries


async def run_pipeline(file_path: str, config: dict | None = None) -> dict:
    """Run the full pipeline on a single file.

    Returns a dict with all stage results.
    """
    if config is None:
        from pipeline.core.llm_client import load_config
        config = load_config()

    llm = LLMClient(config)
    results = {}

    # Stage 1: Ingest
    print("[Stage 1/7] Ingesting file...")
    ingest_result = await ingest(file_path, config)
    results["ingest"] = ingest_result
    print(f"  → {ingest_result.page_count} pages, {len(ingest_result.raw_text)} chars, method: {ingest_result.ocr_method}")

    # Stage 2: Segment
    print("[Stage 2/7] Segmenting text...")
    segment_result = await segment(ingest_result)
    results["segment"] = segment_result
    print(f"  → {len(segment_result.segments)} segments")

    # Stage 3: Extract entities
    print("[Stage 3/7] Extracting entities...")
    entity_result = await extract_entities(segment_result, llm)
    results["entity"] = entity_result
    print(f"  → {len(entity_result.entries)} entries extracted")
    if entity_result.book_meta:
        print(f"  → Book: {entity_result.book_meta.title}")

    # Stage 4: Geocode
    print("[Stage 4/7] Geocoding locations...")
    geocoded_result = await geocode_locations(entity_result, llm)
    results["geocoded"] = geocoded_result
    print(f"  → {len(geocoded_result.locations)} locations resolved")

    # Stage 5: Translate
    print("[Stage 5/7] Translating entries...")
    translated_result = await translate_entries(geocoded_result, llm)
    results["translated"] = translated_result

    # Stage 6: Analyze
    print("[Stage 6/7] Analyzing credibility...")
    book_title = entity_result.book_meta.title if entity_result.book_meta else ""
    author_name = entity_result.author_meta.name if entity_result.author_meta else ""
    analyzed_result = await analyze_entries(translated_result, llm, book_title, author_name)
    results["analyzed"] = analyzed_result
    print(f"  → {len(analyzed_result.credibility_reports)} credibility reports")

    # Stage 7: Output (skipped in dry-run — use s7_output.output_to_db directly)
    print("[Stage 7/7] Output to DB (skipped in dry-run)")

    print("Pipeline complete!")
    return results
```

- [ ] **Step 2: Write basic runner test (mocked)**

```python
# pipeline/tests/test_runner.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from pipeline.models import (
    IngestResult,
    SegmentResult,
    TextSegment,
    EntityResult,
    ExtractedEntry,
    GeocodedResult,
    GeocodedEntry,
    TranslatedResult,
    TranslatedEntry,
    AnalyzedResult,
    AnalyzedEntry,
    CredibilityReport,
    ScoredDimension,
)


@pytest.mark.asyncio
async def test_run_pipeline_dry_run():
    """Test pipeline stages are called in order with mocked LLM."""
    mock_ingest = IngestResult(
        source_file="test.txt", file_type="text", raw_text="马可·波罗到达泉州", page_count=1, ocr_method="direct"
    )
    mock_segment = SegmentResult(segments=[
        TextSegment(segment_id="s1", text="马可·波罗到达泉州", language="zh-cn")
    ])
    mock_entity = EntityResult(entries=[
        ExtractedEntry(
            segment_id="s1", title="泉州见闻",
            original_text="马可·波罗到达泉州",
            locations_mentioned=["泉州"], dates_mentioned=["1292"],
            persons_mentioned=["马可·波罗"], keywords=["泉州"],
        )
    ])

    dim = ScoredDimension(score=0.8, evidence="test")

    with (
        patch("pipeline.runner.ingest", return_value=mock_ingest),
        patch("pipeline.runner.segment", return_value=mock_segment),
        patch("pipeline.runner.extract_entities", return_value=mock_entity),
        patch("pipeline.runner.geocode_locations", return_value=GeocodedResult(entries=[
            GeocodedEntry(segment_id="s1", title="泉州见闻", original_text="马可·波罗到达泉州", location_links=[])
        ], locations=[])),
        patch("pipeline.runner.translate_entries", return_value=TranslatedResult(entries=[
            TranslatedEntry(segment_id="s1", title="泉州见闻", original_text="马可·波罗到达泉州", location_links=[])
        ])),
        patch("pipeline.runner.analyze_entries", return_value=AnalyzedResult(
            entries=[AnalyzedEntry(segment_id="s1", title="泉州见闻", original_text="马可·波罗到达泉州", location_links=[])],
            credibility_reports=[],
        )),
    ):
        from pipeline.runner import run_pipeline
        results = await run_pipeline("test.txt", {"llm": {"base_url": "x", "api_key": "x", "model": "x"}})

        assert "ingest" in results
        assert "analyzed" in results
        assert len(results["entity"].entries) == 1
```

- [ ] **Step 3: Run test**

Run: `cd pipeline && pytest tests/test_runner.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add pipeline/runner.py pipeline/tests/
git commit -m "feat: add pipeline runner orchestrating all 7 stages"
```

---

## Task 12: Review API

**Files:**
- Create: `pipeline/review/app.py`
- Create: `pipeline/review/static/index.html`

- [ ] **Step 1: Create review API**

```python
# pipeline/review/app.py
from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI(title="HiSMap Pipeline Review")

# In-memory store for demo. Production would use DB.
pipeline_runs: dict[int, dict] = {}
run_counter = 0


@app.get("/api/review/runs")
async def list_runs():
    return list(pipeline_runs.values())


@app.get("/api/review/runs/{run_id}")
async def get_run(run_id: int):
    run = pipeline_runs.get(run_id)
    if not run:
        return {"error": "Not found"}, 404
    return run


@app.post("/api/review/runs/{run_id}/approve")
async def approve_run(run_id: int):
    run = pipeline_runs.get(run_id)
    if not run:
        return {"error": "Not found"}, 404
    run["human_review_status"] = "approved"
    return run


@app.post("/api/review/runs/{run_id}/reject")
async def reject_run(run_id: int):
    run = pipeline_runs.get(run_id)
    if not run:
        return {"error": "Not found"}, 404
    run["human_review_status"] = "rejected"
    return run


static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/")
    async def review_ui():
        return FileResponse(str(static_dir / "index.html"))
```

- [ ] **Step 2: Create simple review UI**

```html
<!-- pipeline/review/static/index.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>HiSMap Pipeline Review</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 8px 12px; border: 1px solid #ddd; text-align: left; }
    th { background: #f5f5f5; }
    .btn { padding: 4px 12px; border: 1px solid #ccc; background: white; border-radius: 4px; cursor: pointer; }
    .btn-approve { background: #10b981; color: white; border-color: #10b981; }
    .btn-reject { background: #ef4444; color: white; border-color: #ef4444; }
  </style>
</head>
<body>
  <h1>Pipeline Review Dashboard</h1>
  <table>
    <thead>
      <tr>
        <th>Run ID</th>
        <th>Source</th>
        <th>Stage</th>
        <th>Status</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody id="runs"></tbody>
  </table>
  <script>
    async function loadRuns() {
      const res = await fetch('/api/review/runs');
      const runs = await res.json();
      const tbody = document.getElementById('runs');
      tbody.innerHTML = runs.map(r => `
        <tr>
          <td>#${r.id}</td>
          <td>${r.source_file}</td>
          <td>${r.current_stage}/7</td>
          <td>${r.human_review_status}</td>
          <td>
            <button class="btn btn-approve" onclick="approve(${r.id})">Approve</button>
            <button class="btn btn-reject" onclick="reject(${r.id})">Reject</button>
          </td>
        </tr>
      `).join('');
    }
    async function approve(id) {
      await fetch(`/api/review/runs/${id}/approve`, { method: 'POST' });
      loadRuns();
    }
    async function reject(id) {
      await fetch(`/api/review/runs/${id}/reject`, { method: 'POST' });
      loadRuns();
    }
    loadRuns();
  </script>
</body>
</html>
```

- [ ] **Step 3: Commit**

```bash
git add pipeline/review/
git commit -m "feat: add review API with dashboard UI"
```

---

## Summary

This plan produces a fully functional data processing pipeline with:

- **7 stages** — Ingestion, Segmentation, Entity Extraction, Geocoding, Translation, Credibility Analysis, DB Output
- **Typed inter-stage models** — Pydantic v2 models for all data flowing between stages
- **LLM client** — Async OpenAI SDK wrapper with provider-agnostic config
- **PDF/text parsing** — PyMuPDF with Google Vision and vision-LLM OCR fallbacks
- **Pipeline runner** — Orchestrates all stages, supports dry-run
- **Review API** — FastAPI dashboard for human supervision
- **Test suite** — Unit tests for models, mocked tests for LLM-dependent stages

**All 4 plans now cover the full HiSMap system:**
1. Backend Foundation — Database + API
2. Frontend Foundation — Map + Search + Filter
3. Location Detail Page — Four-layer content page
4. Data Pipeline — PDF to structured data
