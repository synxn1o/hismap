from pydantic import BaseModel


class RelatedLocation(BaseModel):
    id: int
    name: str
    relation_type: str
    description: str | None = None


class LocationBase(BaseModel):
    name: str
    modern_name: str | None = None
    ancient_name: str | None = None
    latitude: float
    longitude: float
    location_type: str | None = None
    ancient_region: str | None = None
    one_line_summary: str | None = None
    location_rationale: str | None = None
    academic_disputes: str | None = None
    credibility_notes: str | None = None
    today_remains: str | None = None


class LocationCreate(LocationBase):
    pass


class LocationUpdate(BaseModel):
    name: str | None = None
    modern_name: str | None = None
    ancient_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_type: str | None = None
    ancient_region: str | None = None
    one_line_summary: str | None = None
    location_rationale: str | None = None
    academic_disputes: str | None = None
    credibility_notes: str | None = None
    today_remains: str | None = None


class LocationRead(LocationBase):
    id: int

    model_config = {"from_attributes": True}


class LocationDetail(LocationRead):
    entries: list["JournalEntryRead"] = []
    related_locations: list[RelatedLocation] = []

    model_config = {"from_attributes": True}


from app.schemas.journal_entry import JournalEntryRead  # noqa: E402

LocationDetail.model_rebuild()
