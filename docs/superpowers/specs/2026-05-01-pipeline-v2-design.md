# Book Extract Pipeline v2 Design

## Problem Statement

The current 7-stage pipeline has two critical issues:
1. **No complete DB write flow** - Stage 7 is skipped in the runner; data only reaches the DB through a separate `import_to_db.py` script
2. **Excessive token consumption** - Each stage makes separate LLM calls with repeated context (~140K tokens for 10 segments of Marco Polo)

## Goals

- Consolidate LLM calls: one call per story instead of many
- Integrate DB write into the pipeline
- Support both text-based and scanned PDF inputs (auto-detect)
- Save extracted stories as local JSON files (checkpoint + audit trail)
- Reduce token consumption by ~60%+

## Architecture: 4-Stage Pipeline

```
Input File (.pdf / .rtf / .txt / .md / scanned images)
  │
  ├─ [S1 Ingest]  ── auto-detect: text extraction OR OCR
  │                   Output: raw_text + source_type
  │
  ├─ [S2 Segment] ── split by headings (text) or merge flags (OCR)
  │                   LLM fallback for heading-less texts
  │                   Assign IDs, save JSON files locally
  │
  ├─ [S3 Extract] ── single LLM call per story with web_search tool
  │                   Extract: metadata + entities + geocoding + translation + credibility
  │                   Update JSON files with extracted data
  │
  └─ [S4 Output]  ── write Book, Author, Location, JournalEntry to DB
                     JournalEntry.original_text = file path to JSON
```

---

## Stage 1: Ingest

### Input Detection

```
if input is .txt / .md:
    → read file directly as raw_text
elif input is .rtf:
    → strip RTF formatting → raw_text
elif input is .pdf:
    → try PyMuPDF text extraction
    → if extracted text length < threshold (e.g. 100 chars/page avg):
        → treat as scanned PDF → OCR path
    → else:
        → use extracted text
```

### OCR Path (Scanned PDFs)

1. Extract pages as images using PyMuPDF (`page.get_pixmap()`)
2. Send each page image to the vision model with an OCR prompt that returns structured JSON:

```json
{
  "text": "extracted text of the page",
  "stories": [
    {
      "title": "story title if visible",
      "text": "story text on this page",
      "continues_from_prev": false,
      "continues_to_next": true
    }
  ]
}
```

3. The OCR model uses its multimodal capabilities to identify story boundaries visually (chapter headings, spacing, decorative elements)

### Output Type

```python
class IngestResult(BaseModel):
    raw_text: str           # full text (for text-based inputs)
    source_type: str        # "text" | "ocr"
    ocr_pages: list[dict]   # per-page OCR results (empty for text-based)
    book_slug: str          # normalized from filename
    detected_language: str  # langdetect on first 1000 chars
```

---

## Stage 2: Segment

### Segmentation Logic (Three Paths)

**Path A: Text with headings (regex-based)**
- Reuse existing `segment_by_headings()` regex patterns (chapter markers, roman numerals, etc.)
- A pattern must match ≥ 2 times to be used
- Split by matched headings

**Path B: Text without headings (LLM fallback)**
- Triggered when regex heading detection finds < 2 matches
- Split raw text into chunks of ~20,000 chars at paragraph boundaries
- Send each chunk to LLM with prompt:

```
Identify individual stories/narratives in this text.
Return JSON:
{
  "stories": [
    {
      "title": "story title",
      "text": "full story text",
      "continues_from_prev": false,
      "continues_to_next": true
    }
  ]
}
Use continues_from_prev/continues_to_next flags for stories that span chunk boundaries.
```

- Merge stories across chunks using the flags (same logic as OCR path)

**Path C: OCR results**
- Use the `ocr_pages` from S1
- Merge stories across pages: if page N's last story has `continues_to_next: true` and page N+1's first story has `continues_from_prev: true` (or matching title), concatenate text
- Each merged story becomes one segment

### Shared Merge Logic

All paths (OCR, LLM fallback) produce the same JSON structure:
```json
{"stories": [{"title": "...", "text": "...", "continues_from_prev": bool, "continues_to_next": bool}]}
```

