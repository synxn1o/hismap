from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_session
from app.crud import journal_entry as entry_crud
from app.schemas.journal_entry import JournalEntryCreate, JournalEntryRead, JournalEntryUpdate

router = APIRouter(prefix="/admin/entries", tags=["admin-entries"])


@router.post("", response_model=JournalEntryRead)
async def create_entry(
    data: JournalEntryCreate,
    db: AsyncSession = Depends(get_session),
    _admin: dict = Depends(get_current_admin),
):
    return await entry_crud.create_entry(db, data)


@router.put("/{entry_id}", response_model=JournalEntryRead)
async def update_entry(
    entry_id: int,
    data: JournalEntryUpdate,
    db: AsyncSession = Depends(get_session),
    _admin: dict = Depends(get_current_admin),
):
    entry = await entry_crud.update_entry(db, entry_id, data)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.delete("/{entry_id}")
async def delete_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_session),
    _admin: dict = Depends(get_current_admin),
):
    deleted = await entry_crud.delete_entry(db, entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"ok": True}
