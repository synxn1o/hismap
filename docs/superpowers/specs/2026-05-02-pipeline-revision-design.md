# Pipeline Revision: Chapter-Based Chunking + Excerpt/Summary Extraction

## Overview

Revise the extraction pipeline from fixed-size chunking to chapter-based segmentation with LLM-powered excerpt/summary generation. The goal is to produce one entry per travel story/anecdote, with bilingual summaries replacing direct translations, and a secondary page for viewing full original text.

## Goals

1. **Chapter-based chunking** — integrate `chapter_detector.py` for intelligent segmentation
2. **Excerpt + Summary** — replace `translations` with LLM-generated excerpt (source language + translation) and bilingual summary
3. **Completeness-aware extraction** — single LLM call handles non-content filtering, multi-story detection, and structured extraction
4. **Prompt optimization** — combined extraction prompt with structured output, rich context injection
5. **Frontend revision** — list shows excerpt/summary, independent route page for full text
6. **Extensibility** — support beyond travelogues (novels, diaries, essays)

## Architecture

```
S1 (ingest) → S2 (chapter_detector split) → S2.5 [optional, user-triggered] → S3 (extract) → S4 (output to DB)
                                                    ↑
                                         User previews split,
                                         optionally triggers LLM
                                         anchor-matching subdivision
```

---

## S2: Chapter-Based Segmentation

### Approach

Replace the current regex-based heading detection + fixed 2000-char fallback with `chapter_detector.py`'s chain-of-responsibility pattern.

### Flow

1. Load `ChapterDetectorChain` via `build_default_chain(llm_client)`
2. Run `chain.detect(text, strategy="auto")` to get chapter list
3. Each chapter → one `ExtractedStory` JSON file on disk
4. Mark chapters > 5000 chars with `needs_subdivision=True`
5. If detector returns only 1 chapter (no structure detected), fallback to existing regex segmentation

### Changes to `s2_segment.py`

- Import and use `chapter_detector.build_default_chain`
- New function `segment_by_chapters(ingest_result, output_dir, llm)` replacing `segment_by_headings`
- Preserve existing `_segment_by_llm()` and `merge_ocr_stories()` as fallback paths
- Add `chapter_title` and `needs_subdivision` fields to `SegmentInfo`

### `ExtractedStory` model additions

```python
chapter_title: str | None = None
is_content: bool = True
is_truncated: bool = False
needs_subdivision: bool = False
```

### Book Summary Extraction

Before S3 extraction, a one-time LLM call summarizes the book's preface/序言:
1. S1 identifies preface pages (via electronic TOC bookmarks or heuristic first-10-pages scan)
2. Preface text is sent to LLM with a summarization prompt
3. Result stored as `book_summary` in book metadata
4. This summary is injected into every S3 extraction call as context item #1

### Backward Compatibility

- If `chapter_detector` finds < 2 chapters, fall back to regex heading detection
- If regex also fails, fall back to LLM segmentation (existing path)
- All existing JSON file format and naming conventions preserved

---

## S2.5: Optional LLM Subdivision (User-Triggered)

### Purpose

For chapters marked `needs_subdivision=True`, allow the user to preview and optionally trigger LLM-based finer splitting.

### Anchor Matching Approach

1. User previews split results (chapter title, char count, text preview)
2. User selects chapters to subdivide
3. For selected chapters, call LLM with subdivision prompt:
   - Input: chapter text + book context
   - Output: JSON array of `{ "start_anchor": "前30字...", "end_anchor": "...后15字", "title": "..." }`
4. Script matches anchors in original text via substring search
5. If anchor matching fails (e.g., duplicate text), fall back to character position estimation
6. New `ExtractedStory` JSON files created for each sub-segment

### Truncation Support

- If a chapter ends mid-sentence, the last anchor's `end_anchor` can be set to `"truncated"`
- Script handles this by using end-of-text as the boundary
- The resulting entry will be marked `is_truncated=True`

---

## S3: Extraction with Completeness Awareness

### Flow

For each `ExtractedStory` JSON file (where `extracted=False`):

```
Step 1: Load chunk text + build context injection
Step 2: Call LLM with combined filter+extract prompt
Step 3: Parse response → entries[]
Step 4: For each entry: match anchors in original text, create sub-segment JSON
Step 5: Write results back to JSON files, set extracted=True
```

### Single LLM Call Design

One API call handles filtering, segmentation, and full extraction in a single structured JSON response. The prompt instructs the LLM to: (1) identify content vs non-content sections using anchors, (2) split multi-story chunks into separate entries, (3) extract all fields for each content entry. This avoids the latency and cost of multiple sequential LLM calls.

