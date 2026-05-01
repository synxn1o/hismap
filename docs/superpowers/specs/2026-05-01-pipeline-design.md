# HiSMap Data Processing Pipeline — Design Document

## Overview

This document describes the data processing pipeline for HiSMap, which converts raw historical texts (PDFs, digital text) into structured database records. The pipeline uses AI tools (OCR, LLM extraction, translation, credibility analysis) with human supervision support.

## Goals

- Process scanned and digital PDFs of historical travel journals
- Support multi-language sources (English, Classical Chinese, Arabic, Latin, Italian, etc.)
- Extract locations, dates, persons, keywords, and historical context
- Generate translations when no existing translation is available
- Produce credibility reports for each journal entry (firsthand vs hearsay, exaggeration, fantasy elements)
- Cross-reference entries across different sources
- Feed structured data into the existing PostgreSQL database
- Allow human supervision at each stage via a review UI

## Architecture

### Pipeline Stages

```
┌─────────────────────────────────────────────────────────────────┐
│                        Input Layer                               │
│  PDF files (scanned/digital)  |  Text files  |  (future: URLs)  │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────┐
│  Stage 1: Ingestion & OCR                                        │
│  - Scanned PDF → Google Vision OCR → raw text                    │
│  - Digital PDF → text extraction (PyMuPDF)                       │
│  - Text files → direct read                                      │
│  - Output: raw text + metadata (page count, language hints)      │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────┐
│  Stage 2: Language Detection & Segmentation                      │
│  - Detect primary language(s) of the text                        │
│  - Segment into logical entries (by chapter, heading, or LLM)    │
│  - Output: list of text segments with language tags              │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────┐
│  Stage 3: Entity Extraction                                      │
│  - LLM extracts: locations, dates, persons, events, keywords     │
│  - Identify book metadata (title, author, dynasty/era)           │
│  - Output: structured entities per segment                       │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────┐
│  Stage 4: Location Resolution & Geocoding                        │
│  - Match extracted location names → known locations (DB lookup)  │
│  - New locations → LLM suggests modern name + coordinates        │
│  - Validate coordinates against known geography                  │
│  - Output: location records with lat/lng and ancient/modern names│
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────┐
│  Stage 5: Translation                                            │
│  - If text is Chinese → English translation (LLM)                │
│  - If text is English → Chinese translation (LLM)                │
│  - Other languages → English first, then Chinese                 │
│  - Skip if quality translation already exists                    │
│  - Output: original + english_translation + modern_translation   │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────┐
│  Stage 6: Context & Credibility Analysis                         │
│  - LLM analyzes each entry for:                                  │
│    • era_context, political_context, religious_context            │
│    • social_environment                                           │
│    • Credibility report (see below)                               │
│  - Cross-references against other entries in corpus              │
│  - Output: context annotations + credibility report per entry    │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────┐
│  Stage 7: Output & DB Insert                                     │
│  - Assemble final JournalEntry, Location, Book, Author records   │
│  - Insert into PostgreSQL via existing FastAPI CRUD layer        │
│  - Mark pipeline run as complete                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Credibility Report Structure

Stored in `JournalEntry.credibility_report` as JSON:

```json
{
  "overall_score": 0.75,
  "firsthand": true,
  "personal_experience": {
    "score": 0.9,
    "evidence": "Author uses first-person narrative, describes sensory details consistent with actual travel",
    "flags": []
  },
  "accuracy": {
    "score": 0.7,
    "evidence": "Distances and directions roughly consistent with known geography",
    "flags": ["some distance estimates appear rounded"]
  },
  "exaggeration": {
    "score": 0.6,
    "evidence": "Population figures and city sizes likely inflated, common for era",
    "flags": ["claims city had 1 million inhabitants", "describes palace as largest in world"]
  },
  "fantasy_elements": {
    "score": 0.95,
    "evidence": "No mythical creatures or supernatural claims",
    "flags": []
  },
  "source_reliability": {
    "score": 0.8,
    "evidence": "Author's other accounts verified by archaeology in 3 of 5 cases",
    "flags": ["some passages appear borrowed from earlier texts"]
  },
  "cross_references": [
    {"source": "Ibn Battuta, Rihla, 1325", "agreement": "confirms city's trade importance"},
    {"source": "Chinese records, Song Dynasty", "agreement": "corroborates port description"}
  ],
  "scholarly_notes": "Yule (1871) considers this passage reliable; modern scholars generally agree."
}
```

## Tech Stack

| Component | Technology | Reason |
|---|---|---|
| Pipeline framework | Python 3.11+ with `asyncio` | Async support for concurrent API calls |
| OCR (primary) | Google Cloud Vision API | Best accuracy for historical/multilingual documents |
| OCR (fallback) | Vision-capable LLM (Claude/GPT-4o) | Zero Google dependency option |
| LLM client | OpenAI Python SDK (`openai`) | Provider-agnostic via `base_url` config |
| Default LLM provider | Claude (via Anthropic `/v1` endpoint) | Strong multilingual, long context |
| Geocoding | LLM + OpenStreetMap Nominatim | LLM for ancient→modern mapping, Nominatim for validation |
| PDF parsing | PyMuPDF (fitz) | Handles both scanned and digital PDFs |
| Language detection | `langdetect` library | Lightweight, good accuracy |
| Database | PostgreSQL (shared with existing backend) | Reuse existing schema and CRUD layer |
| Review UI | FastAPI + simple React page | Reuse existing backend patterns |

### LLM Provider Configuration

All LLM calls use the OpenAI SDK format. Changing provider is a config change:

```yaml
# config.yaml
llm:
  base_url: "https://api.anthropic.com/v1"
  api_key: "${ANTHROPIC_API_KEY}"
  model: "claude-sonnet-4-6"
  # Swap to OpenAI:
  # base_url: "https://api.openai.com/v1"
  # model: "gpt-4o"
  # Swap to local:
  # base_url: "http://localhost:11434/v1"
  # model: "qwen2.5:72b"
