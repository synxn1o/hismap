import pytest


async def _get_admin_token(client) -> str:
    resp = await client.post("/api/admin/login", data={"username": "admin", "password": "admin123"})
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_admin_create_location(client):
    token = await _get_admin_token(client)
    resp = await client.post(
        "/api/admin/locations",
        json={"name": "泉州", "latitude": 24.87, "longitude": 118.67, "location_type": "古城"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "泉州"
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_admin_update_location(client, db_session):
    from app.models.location import Location

    location = Location(name="Old Name", latitude=24.87, longitude=118.67)
    db_session.add(location)
    await db_session.flush()

    token = await _get_admin_token(client)
    resp = await client.put(
        f"/api/admin/locations/{location.id}",
        json={"name": "New Name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
