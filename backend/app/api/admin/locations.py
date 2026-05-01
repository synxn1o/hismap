from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_session
from app.crud import location as location_crud
from app.schemas.location import LocationCreate, LocationRead, LocationUpdate

router = APIRouter(prefix="/admin/locations", tags=["admin-locations"])


@router.post("", response_model=LocationRead)
async def create_location(
    data: LocationCreate,
    db: AsyncSession = Depends(get_session),
    _admin: dict = Depends(get_current_admin),
):
    return await location_crud.create_location(db, data)


@router.put("/{location_id}", response_model=LocationRead)
async def update_location(
    location_id: int,
    data: LocationUpdate,
    db: AsyncSession = Depends(get_session),
    _admin: dict = Depends(get_current_admin),
):
    location = await location_crud.update_location(db, location_id, data)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location


@router.post("/{location_id}/relations")
async def add_relation(
    location_id: int,
    to_location_id: int,
    relation_type: str,
    description: str | None = None,
    db: AsyncSession = Depends(get_session),
    _admin: dict = Depends(get_current_admin),
):
    await location_crud.add_location_relation(db, location_id, to_location_id, relation_type, description)
    return {"ok": True}


@router.delete("/{location_id}/relations/{relation_id}")
async def delete_relation(
    location_id: int,
    relation_id: int,
    db: AsyncSession = Depends(get_session),
    _admin: dict = Depends(get_current_admin),
):
    deleted = await location_crud.delete_location_relation(db, relation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Relation not found")
    return {"ok": True}