```

### OCR Strategy

```python
async def extract_text(pdf_path: str) -> str:
    if config.google_vision_key:
        text = await google_vision_ocr(pdf_path)
        if confidence(text) > 0.8:
            return text
    # Fallback to vision LLM
    images = pdf_to_images(pdf_path)
    return await vision_llm_ocr(images)
```

### API Cost Estimates

| Stage | API | Est. Cost per Entry |
|---|---|---|
| 1. OCR | Google Vision | ~$0.0015/page |
| 3. Entity Extraction | LLM | ~$0.01-0.03 |
| 4. Geocoding | LLM + Nominatim | ~$0.005 |
| 5. Translation | LLM | ~$0.02-0.05 |
| 6. Credibility | LLM | ~$0.03-0.08 |

**Rough total per journal entry**: $0.05–$0.15

## Project Structure

```
hismap/
├── frontend/                  # (existing v1 plan)
├── backend/                   # (existing v1 plan)
├── pipeline/                  # data processing pipeline
│   ├── config/
│   │   ├── config.yaml        # provider URLs, API keys, model names
│   │   └── prompts/           # LLM prompt templates per stage
│   │       ├── extraction.txt
│   │       ├── geocoding.txt
│   │       ├── translation.txt
│   │       ├── credibility.txt
│   │       └── ocr_fallback.txt
│   ├── stages/
│   │   ├── __init__.py
│   │   ├── s1_ingest.py       # OCR + text extraction
│   │   ├── s2_segment.py      # language detection + segmentation
│   │   ├── s3_extract.py      # entity extraction (LLM)
│   │   ├── s4_geocode.py      # location resolution (LLM + Nominatim)
│   │   ├── s5_translate.py    # translation (LLM)
│   │   ├── s6_analyze.py      # context + credibility (LLM)
│   │   └── s7_output.py       # DB insert
│   ├── core/
│   │   ├── llm_client.py      # OpenAI SDK wrapper (single entry point)
│   │   ├── ocr.py             # Google Vision + vision-LLM fallback
│   │   ├── pdf_parser.py      # PyMuPDF wrapper
│   │   └── db.py              # DB connection (reuse backend models)
│   ├── review/
│   │   ├── app.py             # FastAPI review API endpoints
│   │   └── static/            # simple review UI (HTML/JS)
│   ├── runner.py              # pipeline orchestrator
│   ├── models.py              # pipeline-specific Pydantic models
│   └── requirements.txt
└── docs/
```

## Data Flow & Inter-Stage Models

Each stage passes typed Pydantic models to the next.

### Stage 1 → Stage 2: IngestResult

```python
class IngestResult(BaseModel):
    source_file: str
    file_type: Literal["pdf_scanned", "pdf_digital", "text"]
    raw_text: str
    page_count: int
    ocr_method: Literal["google_vision", "vision_llm", "direct"]
    metadata: dict
