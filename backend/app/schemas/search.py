from pydantic import BaseModel


class SearchResult(BaseModel):
    entries: list["JournalEntryRead"]
    total: int


from app.schemas.journal_entry import JournalEntryRead  # noqa: E402

SearchResult.model_rebuild()
