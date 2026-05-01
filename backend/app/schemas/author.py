from pydantic import BaseModel


class AuthorBase(BaseModel):
    name: str
    dynasty: str | None = None
    birth_year: int | None = None
    death_year: int | None = None
    biography: str | None = None


class AuthorCreate(AuthorBase):
    pass


class AuthorUpdate(BaseModel):
    name: str | None = None
    dynasty: str | None = None
    birth_year: int | None = None
    death_year: int | None = None
    biography: str | None = None


class AuthorRead(AuthorBase):
    id: int

    model_config = {"from_attributes": True}


class AuthorDetail(AuthorRead):
    entries: list["JournalEntryRead"] = []

    model_config = {"from_attributes": True}


from app.schemas.journal_entry import JournalEntryRead  # noqa: E402

AuthorDetail.model_rebuild()