```

### Stage 2 → Stage 3: SegmentResult

```python
class TextSegment(BaseModel):
    segment_id: str
    text: str
    language: str  # ISO 639-1
    page_range: tuple[int, int] | None
    heading: str | None

class SegmentResult(BaseModel):
    segments: list[TextSegment]
```

### Stage 3 → Stage 4: EntityResult

```python
class ExtractedEntry(BaseModel):
    segment_id: str
    title: str
    original_text: str
    locations_mentioned: list[str]
    dates_mentioned: list[str]
    persons_mentioned: list[str]
    keywords: list[str]
    visit_date_approximate: str | None

class EntityResult(BaseModel):
    book_meta: BookMeta | None
    author_meta: AuthorMeta | None
    entries: list[ExtractedEntry]
```

### Stage 4 → Stage 5: GeocodedResult

```python
class ResolvedLocation(BaseModel):
    name: str
    ancient_name: str | None
    modern_name: str
    latitude: float
    longitude: float
    location_type: str
    confidence: float
    source: Literal["db_lookup", "llm_inference", "nominatim"]
    existing_location_id: int | None

class LocationLink(BaseModel):
    location_name: str
    resolved_location: ResolvedLocation | None
    location_order: int

class GeocodedEntry(BaseModel):
    segment_id: str
    title: str
    original_text: str
    location_links: list[LocationLink]

class GeocodedResult(BaseModel):
    entries: list[GeocodedEntry]
    locations: list[ResolvedLocation]
```

### Stage 5 → Stage 6: TranslatedResult

```python
class TranslatedEntry(BaseModel):
    # all fields from GeocodedEntry, plus:
    english_translation: str | None
    modern_translation: str | None
    translation_source: Literal["ai", "existing", "mixed"]

class TranslatedResult(BaseModel):
    entries: list[TranslatedEntry]
```

### Stage 6 → Stage 7: AnalyzedResult

```python
class ScoredDimension(BaseModel):
    score: float
    evidence: str
    flags: list[str]

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
    cross_references: list[CrossReference]
    scholarly_notes: str

class AnalyzedEntry(BaseModel):
    # all fields from TranslatedEntry, plus:
    era_context: str
    political_context: str
    religious_context: str
    social_environment: str
    keyword_annotations: list[KeywordAnnotation]

class AnalyzedResult(BaseModel):
    entries: list[AnalyzedEntry]
    credibility_reports: list[CredibilityReport]
```

## Pipeline State Management

```python
# pipeline_runs table
class PipelineRun(BaseModel):
    id: int
    source_file: str
    status: Literal["pending", "running", "stage_N", "completed", "failed"]
    current_stage: int  # 1-7
    stage_results: dict  # JSON output of each completed stage
    human_review_status: Literal["pending", "approved", "rejected", "edited"]
    human_review_notes: str | None
    created_at: datetime
    updated_at: datetime
```

### Review Flow

```
Pipeline runs Stage N
    ↓
Results saved to pipeline_runs.stage_results[N]
    ↓
Review UI shows results for human inspection
    ↓
