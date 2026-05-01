from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.book import Book
from app.schemas.book import BookCreate, BookUpdate


async def get_book(db: AsyncSession, book_id: int) -> Book | None:
    result = await db.execute(
        select(Book).options(selectinload(Book.entries)).where(Book.id == book_id)
    )
    return result.scalar_one_or_none()


async def get_books(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Book]:
    result = await db.execute(select(Book).offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_book(db: AsyncSession, data: BookCreate) -> Book:
    book = Book(**data.model_dump())
    db.add(book)
    await db.flush()
    await db.refresh(book)
    return book


async def update_book(db: AsyncSession, book_id: int, data: BookUpdate) -> Book | None:
    book = await get_book(db, book_id)
    if not book:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(book, field, value)
    await db.flush()
    await db.refresh(book)
    return book


async def delete_book(db: AsyncSession, book_id: int) -> bool:
    book = await db.get(Book, book_id)
    if not book:
        return False
    await db.delete(book)
    await db.flush()
    return True