```json
{
  "entries": [
    {
      "start_anchor": "目  录",
      "end_anchor": "...页码12",
      "is_content": false
    },
    {
      "start_anchor": "波罗弟兄二人自君士坦丁堡...",
      "end_anchor": "...抵达上都。",
      "is_content": true,
      "is_truncated": false,
      "story_metadata": {
        "title": "从君士坦丁堡到上都",
        "chapter_reference": "第一章",
        "visit_date_approximate": "1271年"
      },
      "excerpt": {
        "original": "波罗弟兄二人自君士坦丁堡出发...",
        "translation": "The two Polo brothers set out from Constantinople..."
      },
      "summary": {
        "chinese": "马可·波罗的父亲和叔叔从君士坦丁堡出发，途经中亚，最终抵达元朝上都。",
        "english": "Marco Polo's father and uncle traveled from Constantinople through Central Asia to reach Kublai Khan's capital at Shangdu."
      },
      "entities": {
        "locations": [
          {
            "name": "君士坦丁堡",
            "modern_name": "伊斯坦布尔",
            "ancient_name": "Constantinople",
            "lat": 41.0082,
            "lng": 28.9784,
            "location_type": "city",
            "one_line_summary": "拜占庭帝国首都，丝绸之路西端起点"
          }
        ],
        "persons": ["马可·波罗", "尼科洛·波罗", "马费奥·波罗"],
        "dates": ["1271年"],
        "keywords": ["丝绸之路", "中世纪旅行", "元朝"]
      },
      "credibility": {
        "era_context": "13世纪蒙古帝国鼎盛时期",
        "political_context": "元朝忽必烈汗统治",
        "religious_context": null,
        "social_environment": "东西方贸易繁荣",
        "credibility_score": 0.7,
        "notes": "波罗游记的真实性长期有争议"
      },
      "annotations": [
        {
          "source": "web_search",
          "query": "Marco Polo journey Constantinople to Shangdu",
          "url": "https://...",
          "snippet": "..."
        }
      ]
    }
  ]
}
```

### Key Rules for the LLM

**Segmentation rules:**
- Each entry = one independent narrative unit (story, anecdote, travel segment)
- `is_content=false` for: table of contents, preface, index, bibliography, translator's notes
- Anchors must be in document order and non-overlapping
- A chunk typically contains 1-3 entries; do not over-segment

**Truncation detection:**
- `is_truncated=true` ONLY when: sentence is grammatically incomplete, narrative suddenly breaks off with no natural ending
- Do NOT flag as truncated if: text is long but coherent, contains multiple locations but same journey, describes a complex event

**Content judgment criteria (for `is_content`):**
- Non-content indicators: numbered page references, dotted lines (目录格式), "参见"/"see also" references, bibliography format
- Content indicators: continuous narrative, character dialogue, event description, location description

### Context Injection

Every LLM call includes these 7 context items:

1. **Book summary** — extracted from preface/序言 (one-time, stored in book metadata)
2. **Book metadata** — title, author, dynasty, era
3. **Current chapter title** — from `chapter_detector`
4. **Chapter position** — "第 X 章 / 共 N 章"
5. **Adjacent chapter titles** — previous/next chapter
6. **Known entities list** — previously extracted locations/persons for consistency
7. **Source language rules** — language-specific extraction guidelines

### Prompt Templates

```
pipeline/config/prompts/
├── extraction_combined.txt     # Combined filter + extract prompt
├── extraction_subdivide.txt    # Anchor matching for S2.5 subdivision
├── book_summary.txt            # Preface summarization (one-time per book)
```

The combined prompt structure:
- **System role**: historical text analysis expert
- **Context block**: all 7 context items (book summary, metadata, chapter info, adjacent chapters, known entities, language rules)
- **Task description**: filter non-content, segment multi-story chunks, extract all fields
- **Segmentation rules**: with examples and anti-patterns for over-segmentation
- **Output JSON schema**: exact structure with `entries[]` containing anchors + extraction data
- **Anti false-positive rules**: explicit criteria for truncation and non-content detection

### Tool Usage

- `web_search` tool attached to the extraction call
- LLM decides when to search (for unfamiliar place names, historical figures)
- `max_keywords=3`, `limit=2` per search, `force_search=False`
- Search results go into `annotations[]`

---

## S4: Output to Database

### Changes to `s4_output.py`

1. Read new fields from `ExtractedStory` JSON: `summary_chinese`, `summary_english`, `excerpt_original`, `excerpt_translation`, `persons`, `dates`
2. Write to `JournalEntry` new columns
3. Skip entries where `is_content=False`
4. For `dates`: write first extracted date to `visit_date_approximate` (if field is empty)
5. Write `credibility` and `annotations` to their existing JSON columns (now exposed via API)

---

## Data Model Changes

