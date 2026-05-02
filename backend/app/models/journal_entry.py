from sqlalchemy import Column, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class JournalEntry(BaseModel):
    __tablename__ = "journal_entries"

    book_id = Column(Integer, ForeignKey("books.id"), nullable=True)
    title = Column(String(500), nullable=False)
    original_text = Column(Text, nullable=False)
    excerpt_original = Column(Text, nullable=True)
    excerpt_translation = Column(Text, nullable=True)
    summary_chinese = Column(Text, nullable=True)
    summary_english = Column(Text, nullable=True)
    chapter_reference = Column(String(200), nullable=True)
    keywords = Column(JSON, nullable=True)
    keyword_annotations = Column(JSON, nullable=True)
    persons = Column(JSON, nullable=True)
    dates = Column(JSON, nullable=True)
    era_context = Column(Text, nullable=True)
    political_context = Column(Text, nullable=True)
    religious_context = Column(Text, nullable=True)
    social_environment = Column(Text, nullable=True)
    visit_date_approximate = Column(String(100), nullable=True)
    credibility = Column(JSON, nullable=True)
    annotations = Column(JSON, nullable=True)

    book = relationship("Book", back_populates="entries", lazy="selectin")
    locations = relationship(
        "Location", secondary="entry_locations", back_populates="entries", lazy="selectin"
    )
    authors = relationship(
        "Author", secondary="entry_authors", back_populates="entries", lazy="selectin"
    )