The merge algorithm is shared:
1. For each story in order, check `continues_from_prev`
2. If true and there's a previous unfinished story, append text to it
3. If false, start a new segment
4. Propagate `continues_to_next` to the merged segment

### ID Assignment

- Book slug from filename: normalized (lowercase, hyphens, strip special chars)
- Language from S1's `detected_language` (e.g. `chs`, `eng`, `jpn`)
- Sequential: `001`, `002`, ...
- Format: `{book_slug}-{lang}-{seq}` → e.g. `marco-polo-chs-001`

### Local JSON File Structure

One file per story, saved to `pipeline/output/{book_slug}/{id}.json`:

```json
{
  "id": "marco-polo-chs-001",
  "book_slug": "marco-polo",
  "language": "chs",
  "sequence": 1,
  "title": "Chapter 1 - The Emperor's Envoys",
  "original_text": "...full story text...",
  "source_type": "text",
  "page_range": [1, 3],
  "created_at": "2026-05-01T12:00:00Z",
  "extracted": false,
  "error": null
}
```

### Output Type

```python
class SegmentInfo(BaseModel):
    id: str
    title: str
    file_path: str
    original_text_preview: str  # first 200 chars for logging

class SegmentResult(BaseModel):
    book_slug: str
    language: str
    segments: list[SegmentInfo]
```

---

## Stage 3: Extract (Single LLM Call Per Story)

### LLM Call Structure

```python
response = await llm_client.chat(
    model=config.model,
    messages=[
        {"role": "system", "content": EXTRACTION_PROMPT},
        {"role": "user", "content": story_text}
    ],
    tools=[{
        "type": "web_search",
        "max_keyword": 6,
        "force_search": False,
        "limit": 6
    }],
    response_format={"type": "json_object"}
)
```

### Expected JSON Response

```json
{
  "book_metadata": {
    "title": "The Travels of Marco Polo",
    "author": "Marco Polo",
    "dynasty": "Yuan",
    "era_start": 1271,
    "era_end": 1295,
    "author_biography": "Venetian merchant traveler..."
  },
  "story_metadata": {
    "title": "Chapter 1 - The Emperor's Envoys",
    "chapter_reference": "Chapter 1",
    "visit_date_approximate": "1271"
  },
  "entities": {
    "locations": [
      {
        "name": "Beijing",
        "modern_name": "Beijing",
        "ancient_name": "Dadu",
        "lat": 39.9042,
        "lng": 116.4074,
        "location_type": "city",
        "one_line_summary": "Capital of Yuan Dynasty, seat of Kublai Khan's court"
      }
    ],
    "persons": ["Kublai Khan", "Niccolò Polo"],
    "dates": ["1271", "1275"],
    "keywords": ["trade", "silk road", "diplomacy"]
  },
  "translations": {
    "modern_chinese": "...(if source is classical Chinese)...",
    "english": "..."
  },
  "credibility": {
    "era_context": "Late 13th century, Pax Mongolica",
    "political_context": "Yuan Dynasty expansion under Kublai Khan",
    "religious_context": "Religious tolerance under Mongol rule",
    "social_environment": "Active Silk Road trade",
    "credibility_score": 0.85,
    "notes": "First-hand account, some embellishments likely"
  },
  "annotations": [
    {
      "source": "web_search",
      "query": "Marco Polo Dadu Beijing Yuan Dynasty",
      "url": "https://en.wikipedia.org/wiki/Marco_Polo",
      "snippet": "Marco Polo departed Venice in 1271..."
    }
  ]
}
```

### Processing Per Story

1. Read `{id}.json` from disk
2. Check `extracted` flag - skip if already `true` (resume support)
3. Call LLM with story text + web_search tool
4. Parse JSON response
5. Merge extracted data back into the JSON file
6. Set `extracted: true`, save to disk

### Token Savings Estimate

For 10 segments of Marco Polo:
- **Current**: ~140K tokens (many calls with repeated context)
- **New**: ~10 calls × ~5K tokens each = ~50K tokens (**64% reduction**)

