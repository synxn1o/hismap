from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.crud import location as location_crud
from app.schemas.location import LocationCreate, LocationDetail, LocationRead, LocationUpdate

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("", response_model=list[LocationRead])
async def list_locations(
    type: str | None = Query(None, description="地点类型"),
    dynasty: str | None = Query(None, description="朝代"),
    db: AsyncSession = Depends(get_session),
):
    return await location_crud.get_locations(db, location_type=type, dynasty=dynasty)


@router.get("/{location_id}", response_model=LocationDetail)
async def get_location(location_id: int, db: AsyncSession = Depends(get_session)):
    location = await location_crud.get_location(db, location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    related = await location_crud.get_related_locations(db, location_id)
    return LocationDetail(
        **{k: v for k, v in location.__dict__.items() if not k.startswith("_")},
        related_locations=related,
    )
