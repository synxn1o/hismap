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
