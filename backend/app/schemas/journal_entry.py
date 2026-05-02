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
