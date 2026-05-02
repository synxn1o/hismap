from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text

from app.core.database import Base

entry_locations = Table(
    "entry_locations",
    Base.metadata,
    Column("entry_id", Integer, ForeignKey("journal_entries.id", ondelete="CASCADE"), primary_key=True),
    Column("location_id", Integer, ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True),
    Column("location_order", Integer, nullable=False, default=0),
    Column("importance", Integer, nullable=False, server_default="0"),
)

entry_authors = Table(
    "entry_authors",
    Base.metadata,
    Column("entry_id", Integer, ForeignKey("journal_entries.id", ondelete="CASCADE"), primary_key=True),
    Column("author_id", Integer, ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True),
)

relation_locations = Table(
    "relation_locations",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("from_location_id", Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False),
    Column("to_location_id", Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False),
    Column("relation_type", String(100), nullable=False),
    Column("description", Text),
)
