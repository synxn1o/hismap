from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.crud import journal_entry as entry_crud
from app.schemas.journal_entry import JournalEntryRead

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[JournalEntryRead])
async def search(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_session),
):
    return await entry_crud.search_entries(db, query=q, limit=limit)
