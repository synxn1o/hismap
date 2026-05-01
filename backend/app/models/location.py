from sqlalchemy import Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Location(BaseModel):
    __tablename__ = "locations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    modern_name: Mapped[str | None] = mapped_column(String(200))
    ancient_name: Mapped[str | None] = mapped_column(String(200))
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    # PostGIS geometry — stored as raw SQL in migrations, not in model
    location_type: Mapped[str | None] = mapped_column(String(50))
    ancient_region: Mapped[str | None] = mapped_column(String(200))
    one_line_summary: Mapped[str | None] = mapped_column(Text)
    location_rationale: Mapped[str | None] = mapped_column(Text)
    academic_disputes: Mapped[str | None] = mapped_column(Text)
    credibility_notes: Mapped[str | None] = mapped_column(Text)
    today_remains: Mapped[str | None] = mapped_column(Text)

    entries = relationship(
        "JournalEntry", secondary="entry_locations", back_populates="locations", lazy="selectin"
    )
