import pytest

from app.models.book import Book
from app.models.journal_entry import JournalEntry


@pytest.mark.asyncio
async def test_search_by_text(client, db_session):
    book = Book(title="Test Book")
    db_session.add(book)
    await db_session.flush()

    db_session.add(JournalEntry(book_id=book.id, title="泉州见闻", original_text="在这座城市里有香料"))
    db_session.add(JournalEntry(book_id=book.id, title="长安行", original_text="古都繁华"))
    await db_session.flush()

    resp = await client.get("/api/search", params={"q": "香料"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "泉州见闻"


@pytest.mark.asyncio
async def test_search_no_results(client, db_session):
    resp = await client.get("/api/search", params={"q": "不存在的词"})
    assert resp.status_code == 200
    assert resp.json() == []
