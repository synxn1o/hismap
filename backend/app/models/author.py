from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Author(BaseModel):
    __tablename__ = "authors"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    dynasty: Mapped[str | None] = mapped_column(String(50))
    birth_year: Mapped[int | None] = mapped_column(Integer)
    death_year: Mapped[int | None] = mapped_column(Integer)
    biography: Mapped[str | None] = mapped_column(Text)

    entries = relationship(
        "JournalEntry", secondary="entry_authors", back_populates="authors", lazy="selectin"
    )
