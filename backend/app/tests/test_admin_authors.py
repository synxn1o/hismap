import pytest


async def _get_admin_token(client) -> str:
    resp = await client.post("/api/admin/login", data={"username": "admin", "password": "admin123"})
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_admin_create_author(client):
    token = await _get_admin_token(client)
    resp = await client.post(
        "/api/admin/authors",
        json={"name": "马可·波罗", "dynasty": "元", "birth_year": 1254},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "马可·波罗"
    assert data["id"] is not None
