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
    # v2 additions
    book_slug: str = ""
    detected_language: str = "unknown"
    ocr_pages: list[dict] = []  # per-page OCR results for scanned PDFs


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


# === Pipeline v2 models ===


class SegmentInfo(BaseModel):
    id: str
    title: str
    file_path: str
    original_text_preview: str  # first 200 chars for logging


class SegmentResultV2(BaseModel):
    """v2 segment result — replaces v1 SegmentResult."""
    book_slug: str
    language: str
    segments: list[SegmentInfo]


class ExtractedStory(BaseModel):
    """Represents a single story JSON file on disk."""
    id: str
    book_slug: str
    language: str
    sequence: int
    title: str
    original_text: str
    source_type: str  # "text" | "ocr"
    page_range: list[int] = []
    created_at: str = ""
    extracted: bool = False
    error: str | None = None
    # Extracted fields (populated by S3)
    book_metadata: dict | None = None
    story_metadata: dict | None = None
    entities: dict | None = None
    translations: dict | None = None
    credibility: dict | None = None
    annotations: list[dict] | None = None


class OutputResult(BaseModel):
    books: int = 0
    authors: int = 0
    locations: int = 0
    entries: int = 0


# Pipeline state
class PipelineRun(BaseModel):
    id: int | None = None
    source_file: str
    status: str = "pending"  # "pending" | "running" | "stage_N" | "completed" | "failed"
    current_stage: int = 0
    stage_results: dict = {}
    human_review_status: str = "pending"  # "pending" | "approved" | "rejected" | "edited"
    human_review_notes: str | None = None
