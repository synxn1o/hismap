import pytest


@pytest.mark.asyncio
async def test_admin_login_success(client):
    resp = await client.post(
        "/api/admin/login",
        data={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_admin_login_wrong_password(client):
    resp = await client.post(
        "/api/admin/login",
        data={"username": "admin", "password": "wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_endpoint_requires_auth(client):
    resp = await client.post(
        "/api/admin/entries",
        json={"title": "test", "original_text": "text"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_endpoint_with_auth(client):
    # Login first
    login_resp = await client.post(
        "/api/admin/login",
        data={"username": "admin", "password": "admin123"},
    )
    token = login_resp.json()["access_token"]

    # Access admin endpoint
    resp = await client.post(
        "/api/admin/entries",
        json={"title": "test", "original_text": "text"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
