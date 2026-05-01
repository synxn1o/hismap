import pytest

from app.models.author import Author
from app.models.location import Location


@pytest.mark.asyncio
async def test_get_filters(client, db_session):
    db_session.add(Author(name="马可·波罗", dynasty="元"))
    db_session.add(Author(name="玄奘", dynasty="唐"))
    db_session.add(Location(name="泉州", latitude=24.87, longitude=118.67, location_type="古城"))
    await db_session.flush()

    resp = await client.get("/api/filters")
    assert resp.status_code == 200
    data = resp.json()
    assert "元" in data["dynasties"]
    assert "唐" in data["dynasties"]
    assert "古城" in data["location_types"]
