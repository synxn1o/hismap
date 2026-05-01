from fastapi import APIRouter, Depends
from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.author import Author
from app.models.journal_entry import JournalEntry
from app.models.location import Location
from app.schemas.filter import FilterOptions

router = APIRouter(prefix="/filters", tags=["filters"])


@router.get("", response_model=FilterOptions)
async def get_filters(db: AsyncSession = Depends(get_session)):
    dynasties_result = await db.execute(select(distinct(Author.dynasty)).where(Author.dynasty.isnot(None)))
    authors_result = await db.execute(select(distinct(Author.name)))
    types_result = await db.execute(select(distinct(Location.location_type)).where(Location.location_type.isnot(None)))
    era_result = await db.execute(
        select(distinct(JournalEntry.era_context)).where(JournalEntry.era_context.isnot(None))
    )

    return FilterOptions(
        dynasties=sorted([r[0] for r in dynasties_result.all()]),
        authors=sorted([r[0] for r in authors_result.all()]),
        location_types=sorted([r[0] for r in types_result.all()]),
        era_contexts=sorted([r[0] for r in era_result.all()]),
    )
