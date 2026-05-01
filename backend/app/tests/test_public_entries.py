import pytest

from app.models.book import Book
from app.models.journal_entry import JournalEntry


@pytest.mark.asyncio
async def test_list_entries_empty(client):
    resp = await client.get("/api/entries")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_entries(client, db_session):
    book = Book(title="Test Book")
    db_session.add(book)
    await db_session.flush()

    db_session.add(JournalEntry(book_id=book.id, title="泉州见闻", original_text="港口描述"))
    db_session.add(JournalEntry(book_id=book.id, title="长安行", original_text="古都描写"))
    await db_session.flush()

    resp = await client.get("/api/entries")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_entry(client, db_session):
    book = Book(title="Test Book")
    db_session.add(book)
    await db_session.flush()

    entry = JournalEntry(book_id=book.id, title="泉州见闻", original_text="在这座城市里...")
    db_session.add(entry)
    await db_session.flush()

    resp = await client.get(f"/api/entries/{entry.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "泉州见闻"
