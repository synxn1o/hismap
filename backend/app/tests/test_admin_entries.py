import pytest


async def _get_admin_token(client) -> str:
    resp = await client.post("/api/admin/login", data={"username": "admin", "password": "admin123"})
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_admin_create_entry(client):
    token = await _get_admin_token(client)
    resp = await client.post(
        "/api/admin/entries",
        json={"title": "泉州见闻", "original_text": "在这座城市里..."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "泉州见闻"
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_admin_update_entry(client, db_session):
    from app.models.book import Book
    from app.models.journal_entry import JournalEntry

    book = Book(title="Test Book")
    db_session.add(book)
    await db_session.flush()
    entry = JournalEntry(book_id=book.id, title="Old Title", original_text="text")
    db_session.add(entry)
    await db_session.flush()

    token = await _get_admin_token(client)
    resp = await client.put(
        f"/api/admin/entries/{entry.id}",
        json={"title": "New Title"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New Title"


@pytest.mark.asyncio
async def test_admin_delete_entry(client, db_session):
    from app.models.book import Book
    from app.models.journal_entry import JournalEntry

    book = Book(title="Test Book")
    db_session.add(book)
    await db_session.flush()
    entry = JournalEntry(book_id=book.id, title="To Delete", original_text="text")
    db_session.add(entry)
    await db_session.flush()

    token = await _get_admin_token(client)
    resp = await client.delete(
        f"/api/admin/entries/{entry.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
