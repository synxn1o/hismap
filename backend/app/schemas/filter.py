from pydantic import BaseModel


class FilterOptions(BaseModel):
    dynasties: list[str]
    authors: list[str]
    location_types: list[str]
    era_contexts: list[str]
