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
