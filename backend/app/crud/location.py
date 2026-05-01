from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.associations import entry_locations, relation_locations
from app.models.location import Location
from app.schemas.location import LocationCreate, LocationUpdate


async def get_location(db: AsyncSession, location_id: int) -> Location | None:
    result = await db.execute(
        select(Location)
        .options(selectinload(Location.entries))
        .where(Location.id == location_id)
    )
    return result.scalar_one_or_none()


async def get_locations(
    db: AsyncSession,
    location_type: str | None = None,
    dynasty: str | None = None,
    skip: int = 0,
    limit: int = 1000,
) -> list[Location]:
    stmt = select(Location)
    if location_type:
        stmt = stmt.where(Location.location_type == location_type)
    result = await db.execute(stmt.offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_location(db: AsyncSession, data: LocationCreate) -> Location:
    location = Location(**data.model_dump())
    db.add(location)
    await db.flush()
    await db.refresh(location)
    return location


async def update_location(db: AsyncSession, location_id: int, data: LocationUpdate) -> Location | None:
    location = await get_location(db, location_id)
    if not location:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(location, field, value)
    await db.flush()
    await db.refresh(location)
    return location


async def add_location_relation(
    db: AsyncSession, from_id: int, to_id: int, relation_type: str, description: str | None = None
) -> None:
    await db.execute(
        relation_locations.insert().values(
            from_location_id=from_id,
            to_location_id=to_id,
            relation_type=relation_type,
            description=description,
        )
    )
    await db.flush()


async def delete_location_relation(db: AsyncSession, relation_id: int) -> bool:
    result = await db.execute(
        relation_locations.delete().where(relation_locations.c.id == relation_id)
    )
    await db.flush()
    return result.rowcount > 0


async def get_related_locations(db: AsyncSession, location_id: int) -> list[dict]:
    result = await db.execute(
        select(
            relation_locations.c.id,
            relation_locations.c.to_location_id,
            relation_locations.c.relation_type,
            relation_locations.c.description,
            Location.name,
        )
        .join(Location, Location.id == relation_locations.c.to_location_id)
        .where(relation_locations.c.from_location_id == location_id)
    )
    return [
        {
            "id": row.id,
            "to_location_id": row.to_location_id,
            "name": row.name,
            "relation_type": row.relation_type,
            "description": row.description,
        }
        for row in result.all()
    ]
