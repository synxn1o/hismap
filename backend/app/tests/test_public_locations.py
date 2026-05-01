import pytest

from app.models.location import Location


@pytest.mark.asyncio
async def test_list_locations_empty(client):
    resp = await client.get("/api/locations")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_locations(client, db_session):
    db_session.add(Location(name="泉州", latitude=24.87, longitude=118.67, location_type="古城"))
    db_session.add(Location(name="长安", latitude=34.26, longitude=108.94, location_type="古城"))
    await db_session.flush()

    resp = await client.get("/api/locations")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_list_locations_filter_type(client, db_session):
    db_session.add(Location(name="泉州", latitude=24.87, longitude=118.67, location_type="古城"))
    db_session.add(Location(name="泰山", latitude=36.25, longitude=117.10, location_type="山川"))
    await db_session.flush()

    resp = await client.get("/api/locations", params={"type": "山川"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "泰山"


@pytest.mark.asyncio
async def test_get_location_not_found(client):
    resp = await client.get("/api/locations/999")
    assert resp.status_code == 404
