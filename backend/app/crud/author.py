from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.author import Author
from app.schemas.author import AuthorCreate, AuthorUpdate


async def get_author(db: AsyncSession, author_id: int) -> Author | None:
    result = await db.execute(
        select(Author).options(selectinload(Author.entries)).where(Author.id == author_id)
    )
    return result.scalar_one_or_none()


async def get_authors(db: AsyncSession, dynasty: str | None = None, skip: int = 0, limit: int = 100) -> list[Author]:
    stmt = select(Author)
    if dynasty:
        stmt = stmt.where(Author.dynasty == dynasty)
    result = await db.execute(stmt.offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_author(db: AsyncSession, data: AuthorCreate) -> Author:
    author = Author(**data.model_dump())
    db.add(author)
    await db.flush()
    await db.refresh(author)
    return author


async def update_author(db: AsyncSession, author_id: int, data: AuthorUpdate) -> Author | None:
    author = await get_author(db, author_id)
    if not author:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(author, field, value)
    await db.flush()
    await db.refresh(author)
    return author
