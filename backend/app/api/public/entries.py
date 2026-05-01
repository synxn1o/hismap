from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.crud import journal_entry as entry_crud
from app.schemas.journal_entry import JournalEntryDetail, JournalEntryRead

router = APIRouter(prefix="/entries", tags=["entries"])


@router.get("", response_model=list[JournalEntryRead])
async def list_entries(
    dynasty: str | None = None,
    author: str | None = None,
    keyword: str | None = None,
    era: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
):
    return await entry_crud.get_entries(
        db, dynasty=dynasty, author=author, keyword=keyword, era=era, skip=skip, limit=limit
    )


@router.get("/{entry_id}", response_model=JournalEntryDetail)
async def get_entry(entry_id: int, db: AsyncSession = Depends(get_session)):
    entry = await entry_crud.get_entry(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry
