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
    # v2 models
    SegmentInfo,
    SegmentResultV2,
    ExtractedStory,
    OutputResult,
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


# === v2 model tests ===


def test_v2_ingest_result_has_new_fields():
    r = IngestResult(
        source_file="test.pdf",
        file_type="pdf_digital",
        raw_text="hello world",
        page_count=5,
        ocr_method="direct",
        book_slug="test-book",
        detected_language="en",
    )
    assert r.book_slug == "test-book"
    assert r.detected_language == "en"


def test_segment_info():
    s = SegmentInfo(
        id="test-book-en-001",
        title="Chapter 1",
        file_path="/tmp/test-book-en-001.json",
        original_text_preview="First 200 chars...",
    )
    assert s.id == "test-book-en-001"
    assert s.file_path.endswith(".json")


def test_v2_segment_result():
    s = SegmentInfo(
        id="test-book-en-001",
        title="Chapter 1",
        file_path="/tmp/test-book-en-001.json",
        original_text_preview="preview",
    )
    r = SegmentResultV2(book_slug="test-book", language="en", segments=[s])
    assert r.book_slug == "test-book"
    assert len(r.segments) == 1


def test_extracted_story():
    s = ExtractedStory(
        id="test-book-en-001",
        book_slug="test-book",
        language="en",
        sequence=1,
        title="Chapter 1",
        original_text="Full story text here...",
        source_type="text",
        page_range=[1, 3],
        extracted=True,
    )
    assert s.extracted is True
    assert s.error is None


def test_output_result():
    r = OutputResult(books=1, authors=1, locations=5, entries=10)
    assert r.entries == 10


def test_extracted_story_default_extracted_is_false():
    s = ExtractedStory(
        id="t-001", book_slug="t", language="en", sequence=1,
        title="T", original_text="text", source_type="text",
    )
    assert s.extracted is False
    assert s.error is None
    assert s.book_metadata is None


def test_extracted_story_serialization_roundtrip():
    s = ExtractedStory(
        id="t-001", book_slug="t", language="en", sequence=1,
        title="T", original_text="text", source_type="text",
        extracted=True, credibility={"score": 0.9},
    )
    json_str = s.model_dump_json()
    s2 = ExtractedStory.model_validate_json(json_str)
    assert s2.id == s.id
    assert s2.extracted is True
    assert s2.credibility == {"score": 0.9}


def test_extracted_story_source_type_literal():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ExtractedStory(
            id="t-001", book_slug="t", language="en", sequence=1,
            title="T", original_text="text", source_type="invalid",
        )
