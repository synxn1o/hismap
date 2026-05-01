import pytest

from app.models.book import Book


@pytest.mark.asyncio
async def test_list_books(client, db_session):
    db_session.add(Book(title="马可·波罗游记"))
    await db_session.flush()

    resp = await client.get("/api/books")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_get_book_detail(client, db_session):
    book = Book(title="马可·波罗游记", dynasty="元")
    db_session.add(book)
    await db_session.flush()

    resp = await client.get(f"/api/books/{book.id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "马可·波罗游记"
