import pytest

from app.models.author import Author


@pytest.mark.asyncio
async def test_list_authors(client, db_session):
    db_session.add(Author(name="马可·波罗", dynasty="元"))
    db_session.add(Author(name="伊本·白图泰", dynasty="元"))
    await db_session.flush()

    resp = await client.get("/api/authors")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_list_authors_filter_dynasty(client, db_session):
    db_session.add(Author(name="马可·波罗", dynasty="元"))
    db_session.add(Author(name="玄奘", dynasty="唐"))
    await db_session.flush()

    resp = await client.get("/api/authors", params={"dynasty": "唐"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "玄奘"