For a full book with 100 segments:
- **Current**: ~1.4M tokens
- **New**: ~500K tokens

---

## Stage 4: Output (Database Write)

### Records Written

1. **Book** (create once per pipeline run):
   - `title`, `author`, `dynasty`, `era_start`, `era_end` from first story's `book_metadata`
   - `source_text` = relative path to JSON directory

2. **Author** (create or reuse by name):
   - `name`, `dynasty`, `birth_year`, `death_year`, `biography` from `book_metadata`

3. **Locations** (deduplicated by `name`):
   - For each unique location across all stories
   - Fields: `name`, `modern_name`, `ancient_name`, `latitude`, `longitude`, `location_type`, `one_line_summary`
   - If location already exists in DB (by name match), reuse its ID

4. **JournalEntry** (one per story):
   - `book_id` → FK to book
   - `title` from `story_metadata.title`
   - `original_text` = relative file path (e.g. `pipeline/output/marco-polo/marco-polo-chs-001.json`)
   - `modern_translation`, `english_translation` from `translations`
   - `chapter_reference` from `story_metadata`
   - `keywords` from `entities.keywords`
   - `era_context`, `political_context`, `religious_context`, `social_environment` from `credibility`
   - `visit_date_approximate` from `story_metadata`
   - `credibility` = full credibility JSON object
   - `annotations` = full annotations JSON array

5. **Association tables**:
   - `entry_locations`: link entries to locations with `location_order`
   - `entry_authors`: link entries to author

### DB Schema Changes

New Alembic migration to add to `journal_entries`:
- `credibility` (JSON) - full credibility report
- `annotations` (JSON) - web search annotations

Change `original_text` semantics: now stores file path instead of text content. Note: in the local JSON files, `original_text` still contains the full story text. Only in the database does `original_text` store the file path.

### Transaction Behavior

- Use a single DB transaction for the entire batch
- If any write fails, rollback all changes
- On success, commit all records atomically

---

## Error Handling

- **S1 (OCR)**: If OCR fails for a page, skip it and log a warning. Mark the book as partially processed.
- **S2 (Segment)**: If no segments found, raise an error. Skip malformed segments with a warning.
- **S3 (Extract)**: Retry up to 2 times on LLM failure. If still fails, mark story as `extracted: false, error: "..."` and continue. Don't fail the entire pipeline.
- **S4 (Output)**: Use DB transaction. Rollback entire batch on any failure.

## Resume Support

- **S3**: Check each story's JSON for `extracted: true`. Skip already-extracted stories.
- **S4**: Check if book already exists in DB. If so, update rather than duplicate.

---

## Files to Create/Modify

```
pipeline/
├── stages/
│   ├── s1_ingest.py      # REWRITE: add OCR path, auto-detect
│   ├── s2_segment.py     # REWRITE: add OCR merge, LLM fallback, ID assignment, JSON save
│   ├── s3_extract.py     # REWRITE: single LLM call with web_search
│   └── s4_output.py      # REWRITE (was s7): DB write with file paths
├── core/
│   ├── ocr.py            # MODIFY: add structured OCR prompt with boundary markers
│   ├── llm_client.py     # MODIFY: add web_search tool support
│   └── db.py             # KEEP as-is
├── models.py             # MODIFY: new stage input/output types
├── runner.py             # MODIFY: 4-stage orchestration
└── tests/
    ├── test_s1_ingest.py
    ├── test_s2_segment.py
    ├── test_s3_extract.py
    └── test_s4_output.py

backend/
├── alembic/
│   └── versions/
│       └── 002_add_credibility_annotations.py  # NEW migration
└── app/models/
    └── book.py           # MODIFY: add credibility, annotations columns
```

## Testing Strategy

- Unit tests for each stage function (mock LLM client, mock DB session)
- Integration test: run full pipeline on the existing Marco Polo Chinese test data
- Test OCR merge logic with synthetic multi-page data
- Test LLM fallback segmentation with heading-less text
- Test resume capability (run S3 twice, verify no duplicate processing)
