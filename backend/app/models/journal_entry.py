from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class JournalEntry(BaseModel):
    __tablename__ = "journal_entries"

    book_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("books.id"))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    modern_translation: Mapped[str | None] = mapped_column(Text)
    english_translation: Mapped[str | None] = mapped_column(Text)
    chapter_reference: Mapped[str | None] = mapped_column(String(200))
    keywords: Mapped[list | None] = mapped_column(JSON)
    keyword_annotations: Mapped[dict | None] = mapped_column(JSON)
    era_context: Mapped[str | None] = mapped_column(String(200))
    political_context: Mapped[str | None] = mapped_column(Text)
    religious_context: Mapped[str | None] = mapped_column(Text)
    social_environment: Mapped[str | None] = mapped_column(Text)
    visit_date_approximate: Mapped[str | None] = mapped_column(String(100))

    book = relationship("Book", back_populates="entries", lazy="selectin")
    locations = relationship(
        "Location", secondary="entry_locations", back_populates="entries", lazy="selectin"
    )
    authors = relationship(
        "Author", secondary="entry_authors", back_populates="entries", lazy="selectin"
    )
