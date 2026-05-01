from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Book(BaseModel):
    __tablename__ = "books"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    author: Mapped[str | None] = mapped_column(String(200))
    dynasty: Mapped[str | None] = mapped_column(String(50))
    era_start: Mapped[int | None] = mapped_column(Integer)
    era_end: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    source_text: Mapped[str | None] = mapped_column(Text)

    entries = relationship("JournalEntry", back_populates="book", lazy="selectin")
