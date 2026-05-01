from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.associations import entry_authors, entry_locations
from app.models.journal_entry import JournalEntry
from app.schemas.journal_entry import JournalEntryCreate, JournalEntryUpdate


def _base_query():
    return select(JournalEntry).options(
        selectinload(JournalEntry.locations),
        selectinload(JournalEntry.authors),
    )


async def get_entry(db: AsyncSession, entry_id: int) -> JournalEntry | None:
    result = await db.execute(_base_query().where(JournalEntry.id == entry_id))
    return result.scalar_one_or_none()


async def get_entries(
    db: AsyncSession,
    dynasty: str | None = None,
    author: str | None = None,
    keyword: str | None = None,
    era: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[JournalEntry]:
    stmt = _base_query()
    if era:
        stmt = stmt.where(JournalEntry.era_context == era)
    if keyword:
        stmt = stmt.where(
            or_(
                JournalEntry.original_text.ilike(f"%{keyword}%"),
                JournalEntry.modern_translation.ilike(f"%{keyword}%"),
                JournalEntry.title.ilike(f"%{keyword}%"),
            )
        )
    result = await db.execute(stmt.offset(skip).limit(limit))
    return list(result.scalars().unique().all())


async def create_entry(db: AsyncSession, data: JournalEntryCreate) -> JournalEntry:
    entry_data = data.model_dump(exclude={"location_ids", "author_ids"})
    entry = JournalEntry(**entry_data)
    db.add(entry)
    await db.flush()

    for order, loc_id in enumerate(data.location_ids):
        await db.execute(
            entry_locations.insert().values(entry_id=entry.id, location_id=loc_id, location_order=order)
        )
    for auth_id in data.author_ids:
        await db.execute(entry_authors.insert().values(entry_id=entry.id, author_id=auth_id))

    await db.flush()
    await db.refresh(entry, ["locations", "authors"])
    return entry


async def update_entry(db: AsyncSession, entry_id: int, data: JournalEntryUpdate) -> JournalEntry | None:
    entry = await get_entry(db, entry_id)
    if not entry:
        return None

    update_data = data.model_dump(exclude_unset=True, exclude={"location_ids", "author_ids"})
    for field, value in update_data.items():
        setattr(entry, field, value)

    if data.location_ids is not None:
        await db.execute(entry_locations.delete().where(entry_locations.c.entry_id == entry_id))
        for order, loc_id in enumerate(data.location_ids):
            await db.execute(
                entry_locations.insert().values(entry_id=entry.id, location_id=loc_id, location_order=order)
            )

    if data.author_ids is not None:
        await db.execute(entry_authors.delete().where(entry_authors.c.entry_id == entry_id))
        for auth_id in data.author_ids:
            await db.execute(entry_authors.insert().values(entry_id=entry.id, author_id=auth_id))

    await db.flush()
    await db.refresh(entry, ["locations", "authors"])
    return entry


async def delete_entry(db: AsyncSession, entry_id: int) -> bool:
    entry = await db.get(JournalEntry, entry_id)
    if not entry:
        return False
    await db.delete(entry)
    await db.flush()
    return True


async def search_entries(db: AsyncSession, query: str, limit: int = 50) -> list[JournalEntry]:
    stmt = (
        _base_query()
        .where(
            or_(
                JournalEntry.original_text.ilike(f"%{query}%"),
                JournalEntry.modern_translation.ilike(f"%{query}%"),
                JournalEntry.english_translation.ilike(f"%{query}%"),
                JournalEntry.title.ilike(f"%{query}%"),
                JournalEntry.era_context.ilike(f"%{query}%"),
                JournalEntry.political_context.ilike(f"%{query}%"),
            )
        )
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())