Human: Approve → pipeline continues to Stage N+1
Human: Edit → corrections saved, pipeline continues
Human: Reject → pipeline stops, flagged for re-processing
```

Each stage can be run independently for re-processing:
```bash
python -m pipeline.stages.s3_extract --run-id 123
```

## Review UI

### Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  Pipeline Runs                                               │
├──────────┬──────────┬────────┬──────────┬───────────────────┤
│ Run ID   │ Source   │ Stage  │ Status   │ Actions           │
├──────────┼──────────┼────────┼──────────┼───────────────────┤
│ #042     │ polo.pdf │ 6/7    │ Review   │ [View] [Approve]  │
│ #041     │ batuta   │ 3/7    │ Review   │ [View] [Reject]   │
│ #040     │ xu.txt   │ 7/7    │ Done     │ [View]            │
└──────────┴──────────┴────────┴──────────┴───────────────────┘
```

### Stage Review Page

Side-by-side view of original text vs. extracted entities, with inline editing and bulk approve/reject.

## Frontend Changes

### Credibility Display

The location detail page gets a new credibility card in the "现代解释" section:

```
┌─────────────────────────────────────────────────────────────┐
│  可信度分析                                                   │
│  Overall: ████████░░ 75/100                                  │
│                                                              │
│  ✓ 亲历记录 (Firsthand Account)        ████████░░ 90/100    │
│    作者使用第一人称叙述，描述了感官细节...                      │
│                                                              │
│  ⚠ 夸张成分 (Exaggeration)             ██████░░░░ 60/100    │
│    人口数字和城市规模可能夸大，符合该时期惯例...                 │
│    ⚠ 声称城市有100万人口                                        │
│    ⚠ 描述宫殿为世界最大                                         │
│                                                              │
│  交叉引用:                                                     │
│  • 伊本·白图泰《旅行》1325年 — 确认城市贸易重要性               │
│  • 宋代中国文献 — 佐证港口描述                                  │
│                                                              │
│  学术注释: Yule (1871) 认为此段可靠...                         │
└─────────────────────────────────────────────────────────────┘
```

## Error Handling

### Error Classification

| Error Type | Example | Recoverable | Action |
|---|---|---|---|
| API timeout/rate limit | 429/503 from LLM | Yes | Retry with exponential backoff (3 attempts) |
| API content refusal | LLM refuses text | No | Flag for human review |
| OCR low confidence | Vision confidence < 0.5 | Yes | Retry with vision-LLM fallback |
| Empty extraction | No entities from valid text | Yes | Retry with adjusted prompt |
| Geocoding failure | Location not found | No | Mark unresolved, human adds in review |
| Translation gibberish | Fails language detection | Yes | Retry once, then flag |
| DB insert failure | Duplicate/FK violation | No | Log, flag for human fix |

### Retry Strategy

```python
MAX_RETRIES = 3
BASE_DELAY = 1  # seconds
BACKOFF_MULTIPLIER = 2  # 1s, 2s, 4s
```

### Partial Processing

Entries are processed independently. A single entry failure doesn't stop the pipeline:

```
Stage 3: 12 entries
  Entry 1-2: ✓ success
  Entry 3: ✗ API error → retry → ✓ success
  Entry 4: ✗ LLM refused → flagged for human review
  Entry 5-12: ✓ success

Result: 11/12 processed, 1 flagged. Pipeline continues.
```

### LLM Output Validation

```python
async def extract_with_retry(llm, prompt, text, model_class):
    raw = await llm.chat(prompt.format(text=text))
    try:
        return model_class.model_validate_json(raw)
    except ValidationError as e:
        fix_prompt = f"Your previous output had errors: {e}\nOriginal:\n{raw}\nFix and return valid JSON only."
        raw2 = await llm.chat(fix_prompt)
        try:
            return model_class.model_validate_json(raw2)
        except ValidationError:
            return PartialResult(raw=raw2, error=str(e))
```

### Cost Guardrails

```yaml
cost_limits:
  max_cost_per_run: 5.00      # USD
  max_tokens_per_entry: 8000   # per LLM call
  max_entries_per_run: 500     # safety cap
```

## Future Extensions

- **Online source scraping** (Project Gutenberg, Wikisource, etc.)
- **Batch processing** with Airflow/Prefect orchestration
- **Embedding-based semantic search** across the corpus
- **Active learning**: pipeline learns from human corrections to improve over time
- **Multi-pass credibility**: compare new entries against already-verified entries
