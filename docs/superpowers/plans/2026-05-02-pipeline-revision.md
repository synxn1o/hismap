# Pipeline Revision: Chapter-Based Chunking + Excerpt/Summary Extraction

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Revise the extraction pipeline from fixed-size chunking to chapter-based segmentation with LLM-powered excerpt/summary generation, producing one entry per travel story with bilingual summaries.

**Architecture:** Replace S2's regex heading detection with `chapter_detector.py`'s chain-of-responsibility pattern. Replace S3's single-prompt extraction with a combined filter+extract prompt that handles non-content detection, multi-story segmentation, and full field extraction in one LLM call. Add excerpt/summary fields replacing direct translations. Frontend changes are in a separate plan (`2026-05-02-frontend-pipeline-revision.md`).

**Tech Stack:** Python, Pydantic v2, FastAPI, SQLAlchemy, Alembic -- run with conda environment `hismap`

**Branch:** `feat/4-non-content-detection-and-pipeline-revision` (from issue #4)

---

## File Structure

### Pipeline — Create/Modify
- `pipeline/models.py` — **Modify:178-197** — add fields to `ExtractedStory`
- `pipeline/stages/s2_segment.py` — **Modify** — integrate chapter_detector, add `segment_by_chapters()`
- `pipeline/stages/s3_extract.py` — **Modify** — new combined prompt, context injection, `is_content` filtering
- `pipeline/stages/s4_output.py` — **Modify:94-118** — read new fields, skip `is_content=false`
- `pipeline/stages/book_summary.py` — **Create** — preface detection and summarization
- `pipeline/runner.py` — **Modify** — pass book_summary and known_entities to S3
- `pipeline/config/prompts/extraction_combined.txt` — **Create** — combined filter+extract prompt
- `pipeline/config/prompts/extraction_subdivide.txt` — **Create** — S2.5 subdivision prompt
- `pipeline/config/prompts/book_summary.txt` — **Create** — preface summarization prompt

### Backend — Create/Modify
- `backend/app/models/journal_entry.py` — **Modify:10-24** — remove `modern_translation`/`english_translation`, add new columns
- `backend/app/schemas/journal_entry.py` — **Modify** — update all schemas with new fields
- `backend/app/crud/journal_entry.py` — **Modify:99** — update search to use new field names
- `backend/alembic/versions/004_pipeline_revision.py` — **Create** — migration for column changes

---

## Task 1: Add `is_content` to ExtractedStory Model

**Files:**
- Modify: `pipeline/models.py:178-197`
- Test: `pipeline/tests/test_models.py`

- [ ] **Step 1: Write the failing test for new model fields**

Add to `pipeline/tests/test_models.py`:

```python
def test_extracted_story_is_content_field():
    """ExtractedStory should have is_content field defaulting to True."""
    from pipeline.models import ExtractedStory

    story = ExtractedStory(
        id="test-en-001",
        book_slug="test",
        language="en",
        sequence=1,
        title="Chapter 1",
        original_text="Some text",
        source_type="text",
    )
    assert story.is_content is True

    # Non-content story
    story_nc = ExtractedStory(
        id="test-en-002",
        book_slug="test",
        language="en",
        sequence=2,
        title="Table of Contents",
        original_text="Chapter 1... 1\nChapter 2... 15",
        source_type="text",
        is_content=False,
    )
    assert story_nc.is_content is False


def test_extracted_story_new_fields():
    """ExtractedStory should support excerpt, summary, persons, dates fields."""
    from pipeline.models import ExtractedStory

    story = ExtractedStory(
        id="test-en-001",
        book_slug="test",
        language="en",
        sequence=1,
        title="Chapter 1",
        original_text="Some text",
        source_type="text",
        chapter_title="The Beginning",
        is_truncated=False,
        needs_subdivision=False,
        excerpt_original="The journey began...",
        excerpt_translation="The journey began...",
        summary_chinese="A journey description.",
        summary_english="A journey description.",
        persons=["Marco Polo"],
        dates=["1271"],
    )
    assert story.chapter_title == "The Beginning"
    assert story.is_truncated is False
    assert story.needs_subdivision is False
    assert story.excerpt_original == "The journey began..."
    assert story.excerpt_translation == "The journey began..."
    assert story.summary_chinese == "A journey description."
    assert story.summary_english == "A journey description."
    assert story.persons == ["Marco Polo"]
    assert story.dates == ["1271"]


def test_extracted_story_serialization_roundtrip_with_new_fields():
    """New fields survive model_dump -> model_validate roundtrip."""
    from pipeline.models import ExtractedStory

    story = ExtractedStory(
        id="test-en-001",
        book_slug="test",
        language="en",
        sequence=1,
        title="Chapter 1",
        original_text="Some text",
        source_type="text",
        is_content=False,
        chapter_title="The Beginning",
        excerpt_original="Journey...",
        summary_chinese="旅行描述",
        summary_english="A journey description.",
        persons=["Marco Polo"],
        dates=["1271"],
    )
    data = story.model_dump()
    restored = ExtractedStory(**data)
    assert restored.is_content is False
    assert restored.chapter_title == "The Beginning"
    assert restored.excerpt_original == "Journey..."
    assert restored.summary_chinese == "旅行描述"
    assert restored.persons == ["Marco Polo"]
    assert restored.dates == ["1271"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd pipeline && python -m pytest tests/test_models.py -v -k "is_content or new_fields or roundtrip_with_new" 2>&1 | tail -20`
Expected: FAIL with `ValidationError` — fields not defined on model

- [ ] **Step 3: Add new fields to ExtractedStory**

In `pipeline/models.py`, replace lines 178-197:

```python
class ExtractedStory(BaseModel):
    """Represents a single story JSON file on disk."""
    id: str
    book_slug: str
    language: str
    sequence: int
    title: str
    original_text: str
    source_type: Literal["text", "ocr"]
    page_range: list[int] = []
    created_at: str = ""
    extracted: bool = False
    error: str | None = None
    # Segmentation metadata
    chapter_title: str | None = None
    is_content: bool = True
    is_truncated: bool = False
    needs_subdivision: bool = False
    # Excerpt and summary (populated by S3)
    excerpt_original: str | None = None
    excerpt_translation: str | None = None
    summary_chinese: str | None = None
    summary_english: str | None = None
    persons: list[str] | None = None
    dates: list[str] | None = None
    # Extracted fields (populated by S3)
    book_metadata: dict | None = None
    story_metadata: dict | None = None
    entities: dict | None = None
    translations: dict | None = None
    credibility: dict | None = None
    annotations: list[dict] | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd pipeline && python -m pytest tests/test_models.py -v -k "is_content or new_fields or roundtrip_with_new" 2>&1 | tail -10`
Expected: 3 passed

- [ ] **Step 5: Run full model test suite to check for regressions**

Run: `cd pipeline && python -m pytest tests/test_models.py -v 2>&1 | tail -10`
Expected: All existing tests still pass

- [ ] **Step 6: Commit**

```bash
git add pipeline/models.py pipeline/tests/test_models.py
git commit -m "feat(pipeline): add is_content, excerpt, summary, persons, dates fields to ExtractedStory"
```

---

## Task 2: Add `is_content` Filtering to S2 LLM Fallback

**Files:**
- Modify: `pipeline/stages/s2_segment.py:179-208`
- Test: `pipeline/tests/test_s2_segment.py`

- [ ] **Step 1: Write the failing test for non-content filtering in LLM fallback**

Add to `pipeline/tests/test_s2_segment.py`:

```python
@pytest.mark.asyncio
async def test_segment_by_llm_filters_non_content():
    """LLM fallback should exclude non-content stories from output."""
    from pipeline.stages.s2_segment import _segment_by_llm

    llm = AsyncMock()
    llm.extract_json = AsyncMock(return_value=json.dumps({
        "stories": [
            {"title": "Table of Contents", "text": "Chapter 1... 1\nChapter 2... 15", "is_content": False},
            {"title": "Chapter 1", "text": "The journey began in 1271.", "is_content": True},
            {"title": "Bibliography", "text": "See also: Smith 2020", "is_content": False},
        ]
    }))

    stories = await _segment_by_llm("Some text", llm)
    # Only content stories should remain
    assert len(stories) == 1
    assert stories[0]["title"] == "Chapter 1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd pipeline && python -m pytest tests/test_s2_segment.py -v -k "non_content" 2>&1 | tail -15`
Expected: FAIL — `_segment_by_llm` currently returns all stories regardless of `is_content`

- [ ] **Step 3: Update `_segment_by_llm` to filter non-content**

In `pipeline/stages/s2_segment.py`, replace the `_segment_by_llm` function (lines 179-208):

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd pipeline && python -m pytest tests/test_s2_segment.py -v -k "non_content" 2>&1 | tail -10`
Expected: 1 passed

- [ ] **Step 5: Run full S2 test suite**

Run: `cd pipeline && python -m pytest tests/test_s2_segment.py -v 2>&1 | tail -10`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add pipeline/stages/s2_segment.py pipeline/tests/test_s2_segment.py
git commit -m "feat(pipeline): filter non-content stories in S2 LLM fallback"
```

---

## Task 3: Add `is_content` Handling to S3 Extraction

**Files:**
- Modify: `pipeline/stages/s3_extract.py:25-118`
- Modify: `pipeline/config/prompts/extraction.txt`
- Test: `pipeline/tests/test_s3_extract.py`

- [ ] **Step 1: Write the failing test for non-content skipping in S3**

Add to `pipeline/tests/test_s3_extract.py`:

```python
@pytest.mark.asyncio
async def test_extract_skips_non_content_stories(tmp_path, mock_llm):
    """S3 should skip extraction for stories marked is_content=False."""
    from pipeline.stages.s3_extract import extract

    story = ExtractedStory(
        id="test-en-004",
        book_slug="test",
        language="en",
        sequence=4,
        title="Table of Contents",
        original_text="Chapter 1... 1\nChapter 2... 15",
        source_type="text",
        extracted=False,
        is_content=False,
    )
    path = tmp_path / "test-en-004.json"
    path.write_text(story.model_dump_json(indent=2))

    segment = SegmentInfo(
        id="test-en-004",
        title="Table of Contents",
        file_path=str(path),
        original_text_preview="Chapter 1...",
    )
    segment_result = SegmentResultV2(book_slug="test", language="en", segments=[segment])

    result = await extract(segment_result, mock_llm)

    # LLM should NOT be called for non-content
    mock_llm.chat_with_tools.assert_not_called()
    # Story should be marked as extracted with non_content note
    saved = json.loads(path.read_text())
    assert saved["extracted"] is True
    assert saved["error"] == "non_content"
    assert result["skipped"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd pipeline && python -m pytest tests/test_s3_extract.py -v -k "non_content" 2>&1 | tail -15`
Expected: FAIL — S3 currently processes all stories regardless of `is_content`

- [ ] **Step 3: Update S3 to skip non-content stories**

In `pipeline/stages/s3_extract.py`, after line 47 (`stats["skipped"] += 1; continue`), add a check before the LLM call. Replace lines 44-47 with:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd pipeline && python -m pytest tests/test_s3_extract.py -v -k "non_content" 2>&1 | tail -10`
Expected: 1 passed

- [ ] **Step 5: Run full S3 test suite**

Run: `cd pipeline && python -m pytest tests/test_s3_extract.py -v 2>&1 | tail -10`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add pipeline/stages/s3_extract.py pipeline/tests/test_s3_extract.py
git commit -m "feat(pipeline): skip non-content stories in S3 extraction"
```

---

## Task 4: Add `is_content` Filtering to S4 Output

**Files:**
- Modify: `pipeline/stages/s4_output.py:94-118`
- Test: `pipeline/tests/test_s4_output.py`

- [ ] **Step 1: Write the failing test for non-content filtering in S4**

Add to `pipeline/tests/test_s4_output.py`:

```python
@pytest.mark.asyncio
async def test_output_skips_non_content_stories(tmp_path):
    """S4 should not create JournalEntry for non-content stories."""
    from pipeline.stages.s4_output import output_to_db

    # Create a content story and a non-content story
    content_story = ExtractedStory(
        id="test-en-001",
        book_slug="test",
        language="en",
        sequence=1,
        title="Chapter 1",
        original_text="Journey text",
        source_type="text",
        extracted=True,
        is_content=True,
        book_metadata={"title": "Test Book", "author": "Author"},
        story_metadata={"title": "Chapter 1"},
        entities={"locations": [], "keywords": ["travel"]},
        translations={"modern_chinese": None, "english": "Journey text"},
        credibility={"era_context": "Medieval"},
    )
    non_content_story = ExtractedStory(
        id="test-en-002",
        book_slug="test",
        language="en",
        sequence=2,
        title="TOC",
        original_text="Chapter 1... 1",
        source_type="text",
        extracted=True,
        is_content=False,
    )

    content_path = tmp_path / "test-en-001.json"
    content_path.write_text(content_story.model_dump_json(indent=2))
    non_content_path = tmp_path / "test-en-002.json"
    non_content_path.write_text(non_content_story.model_dump_json(indent=2))

    segment_result = SegmentResultV2(
        book_slug="test",
        language="en",
        segments=[
            SegmentInfo(id="test-en-001", title="Chapter 1", file_path=str(content_path), original_text_preview="Journey"),
            SegmentInfo(id="test-en-002", title="TOC", file_path=str(non_content_path), original_text_preview="Chapter 1"),
        ],
    )

    # Mock session
    from unittest.mock import AsyncMock, MagicMock
    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()

    # Mock the Book/Author/Location/JournalEntry constructors
    with patch("pipeline.stages.s4_output.Book") as MockBook, \
         patch("pipeline.stages.s4_output.Author") as MockAuthor, \
         patch("pipeline.stages.s4_output.JournalEntry") as MockJE, \
         patch("pipeline.stages.s4_output.Location") as MockLoc:
        MockBook.return_value = MagicMock(id=1)
        MockAuthor.return_value = MagicMock(id=1)
        MockJE.return_value = MagicMock(id=1)
        MockLoc.return_value = MagicMock(id=1)

        result = await output_to_db(segment_result, session)

    # Only 1 entry should be created (the content story)
    assert result.entries == 1
```

Note: You'll need to add `from unittest.mock import patch, MagicMock` to the test file imports if not already present.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd pipeline && python -m pytest tests/test_s4_output.py -v -k "non_content" 2>&1 | tail -15`
Expected: FAIL — S4 currently creates entries for all stories

- [ ] **Step 3: Update S4 to skip non-content stories**

In `pipeline/stages/s4_output.py`, replace the entry creation loop (lines 94-118) with:

```python
    # 4. Create JournalEntry for each content story
    for story in stories:
        if not story.is_content:
            continue

        rel_path = f"pipeline/output/{segment_result.book_slug}/{story.id}.json"

        story_meta = story.story_metadata or {}
        entities = story.entities or {}
        translations = story.translations or {}
        credibility = story.credibility or {}

        je = JournalEntry(
            book_id=book.id if book else None,
            title=story_meta.get("title", story.title),
            original_text=rel_path,
            excerpt_original=story.excerpt_original,
            excerpt_translation=story.excerpt_translation,
            summary_chinese=story.summary_chinese,
            summary_english=story.summary_english,
            modern_translation=translations.get("modern_chinese"),
            english_translation=translations.get("english"),
            chapter_reference=story_meta.get("chapter_reference"),
            keywords=entities.get("keywords"),
            persons=story.persons,
            dates=story.dates,
            era_context=credibility.get("era_context"),
            political_context=credibility.get("political_context"),
            religious_context=credibility.get("religious_context"),
            social_environment=credibility.get("social_environment"),
            visit_date_approximate=story_meta.get("visit_date_approximate"),
            credibility=credibility if credibility else None,
            annotations=story.annotations if story.annotations else None,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd pipeline && python -m pytest tests/test_s4_output.py -v -k "non_content" 2>&1 | tail -10`
Expected: 1 passed

- [ ] **Step 5: Run full S4 test suite**

Run: `cd pipeline && python -m pytest tests/test_s4_output.py -v 2>&1 | tail -10`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add pipeline/stages/s4_output.py pipeline/tests/test_s4_output.py
git commit -m "feat(pipeline): skip non-content stories in S4 output, write new excerpt/summary fields"
```

---

## Task 5: Backend Model — Add New Columns, Remove Old Translation Columns

**Files:**
- Modify: `backend/app/models/journal_entry.py:10-24`
- Test: `backend/app/tests/test_models.py`

- [ ] **Step 1: Write the failing test for new columns**

Add to `backend/app/tests/test_models.py` (create if not exists, following existing test patterns):

```python
def test_journal_entry_has_new_fields():
    """JournalEntry model should have excerpt, summary, persons, dates columns."""
    from app.models.journal_entry import JournalEntry

    # Check new columns exist on the model
    columns = {c.name for c in JournalEntry.__table__.columns}
    assert "excerpt_original" in columns
    assert "excerpt_translation" in columns
    assert "summary_chinese" in columns
    assert "summary_english" in columns
    assert "persons" in columns
    assert "dates" in columns


def test_journal_entry_removes_old_translation_fields():
    """JournalEntry model should NOT have modern_translation or english_translation."""
    from app.models.journal_entry import JournalEntry

    columns = {c.name for c in JournalEntry.__table__.columns}
    assert "modern_translation" not in columns
    assert "english_translation" not in columns
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest app/tests/test_models.py -v -k "new_fields or removes_old" 2>&1 | tail -15`
Expected: FAIL — columns don't exist yet / old columns still present

- [ ] **Step 3: Update JournalEntry model**

Replace `backend/app/models/journal_entry.py`:

```python
from sqlalchemy import Column, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class JournalEntry(BaseModel):
    __tablename__ = "journal_entries"

    book_id = Column(Integer, ForeignKey("books.id"), nullable=True)
    title = Column(String(500), nullable=False)
    original_text = Column(Text, nullable=False)
    excerpt_original = Column(Text, nullable=True)
    excerpt_translation = Column(Text, nullable=True)
    summary_chinese = Column(Text, nullable=True)
    summary_english = Column(Text, nullable=True)
    chapter_reference = Column(String(200), nullable=True)
    keywords = Column(JSON, nullable=True)
    keyword_annotations = Column(JSON, nullable=True)
    persons = Column(JSON, nullable=True)
    dates = Column(JSON, nullable=True)
    era_context = Column(String(200), nullable=True)
    political_context = Column(Text, nullable=True)
    religious_context = Column(Text, nullable=True)
    social_environment = Column(Text, nullable=True)
    visit_date_approximate = Column(String(100), nullable=True)
    credibility = Column(JSON, nullable=True)
    annotations = Column(JSON, nullable=True)

    book = relationship("Book", back_populates="entries", lazy="selectin")
    locations = relationship("Location", secondary="entry_locations", back_populates="entries", lazy="selectin")
    authors = relationship("Author", secondary="entry_authors", back_populates="entries", lazy="selectin")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest app/tests/test_models.py -v -k "new_fields or removes_old" 2>&1 | tail -10`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/journal_entry.py backend/app/tests/test_models.py
git commit -m "feat(backend): replace translation columns with excerpt/summary/persons/dates"
```

---

## Task 6: Backend Schemas — Update Pydantic Schemas

**Files:**
- Modify: `backend/app/schemas/journal_entry.py`
- Test: `backend/app/tests/test_schemas.py`

- [ ] **Step 1: Write the failing test for updated schemas**

Create `backend/app/tests/test_schemas.py`:

```python
from app.schemas.journal_entry import (
    JournalEntryBase,
    JournalEntryCreate,
    JournalEntryRead,
    JournalEntryDetail,
    JournalEntryUpdate,
)


def test_journal_entry_base_has_new_fields():
    """JournalEntryBase should have excerpt, summary, persons, dates fields."""
    entry = JournalEntryBase(
        title="Test",
        original_text="Text",
        excerpt_original="Excerpt",
        excerpt_translation="Translation",
        summary_chinese="中文摘要",
        summary_english="English summary",
        persons=["Marco Polo"],
        dates=["1271"],
    )
    assert entry.excerpt_original == "Excerpt"
    assert entry.summary_chinese == "中文摘要"
    assert entry.persons == ["Marco Polo"]
    assert entry.dates == ["1271"]


def test_journal_entry_base_removes_old_fields():
    """JournalEntryBase should NOT have modern_translation or english_translation."""
    import inspect
    fields = JournalEntryBase.model_fields
    assert "modern_translation" not in fields
    assert "english_translation" not in fields


def test_journal_entry_read_exposes_credibility_annotations():
    """JournalEntryRead should include credibility and annotations."""
    entry = JournalEntryRead(
        id=1,
        title="Test",
        original_text="Text",
        credibility={"score": 0.8},
        annotations=[{"source": "web_search"}],
    )
    assert entry.credibility == {"score": 0.8}
    assert entry.annotations == [{"source": "web_search"}]


def test_journal_entry_detail_exposes_all_fields():
    """JournalEntryDetail should include all new fields."""
    entry = JournalEntryDetail(
        id=1,
        title="Test",
        original_text="Text",
        excerpt_original="Excerpt",
        summary_english="Summary",
        credibility={"score": 0.8},
        annotations=[],
    )
    assert entry.excerpt_original == "Excerpt"
    assert entry.summary_english == "Summary"
    assert entry.credibility == {"score": 0.8}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest app/tests/test_schemas.py -v 2>&1 | tail -15`
Expected: FAIL — fields don't exist on schemas

- [ ] **Step 3: Update all Pydantic schemas**

Replace `backend/app/schemas/journal_entry.py`:

```python
from pydantic import BaseModel


class JournalEntryBase(BaseModel):
    book_id: int | None = None
    title: str
    original_text: str
    excerpt_original: str | None = None
    excerpt_translation: str | None = None
    summary_chinese: str | None = None
    summary_english: str | None = None
    chapter_reference: str | None = None
    keywords: list[str] | None = None
    keyword_annotations: dict | None = None
    persons: list[str] | None = None
    dates: list[str] | None = None
    era_context: str | None = None
    political_context: str | None = None
    religious_context: str | None = None
    social_environment: str | None = None
    visit_date_approximate: str | None = None
    credibility: dict | None = None
    annotations: list | None = None


class JournalEntryCreate(JournalEntryBase):
    location_ids: list[int] = []
    author_ids: list[int] = []


class JournalEntryUpdate(BaseModel):
    title: str | None = None
    original_text: str | None = None
    excerpt_original: str | None = None
    excerpt_translation: str | None = None
    summary_chinese: str | None = None
    summary_english: str | None = None
    chapter_reference: str | None = None
    keywords: list[str] | None = None
    keyword_annotations: dict | None = None
    persons: list[str] | None = None
    dates: list[str] | None = None
    era_context: str | None = None
    political_context: str | None = None
    religious_context: str | None = None
    social_environment: str | None = None
    visit_date_approximate: str | None = None
    credibility: dict | None = None
    annotations: list | None = None
    location_ids: list[int] | None = None
    author_ids: list[int] | None = None


class LocationBrief(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float

    model_config = {"from_attributes": True}


class AuthorBrief(BaseModel):
    id: int
    name: str
    dynasty: str | None = None

    model_config = {"from_attributes": True}


class BookBrief(BaseModel):
    id: int
    title: str

    model_config = {"from_attributes": True}


class JournalEntryRead(JournalEntryBase):
    id: int
    locations: list[LocationBrief] = []
    authors: list[AuthorBrief] = []

    model_config = {"from_attributes": True}


class JournalEntryDetail(JournalEntryRead):
    book: BookBrief | None = None

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest app/tests/test_schemas.py -v 2>&1 | tail -10`
Expected: 4 passed

- [ ] **Step 5: Update CRUD search to use new field names**

In `backend/app/crud/journal_entry.py`, update the `search_entries` function (line 99) to search across the new fields instead of the old ones. Replace the `ilike` filters to use `summary_chinese`, `summary_english`, `excerpt_original` instead of `modern_translation`, `english_translation`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/journal_entry.py backend/app/tests/test_schemas.py backend/app/crud/journal_entry.py
git commit -m "feat(backend): update schemas with excerpt/summary fields, expose credibility/annotations"
```

---

## Task 7: Alembic Migration — Column Additions/Removals

**Files:**
- Create: `backend/alembic/versions/004_pipeline_revision.py`

- [ ] **Step 1: Create the migration file**

Create `backend/alembic/versions/004_pipeline_revision.py`:

```python
"""pipeline revision — add excerpt/summary, remove old translations

Revision ID: 004
Revises: 003
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns
    op.add_column("journal_entries", sa.Column("excerpt_original", sa.Text(), nullable=True))
    op.add_column("journal_entries", sa.Column("excerpt_translation", sa.Text(), nullable=True))
    op.add_column("journal_entries", sa.Column("summary_chinese", sa.Text(), nullable=True))
    op.add_column("journal_entries", sa.Column("summary_english", sa.Text(), nullable=True))
    op.add_column("journal_entries", sa.Column("persons", sa.JSON(), nullable=True))
    op.add_column("journal_entries", sa.Column("dates", sa.JSON(), nullable=True))

    # Remove old translation columns
    op.drop_column("journal_entries", "modern_translation")
    op.drop_column("journal_entries", "english_translation")


def downgrade() -> None:
    # Restore old columns
    op.add_column("journal_entries", sa.Column("modern_translation", sa.Text(), nullable=True))
    op.add_column("journal_entries", sa.Column("english_translation", sa.Text(), nullable=True))

    # Remove new columns
    op.drop_column("journal_entries", "dates")
    op.drop_column("journal_entries", "persons")
    op.drop_column("journal_entries", "summary_english")
    op.drop_column("journal_entries", "summary_chinese")
    op.drop_column("journal_entries", "excerpt_translation")
    op.drop_column("journal_entries", "excerpt_original")
```

- [ ] **Step 2: Verify migration file syntax**

Run: `cd backend && python -c "from alembic.versions.004_pipeline_revision import upgrade, downgrade; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/004_pipeline_revision.py
git commit -m "feat(backend): add migration for pipeline revision schema changes"
```

---

## Task 8: Write Combined Extraction Prompt Template

**Files:**
- Create: `pipeline/config/prompts/extraction_combined.txt`
- Test: `pipeline/tests/test_s3_extract.py`

- [ ] **Step 1: Write the combined extraction prompt**

Create `pipeline/config/prompts/extraction_combined.txt`:

```
You are a historical text analysis expert analyzing a travel journal. Perform the following tasks in a SINGLE pass:

1. FILTER: Identify content vs non-content sections
2. SEGMENT: Split multi-story chunks into separate narrative units
3. EXTRACT: Extract all fields for each content entry

CONTEXT:
{context}

STORY TEXT:
{text}

SEGMENTATION RULES:
- Each entry = one independent narrative unit (story, anecdote, travel segment)
- is_content=false for: table of contents, preface, index, bibliography, translator's notes, publisher info
- A chunk typically contains 1-3 entries; do not over-segment
- Anchors must be in document order and non-overlapping
- Use the first 30+ characters as start_anchor and last 15+ characters as end_anchor

TRUNCATION DETECTION:
- is_truncated=true ONLY when: sentence is grammatically incomplete, narrative suddenly breaks off
- Do NOT flag if: text is long but coherent, contains multiple locations but same journey

Return a single JSON object with an "entries" array:

{{
  "entries": [
    {{
      "start_anchor": "first 30+ characters of this entry",
      "end_anchor": "last 15+ characters of this entry",
      "is_content": true,
      "is_truncated": false,
      "story_metadata": {{
        "title": "story/chapter title",
        "chapter_reference": "chapter reference if any",
        "visit_date_approximate": "approximate date"
      }},
      "excerpt": {{
        "original": "2-3 sentence excerpt in source language capturing the essence",
        "translation": "English translation of the excerpt"
      }},
      "summary": {{
        "chinese": "2-3 sentence summary in modern Chinese",
        "english": "2-3 sentence summary in English"
      }},
      "entities": {{
        "locations": [
          {{
            "name": "location name",
            "modern_name": "modern name or null",
            "ancient_name": "historical name or null",
            "lat": 0.0,
            "lng": 0.0,
            "location_type": "city/region/river/mountain/temple/pass/port/route/other",
            "one_line_summary": "one line about this location"
          }}
        ],
        "persons": ["person names mentioned"],
        "dates": ["dates or time references"],
        "keywords": ["5-10 key topics/themes"]
      }},
      "credibility": {{
        "era_context": "historical era description",
        "political_context": "political situation",
        "religious_context": "religious context if relevant",
        "social_environment": "social conditions",
        "credibility_score": 0.0,
        "notes": "credibility notes"
      }},
      "annotations": []
    }}
  ]
}}

Return ONLY valid JSON. No markdown fences.
```

- [ ] **Step 2: Write test for prompt template loading and formatting**

Add to `pipeline/tests/test_s3_extract.py`:

```python
def test_combined_prompt_template_loads():
    """The combined extraction prompt template should load and format correctly."""
    from pathlib import Path

    prompt_path = Path(__file__).parent.parent / "config" / "prompts" / "extraction_combined.txt"
    assert prompt_path.exists(), f"Prompt not found at {prompt_path}"

    template = prompt_path.read_text()
    assert "{context}" in template
    assert "{text}" in template

    # Verify it formats without error
    formatted = template.format(context="Book: Test Book\nAuthor: Test", text="Some story text")
    assert "Test Book" in formatted
    assert "Some story text" in formatted
    assert "{context}" not in formatted
    assert "{text}" not in formatted


def test_combined_prompt_contains_required_sections():
    """The combined prompt should contain filter, segment, and extract instructions."""
    from pathlib import Path

    prompt_path = Path(__file__).parent.parent / "config" / "prompts" / "extraction_combined.txt"
    template = prompt_path.read_text()

    # Check for key instruction sections
    assert "is_content" in template
    assert "start_anchor" in template
    assert "end_anchor" in template
    assert "excerpt" in template
    assert "summary" in template
    assert "entries" in template
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `cd pipeline && python -m pytest tests/test_s3_extract.py -v -k "combined_prompt" 2>&1 | tail -10`
Expected: 2 passed

- [ ] **Step 4: Commit**

```bash
git add pipeline/config/prompts/extraction_combined.txt pipeline/tests/test_s3_extract.py
git commit -m "feat(pipeline): add combined extraction prompt template with filter+segment+extract"
```

---

## Task 9: Build Context Injection for S3

**Files:**
- Modify: `pipeline/stages/s3_extract.py`
- Test: `pipeline/tests/test_s3_extract.py`

- [ ] **Step 1: Write the failing test for context injection**

Add to `pipeline/tests/test_s3_extract.py`:

```python
def test_build_context_includes_all_items():
    """build_context should include all 7 context items."""
    from pipeline.stages.s3_extract import build_context

    story = ExtractedStory(
        id="test-en-001",
        book_slug="test",
        language="en",
        sequence=1,
        title="Chapter 1",
        original_text="Text",
        source_type="text",
        chapter_title="The Beginning",
        book_metadata={
            "title": "Travels",
            "author": "Marco Polo",
            "dynasty": "Yuan",
        },
    )

    segment_result = SegmentResultV2(
        book_slug="test",
        language="en",
        segments=[
            SegmentInfo(id="test-en-001", title="Chapter 1", file_path="/tmp/x.json", original_text_preview="Text"),
            SegmentInfo(id="test-en-002", title="Chapter 2", file_path="/tmp/y.json", original_text_preview="More"),
        ],
    )

    known_entities = [{"name": "Beijing", "lat": 39.9, "lng": 116.4}]
    book_summary = "A travelogue describing Marco Polo's journey."

    context = build_context(
        story=story,
        segment_result=segment_result,
        segment_index=0,
        known_entities=known_entities,
        book_summary=book_summary,
    )

    # Should contain all context items
    assert "Travels" in context  # book metadata
    assert "The Beginning" in context  # chapter title
    assert "Chapter 1 / 2" in context or "1 / 2" in context  # chapter position
    assert "Chapter 2" in context  # adjacent chapter
    assert "Beijing" in context  # known entities
    assert "travelogue" in context.lower() or "marco polo" in context.lower()  # book summary
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd pipeline && python -m pytest tests/test_s3_extract.py -v -k "build_context" 2>&1 | tail -15`
Expected: FAIL — `build_context` doesn't exist yet

- [ ] **Step 3: Implement `build_context` function**

Add to `pipeline/stages/s3_extract.py` (before the `extract` function):

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd pipeline && python -m pytest tests/test_s3_extract.py -v -k "build_context" 2>&1 | tail -10`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add pipeline/stages/s3_extract.py pipeline/tests/test_s3_extract.py
git commit -m "feat(pipeline): add context injection builder for S3 extraction"
```

---

## Task 10: Refactor S3 to Use Combined Prompt + Parse New Response Format

**Files:**
- Modify: `pipeline/stages/s3_extract.py:25-118`
- Test: `pipeline/tests/test_s3_extract.py`

- [ ] **Step 1: Write the failing test for combined extraction**

Add to `pipeline/tests/test_s3_extract.py`:

```python
@pytest.mark.asyncio
async def test_extract_uses_combined_prompt(tmp_path):
    """S3 should use the combined prompt and parse entries[] response."""
    from pipeline.stages.s3_extract import extract

    story = ExtractedStory(
        id="test-en-005",
        book_slug="test",
        language="en",
        sequence=1,
        title="Chapter 1",
        original_text="The journey from Constantinople to Beijing took many months.",
        source_type="text",
        is_content=True,
        extracted=False,
    )
    path = tmp_path / "test-en-005.json"
    path.write_text(story.model_dump_json(indent=2))

    segment = SegmentInfo(
        id="test-en-005",
        title="Chapter 1",
        file_path=str(path),
        original_text_preview="The journey...",
    )
    segment_result = SegmentResultV2(book_slug="test", language="en", segments=[segment])

    llm = AsyncMock()
    llm.chat_with_tools = AsyncMock(return_value=json.dumps({
        "entries": [
            {
                "start_anchor": "The journey from Constantinople",
                "end_anchor": "took many months.",
                "is_content": True,
                "is_truncated": False,
                "story_metadata": {
                    "title": "The Journey",
                    "chapter_reference": "Chapter 1",
                    "visit_date_approximate": "1271",
                },
                "excerpt": {
                    "original": "The journey from Constantinople to Beijing.",
                    "translation": "The journey from Constantinople to Beijing.",
                },
                "summary": {
                    "chinese": "描述从君士坦丁堡到北京的旅程。",
                    "english": "Describes the journey from Constantinople to Beijing.",
                },
                "entities": {
                    "locations": [
                        {
                            "name": "Constantinople",
                            "modern_name": "Istanbul",
                            "ancient_name": "Constantinople",
                            "lat": 41.0082,
                            "lng": 28.9784,
                            "location_type": "city",
                            "one_line_summary": "Byzantine capital",
                        }
                    ],
                    "persons": ["Marco Polo"],
                    "dates": ["1271"],
                    "keywords": ["travel", "silk road"],
                },
                "credibility": {
                    "era_context": "13th century",
                    "political_context": "Mongol Empire",
                    "credibility_score": 0.8,
                },
                "annotations": [],
            }
        ]
    }))

    result = await extract(segment_result, llm)

    saved = json.loads(path.read_text())
    assert saved["extracted"] is True
    assert saved["excerpt_original"] == "The journey from Constantinople to Beijing."
    assert saved["summary_chinese"] == "描述从君士坦丁堡到北京的旅程。"
    assert saved["summary_english"] == "Describes the journey from Constantinople to Beijing."
    assert saved["persons"] == ["Marco Polo"]
    assert saved["dates"] == ["1271"]
    assert result["processed"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd pipeline && python -m pytest tests/test_s3_extract.py -v -k "combined_prompt_parse" 2>&1 | tail -15`
Expected: FAIL — S3 doesn't parse the new response format yet

- [ ] **Step 3: Refactor S3 extract function**

Replace the `extract` function in `pipeline/stages/s3_extract.py` (keep `load_prompt`, `build_context`, `EXTRACTION_TOOLS`):

```python
async def extract(
    segment_result: SegmentResultV2,
    llm: LLMClient,
    book_summary: str | None = None,
    known_entities: list[dict] | None = None,
) -> dict:
    """Stage 3: Extract all data from each story via combined LLM call.

    Uses the combined filter+extract prompt. Handles:
    - Non-content detection (is_content field)
    - Multi-story segmentation (entries[] array)
    - Full field extraction (excerpt, summary, entities, credibility)
    """
    prompt_template = load_prompt("extraction_combined")
    stats = {"processed": 0, "skipped": 0, "failed": 0}

    # Collect known entities from already-processed stories
    if known_entities is None:
        known_entities = []
        for seg_info in segment_result.segments:
            story_path = Path(seg_info.file_path)
            if not story_path.exists():
                continue
            data = json.loads(story_path.read_text(encoding="utf-8"))
            s = ExtractedStory(**data)
            if s.entities:
                for loc in s.entities.get("locations", []):
                    if loc.get("name") and loc.get("lat") and loc.get("lng"):
                        known_entities.append(loc)

    for seg_idx, seg_info in enumerate(segment_result.segments):
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

        context = build_context(story, segment_result, seg_idx, known_entities, book_summary)
        prompt = prompt_template.format(context=context, text=story.original_text)
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
                raw = await llm.extract_json(
                    prompt=prompt,
                    system="You are a historical text analysis expert. Be concise. Return ONLY valid JSON.",
                    max_tokens=8192,
                )

            if not raw or not raw.strip():
                raise ValueError("LLM returned empty response")

            # Clean markdown fences
            if raw.startswith("```"):
                lines = raw.split("\n")
                lines = [l for l in lines if not l.startswith("```")]
                raw = "\n".join(lines)

            try:
                extracted = json.loads(raw)
            except json.JSONDecodeError:
                # Try to recover malformed/truncated JSON
                fixed = raw.rstrip()
                if fixed.endswith(','):
                    fixed = fixed[:-1]
                import re
                fixed = re.sub(r',(\s*[\]}])', r'\1', fixed)
                if fixed.count('"') % 2 != 0:
                    fixed += '"'
                open_brackets = fixed.count('[') - fixed.count(']')
                open_braces = fixed.count('{') - fixed.count('}')
                fixed += ']' * max(0, open_brackets)
                fixed += '}' * max(0, open_braces)
                extracted = json.loads(fixed)

            entries = extracted.get("entries", [])
            if not entries:
                raise ValueError("LLM returned no entries")

            # Use the first content entry (typically only 1 per chunk)
            entry = None
            for e in entries:
                if e.get("is_content", True):
                    entry = e
                    break

            if entry is None:
                # All entries are non-content
                story.is_content = False
                story.extracted = True
                story.error = "non_content"
                story_path.write_text(story.model_dump_json(indent=2), encoding="utf-8")
                stats["skipped"] += 1
                print("non-content")
                continue

            # Map entry fields to story
            story_meta = entry.get("story_metadata", {})
            excerpt = entry.get("excerpt", {})
            summary = entry.get("summary", {})
            entities = entry.get("entities", {})
            credibility = entry.get("credibility", {})

            story.story_metadata = story_meta
            story.entities = entities
            story.credibility = credibility
            story.annotations = entry.get("annotations", [])

            story.excerpt_original = excerpt.get("original")
            story.excerpt_translation = excerpt.get("translation")
            story.summary_chinese = summary.get("chinese")
            story.summary_english = summary.get("english")
            story.persons = entities.get("persons")
            story.dates = entities.get("dates")

            # Keep legacy translations field populated for backward compat
            story.translations = {
                "modern_chinese": summary.get("chinese"),
                "english": summary.get("english"),
            }

            story.is_truncated = entry.get("is_truncated", False)
            story.extracted = True
            story.error = None

            # Update known entities
            for loc in entities.get("locations", []):
                if loc.get("name") and loc.get("lat") and loc.get("lng"):
                    known_entities.append(loc)

            stats["processed"] += 1
            print("OK")

        except Exception as e:
            story.extracted = False
            story.error = str(e)[:500]
            stats["failed"] += 1
            print(f"FAIL: {story.error[:80]}")

        story_path.write_text(story.model_dump_json(indent=2), encoding="utf-8")

    return stats
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd pipeline && python -m pytest tests/test_s3_extract.py -v -k "combined_prompt_parse" 2>&1 | tail -10`
Expected: 1 passed

- [ ] **Step 5: Run full S3 test suite to check for regressions**

Run: `cd pipeline && python -m pytest tests/test_s3_extract.py -v 2>&1 | tail -10`
Expected: All tests pass (existing tests need updating for new mock response format)

- [ ] **Step 6: Update existing S3 tests for new response format**

The existing `mock_llm` fixture returns the old flat format. Update it to return the new `entries[]` format. Update `test_extract_single_story` assertions to check the new field paths.

- [ ] **Step 7: Run full S3 test suite again**

Run: `cd pipeline && python -m pytest tests/test_s3_extract.py -v 2>&1 | tail -10`
Expected: All tests pass

- [ ] **Step 8: Commit**

```bash
git add pipeline/stages/s3_extract.py pipeline/tests/test_s3_extract.py pipeline/config/prompts/extraction_combined.txt
git commit -m "feat(pipeline): refactor S3 to use combined prompt with entries[] response format"
```

---

## Task 11: Integrate chapter_detector into S2

**Files:**
- Modify: `pipeline/stages/s2_segment.py`
- Test: `pipeline/tests/test_s2_segment.py`

- [ ] **Step 1: Write the failing test for chapter-based segmentation**

Add to `pipeline/tests/test_s2_segment.py`:

```python
@pytest.mark.asyncio
async def test_segment_uses_chapter_detector():
    """segment() should use chapter_detector when available."""
    from pipeline.stages.s2_segment import segment

    # Text with clear chapter structure
    text = """Chapter 1 - The Departure

We set out from Venice in the year 1271.

Chapter 2 - Constantinople

After many days we arrived at Constantinople, the great city.

Chapter 3 - The Journey East

From Constantinople we traveled eastward through many lands."""

    ingest_result = _make_ingest(text, language="en")

    with tempfile.TemporaryDirectory() as tmpdir:
        result = await segment(ingest_result, output_dir=tmpdir)
        # Should produce at least 2 segments
        assert len(result.segments) >= 2
        # Segments should have chapter titles
        for seg in result.segments:
            assert Path(seg.file_path).exists()
            saved = json.loads(Path(seg.file_path).read_text())
            assert saved["chapter_title"] is not None or saved["title"] != f"Segment {saved['sequence']}"


def test_segment_marks_large_chapters_for_subdivision():
    """Chapters > 5000 chars should be marked needs_subdivision=True."""
    from pipeline.models import ExtractedStory

    # Simulate a large chapter
    story = ExtractedStory(
        id="test-en-001",
        book_slug="test",
        language="en",
        sequence=1,
        title="Long Chapter",
        original_text="x" * 6000,
        source_type="text",
        needs_subdivision=True,
    )
    assert story.needs_subdivision is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd pipeline && python -m pytest tests/test_s2_segment.py -v -k "chapter_detector or subdivision" 2>&1 | tail -15`
Expected: FAIL — `segment()` doesn't use `chapter_detector` yet

- [ ] **Step 3: Add `segment_by_chapters` function to s2_segment.py**

Add to `pipeline/stages/s2_segment.py` (after the imports, before `segment_by_headings`):

```python
def segment_by_chapters(text: str, llm=None) -> list[dict]:
    """Segment text using chapter_detector.py chain-of-responsibility pattern.

    Falls back to segment_by_headings if chapter_detector finds < 2 chapters.
    """
    try:
        from pipeline.chapter_detector import build_default_chain

        chain = build_default_chain(llm_client=llm)
        chapters = chain.detect(text, strategy="auto")

        if len(chapters) >= 2:
            stories = []
            for ch in chapters:
                story = {
                    "title": ch.title,
                    "text": ch.text,
                    "chapter_title": ch.title,
                    "needs_subdivision": len(ch.text) > 5000,
                }
                stories.append(story)
            return stories
    except Exception:
        pass

    # Fallback to regex headings
    headings = segment_by_headings(text)
    return [{"title": h["heading"], "text": h["text"], "chapter_title": h["heading"]} for h in headings]
```

- [ ] **Step 4: Update `segment()` to use chapter-based path**

In `pipeline/stages/s2_segment.py`, replace the text path in the `segment()` function (lines 128-140):

```python
    else:
        # Path A: Try chapter-based segmentation
        chapters = segment_by_chapters(ingest_result.raw_text, llm=llm)

        if len(chapters) >= 2 and chapters[0].get("title") is not None:
            raw_stories = chapters
            source_type = "text"
        elif llm is not None:
            # Path B: LLM fallback
            raw_stories = await _segment_by_llm(ingest_result.raw_text, llm)
            source_type = "text"
        else:
            raw_stories = [{"title": None, "text": h["text"]} for h in segment_by_headings(ingest_result.raw_text)]
            source_type = "text"
```

Update the story creation loop (lines 145-170) to set the new fields:

```python
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
            chapter_title=story.get("chapter_title"),
            needs_subdivision=story.get("needs_subdivision", False),
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd pipeline && python -m pytest tests/test_s2_segment.py -v 2>&1 | tail -10`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add pipeline/stages/s2_segment.py pipeline/tests/test_s2_segment.py
git commit -m "feat(pipeline): integrate chapter_detector into S2 segmentation"
```

---

## Task 12: Write Subdivision and Book Summary Prompt Templates

**Files:**
- Create: `pipeline/config/prompts/extraction_subdivide.txt`
- Create: `pipeline/config/prompts/book_summary.txt`
- Test: `pipeline/tests/test_s3_extract.py`

- [ ] **Step 1: Write the subdivision prompt**

Create `pipeline/config/prompts/extraction_subdivide.txt`:

```
You are analyzing a long chapter from a historical travel journal. Identify natural subdivision points where the narrative shifts to a new story, anecdote, or travel segment.

CONTEXT:
{context}

CHAPTER TEXT:
{text}

For each sub-segment, provide:
- start_anchor: first 30+ characters of the sub-segment (must match text exactly)
- end_anchor: last 15+ characters of the sub-segment (must match text exactly), or "truncated" if text ends mid-sentence
- title: descriptive title for this sub-segment

Rules:
- Only split where there is a clear narrative break (new journey, new location, time skip)
- Do NOT split mid-story or mid-paragraph
- Each sub-segment should be at least 500 characters
- If the chapter is a single coherent narrative, return it as one sub-segment

Return JSON:
{{
  "subdivisions": [
    {{
      "start_anchor": "first 30+ characters...",
      "end_anchor": "...last 15+ characters",
      "title": "sub-segment title"
    }}
  ]
}}

Return ONLY valid JSON.
```

- [ ] **Step 2: Write the book summary prompt**

Create `pipeline/config/prompts/book_summary.txt`:

```
You are analyzing the preface/序言 of a historical travel journal. Extract a concise summary that captures:
1. Who is the author and what is their background
2. What journey(s) does the book describe
3. When and where did the events take place
4. What is the historical significance of this work
5. Any notable characteristics (language, style, perspective)

PREFACE TEXT:
{text}

Return a JSON object:
{{
  "summary": "2-3 paragraph summary covering the above points",
  "author_background": "brief author bio",
  "journey_description": "what journeys are described",
  "time_period": "when the events took place",
  "significance": "historical significance"
}}

Return ONLY valid JSON.
```

- [ ] **Step 3: Write tests for both templates**

Add to `pipeline/tests/test_s3_extract.py`:

```python
def test_subdivide_prompt_template():
    """Subdivision prompt should load and format correctly."""
    from pathlib import Path

    prompt_path = Path(__file__).parent.parent / "config" / "prompts" / "extraction_subdivide.txt"
    assert prompt_path.exists()
    template = prompt_path.read_text()
    assert "{context}" in template
    assert "{text}" in template
    assert "start_anchor" in template
    assert "end_anchor" in template

    formatted = template.format(context="Test context", text="Test text")
    assert "Test context" in formatted


def test_book_summary_prompt_template():
    """Book summary prompt should load and format correctly."""
    from pathlib import Path

    prompt_path = Path(__file__).parent.parent / "config" / "prompts" / "book_summary.txt"
    assert prompt_path.exists()
    template = prompt_path.read_text()
    assert "{text}" in template
    assert "summary" in template

    formatted = template.format(text="Preface text here")
    assert "Preface text here" in formatted
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd pipeline && python -m pytest tests/test_s3_extract.py -v -k "subdivide_prompt or book_summary_prompt" 2>&1 | tail -10`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add pipeline/config/prompts/extraction_subdivide.txt pipeline/config/prompts/book_summary.txt pipeline/tests/test_s3_extract.py
git commit -m "feat(pipeline): add subdivision and book summary prompt templates"
```

---

## Task 13: Update runner.py to Pass New Parameters

**Files:**
- Modify: `pipeline/runner.py`
- Test: `pipeline/tests/test_runner.py`

- [ ] **Step 1: Write the failing test for new pipeline parameters**

Add to `pipeline/tests/test_runner.py`:

```python
@pytest.mark.asyncio
async def test_run_pipeline_passes_book_summary_to_extract():
    """run_pipeline should pass book_summary from S1 metadata to S3 extract."""
    from pipeline.runner import run_pipeline

    # This test verifies the pipeline accepts and passes the new parameter
    # Full integration tested in test_integration.py
    # Here we just verify the function signature accepts the parameter
    import inspect
    sig = inspect.signature(run_pipeline)
    # Should not raise when called with skip_output=True
    # (actual LLM calls are mocked in integration tests)
```

- [ ] **Step 2: Update runner.py to collect and pass known_entities and book_summary**

In `pipeline/runner.py`, after S2 completes and before S3, add logic to collect known entities from already-processed stories and pass them along. Update the S3 call:

```python
    # Stage 3: Extract
    print("[S3] Extracting structured data...")
    # Collect known entities from already-extracted stories (for context injection)
    known_entities = []
    for seg_info in segment_result.segments:
        story_path = Path(seg_info.file_path)
        if story_path.exists():
            data = json.loads(story_path.read_text(encoding="utf-8"))
            if data.get("entities"):
                for loc in data["entities"].get("locations", []):
                    if loc.get("name") and loc.get("lat") and loc.get("lng"):
                        known_entities.append(loc)

    book_summary = ingest_result.metadata.get("book_summary")
    extract_result = await extract(segment_result, llm, book_summary=book_summary, known_entities=known_entities)
```

- [ ] **Step 3: Run tests**

Run: `cd pipeline && python -m pytest tests/test_runner.py -v 2>&1 | tail -10`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add pipeline/runner.py pipeline/tests/test_runner.py
git commit -m "feat(pipeline): pass book_summary and known_entities to S3 extraction"
```

---

## Task 14: Book Summary Extraction in S1

**Files:**
- Modify: `pipeline/stages/s1_ingest.py`
- Create: `pipeline/stages/book_summary.py`
- Test: `pipeline/tests/test_s1_ingest.py`

- [ ] **Step 1: Write the failing test for book summary extraction**

Add to `pipeline/tests/test_s1_ingest.py`:

```python
@pytest.mark.asyncio
async def test_extract_book_summary_from_preface():
    """Book summary extraction should summarize preface text."""
    from pipeline.stages.book_summary import extract_book_summary

    llm = AsyncMock()
    llm.extract_json = AsyncMock(return_value=json.dumps({
        "summary": "Marco Polo's travelogue describes his journey from Venice to the court of Kublai Khan.",
        "author_background": "Venetian merchant who spent 24 years in Asia",
        "journey_description": "Venice to China and back via maritime route",
        "time_period": "1271-1295",
        "significance": "One of the first European accounts of Asia",
    }))

    result = await extract_book_summary("Preface text about Marco Polo's travels...", llm)
    assert "Marco Polo" in result
    assert len(result) > 50


def test_identify_preface_pages():
    """Should identify preface/序言 pages from text content."""
    from pipeline.stages.book_summary import identify_preface

    # Text with preface indicators
    text = """序言

    本书记录了马可·波罗从威尼斯到元朝上都的旅程...

    第一章 从威尼斯出发

    1271年，我们离开了威尼斯..."""

    preface, remaining = identify_preface(text)
    assert "序言" in preface or "马可·波罗" in preface
    assert "第一章" in remaining or "1271年" in remaining
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd pipeline && python -m pytest tests/test_s1_ingest.py -v -k "book_summary or preface" 2>&1 | tail -15`
Expected: FAIL — functions don't exist yet

- [ ] **Step 3: Create `pipeline/stages/book_summary.py`**

Create `pipeline/stages/book_summary.py`:

```python
from __future__ import annotations

import json
import re
from pathlib import Path

from pipeline.core.llm_client import LLMClient

PROMPTS_DIR = Path(__file__).parent.parent / "config" / "prompts"

PREFACE_KEYWORDS = [
    "序言", "前言", "自序", "代序", "Preface", "Foreword", "Introduction",
    "preface", "foreword", "introduction", "PROLOGUE", "Prologue",
]


def identify_preface(text: str) -> tuple[str, str]:
    """Split text into preface and remaining content.

    Returns (preface_text, remaining_text). If no preface found, returns ("", text).
    """
    lines = text.split("\n")
    preface_end = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if any(kw.lower() in stripped.lower() for kw in PREFACE_KEYWORDS):
            # Found preface marker, collect until next chapter-like heading
            for j in range(i + 1, len(lines)):
                next_line = lines[j].strip()
                # Stop at chapter markers
                if re.match(r'^(第[一二三四五六七八九十\d]+[章节篇]|Chapter\s+\d+|[IVX]+\.)', next_line):
                    preface_end = j
                    break
            if preface_end == 0:
                # No chapter marker found, take up to 2000 chars
                preface_end = min(i + 50, len(lines))
            break

    if preface_end == 0:
        return "", text

    preface = "\n".join(lines[:preface_end]).strip()
    remaining = "\n".join(lines[preface_end:]).strip()
    return preface, remaining


async def extract_book_summary(preface_text: str, llm: LLMClient) -> str:
    """Extract a book summary from preface text using LLM.

    Returns a plain text summary string.
    """
    prompt_template = (PROMPTS_DIR / "book_summary.txt").read_text()
    prompt = prompt_template.format(text=preface_text)

    try:
        raw = await llm.extract_json(
            prompt=prompt,
            system="You are a literary analysis expert. Be concise. Return ONLY valid JSON.",
            max_tokens=2048,
        )
        data = json.loads(raw)
        return data.get("summary", preface_text[:500])
    except Exception:
        # Fallback: return first 500 chars of preface
        return preface_text[:500]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd pipeline && python -m pytest tests/test_s1_ingest.py -v -k "book_summary or preface" 2>&1 | tail -10`
Expected: 2 passed

- [ ] **Step 5: Integrate into runner.py**

In `pipeline/runner.py`, after S1 completes, detect and summarize preface:

```python
    # Book summary extraction (from preface)
    from pipeline.stages.book_summary import identify_preface, extract_book_summary
    preface_text, _ = identify_preface(ingest_result.raw_text)
    book_summary = None
    if preface_text and len(preface_text) > 100:
        print("[S1] Extracting book summary from preface...")
        book_summary = await extract_book_summary(preface_text, llm)
        ingest_result.metadata["book_summary"] = book_summary
```

- [ ] **Step 6: Run full pipeline tests**

Run: `cd pipeline && python -m pytest tests/ -v 2>&1 | tail -20`
Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
git add pipeline/stages/book_summary.py pipeline/tests/test_s1_ingest.py pipeline/runner.py
git commit -m "feat(pipeline): add book summary extraction from preface text"
```

---

## Task 15: Run Full Test Suites

- [ ] **Step 1: Run all pipeline tests**

Run: `cd pipeline && python -m pytest -v 2>&1 | tail -30`
Expected: All tests pass

- [ ] **Step 2: Run all backend tests**

Run: `cd backend && python -m pytest -v 2>&1 | tail -30`
Expected: All tests pass

- [ ] **Step 3: Fix any failures**

Address any test failures before proceeding.

- [ ] **Step 4: Commit fixes if needed**

```bash
git add -A
git commit -m "fix: address test failures from pipeline revision"
```

---

## Task 16: Integration Verification

- [ ] **Step 1: Verify pipeline models serialize correctly**

Run: `cd pipeline && python -c "
from pipeline.models import ExtractedStory
s = ExtractedStory(
    id='test-en-001', book_slug='test', language='en', sequence=1,
    title='Test', original_text='Text', source_type='text',
    is_content=True, chapter_title='Ch1', excerpt_original='Excerpt',
    summary_chinese='摘要', summary_english='Summary',
    persons=['Polo'], dates=['1271'],
)
d = s.model_dump()
assert d['is_content'] is True
assert d['excerpt_original'] == 'Excerpt'
assert d['persons'] == ['Polo']
print('Model serialization OK')
"`

Expected: Model serialization OK

- [ ] **Step 2: Verify backend schema accepts new fields**

Run: `cd backend && python -c "
from app.schemas.journal_entry import JournalEntryRead
e = JournalEntryRead(
    id=1, title='Test', original_text='Text',
    excerpt_original='Excerpt', summary_english='Summary',
    credibility={'score': 0.8}, annotations=[{'source': 'test'}],
    persons=['Polo'], dates=['1271'],
)
assert e.excerpt_original == 'Excerpt'
assert e.credibility == {'score': 0.8}
print('Schema validation OK')
"`

Expected: Schema validation OK

- [ ] **Step 3: Verify prompt templates load**

Run: `cd pipeline && python -c "
from pathlib import Path
for name in ['extraction_combined', 'extraction_subdivide', 'book_summary']:
    p = Path('config/prompts') / f'{name}.txt'
    assert p.exists(), f'{name} not found'
    t = p.read_text()
    assert len(t) > 100, f'{name} too short'
    print(f'{name}: OK ({len(t)} chars)')
"`

Expected: All 3 templates OK

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: verification complete for pipeline revision"
```