### Pipeline (`pipeline/models.py`)

`ExtractedStory` additions:
```python
chapter_title: str | None = None
is_content: bool = True
is_truncated: bool = False
needs_subdivision: bool = False
excerpt_original: str | None = None
excerpt_translation: str | None = None
summary_chinese: str | None = None
summary_english: str | None = None
persons: list[str] | None = None
dates: list[str] | None = None
```

### Backend Model (`backend/app/models/journal_entry.py`)

Remove:
- `modern_translation` (replaced by `summary_chinese`)
- `english_translation` (replaced by `summary_english`)

Add:
```python
excerpt_original = Column(Text, nullable=True)
excerpt_translation = Column(Text, nullable=True)
summary_chinese = Column(Text, nullable=True)
summary_english = Column(Text, nullable=True)
persons = Column(JSON, nullable=True)
dates = Column(JSON, nullable=True)
```

### Backend Schema (`backend/app/schemas/journal_entry.py`)

`JournalEntryBase` changes:
- Remove: `modern_translation`, `english_translation`
- Add: `excerpt_original`, `excerpt_translation`, `summary_chinese`, `summary_english`, `persons`, `dates`
- Expose: `credibility` (dict | None), `annotations` (list | None)

### Alembic Migration

- New migration file for column additions/removals
- `server_default` for new columns to handle existing rows
- Data migration: copy `modern_translation` → `summary_chinese`, `english_translation` → `summary_english` if desired

---

## Frontend Changes

### ResultList (sidebar)

Current: shows `original_text` with 2-line clamp
New: shows `excerpt_original` (source language) + `summary_chinese` or `summary_english` (based on language preference), 2-3 line clamp

### EntryDetail (right panel)

Current: shows full `original_text`
New: shows `excerpt_original` + `excerpt_translation` + bilingual summary
Add "View Full Text" button → navigates to `/entries/:id`

### New Route: `/entries/:id`

Independent page (similar to `LocationPage`):
- **Header**: `story_metadata` (title, chapter, date, authors)
- **Main content**: Full `original_text`
- **Sidebar**: excerpt + summary (bilingual), location list with map links, keyword tags
- **Bottom**: credibility assessment, annotations with source links
- **Navigation**: back button to return to map view

### Language Preference

- Add language toggle in filter area or app settings
- Options: "中文" / "English"
- Affects: `summary_chinese` vs `summary_english`, `excerpt_translation` display
- Persist in localStorage

### Type Changes (`frontend/src/types/index.ts`)

```typescript
interface JournalEntry {
  id: number;
  book_id: number | null;
  title: string;
  original_text: string;
  // Remove: modern_translation, english_translation
  // Add:
  excerpt_original: string | null;
  excerpt_translation: string | null;
  summary_chinese: string | null;
  summary_english: string | null;
  persons: string[] | null;
  dates: string[] | null;
  credibility: Record<string, any> | null;
  annotations: any[] | null;
  // Keep:
  chapter_reference: string | null;
  keywords: string[] | null;
  keyword_annotations: Record<string, any> | null;
  era_context: string | null;
  political_context: string | null;
  religious_context: string | null;
  social_environment: string | null;
  visit_date_approximate: string | null;
  locations: LocationBrief[];
  authors: AuthorBrief[];
}
```

---

## Implementation Order

1. **Pipeline models** — update `ExtractedStory` in `models.py`
2. **S2 refactor** — integrate `chapter_detector`, update `s2_segment.py`
3. **Book summary extraction** — preface detection + summarization in S1/S2
4. **S2.5** — add anchor-matching subdivision (optional, user-triggered)
5. **S3 refactor** — new combined prompt, context injection, anchor matching
6. **Prompt templates** — write `extraction_combined.txt`, `extraction_subdivide.txt`, `book_summary.txt`
7. **S4 refactor** — read new fields, write to new columns
8. **Backend model** — add/remove columns, update schemas
9. **Alembic migration** — generate and apply migration
10. **Frontend types** — update TypeScript interfaces
11. **Frontend components** — ResultList, EntryDetail, new EntryPage
12. **Frontend routing** — add `/entries/:id` route

---

## Design Decisions

- **Book summary**: Extracted automatically. S1 identifies preface/序言 pages (via `TOCPageMapper` or heuristic detection), then a one-time LLM call summarizes the preface into a `book_summary` stored in the book metadata. This summary is injected into every S3 extraction call.
- **Books without chapter structure**: Handled by the existing fallback chain — `chapter_detector` auto strategy tries all detectors by priority, falls back to regex heading detection, then LLM segmentation. No special handling needed.
- **Language preference**: Display only. Extraction always produces both Chinese and English summaries regardless of user preference. The frontend toggle controls which language is shown in the list and detail views.
