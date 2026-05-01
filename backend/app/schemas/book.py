from pydantic import BaseModel


class BookBase(BaseModel):
    title: str
    author: str | None = None
    dynasty: str | None = None
    era_start: int | None = None
    era_end: int | None = None
    description: str | None = None
    source_text: str | None = None


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: str | None = None
    author: str | None = None
    dynasty: str | None = None
    era_start: int | None = None
    era_end: int | None = None
    description: str | None = None
    source_text: str | None = None


class BookRead(BookBase):
    id: int

    model_config = {"from_attributes": True}


class BookDetail(BookRead):
    entries: list["JournalEntryRead"] = []

    model_config = {"from_attributes": True}


from app.schemas.journal_entry import JournalEntryRead  # noqa: E402

BookDetail.model_rebuild()
