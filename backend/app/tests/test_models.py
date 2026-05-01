import pytest
from sqlalchemy import select

from app.models.book import Book
from app.models.author import Author
from app.models.location import Location
from app.models.journal_entry import JournalEntry
from app.models.associations import entry_locations, entry_authors


@pytest.mark.asyncio
async def test_create_book(db_session):
    book = Book(
        title="马可·波罗游记",
        author="马可·波罗",
        dynasty="元",
        era_start=1271,
        era_end=1295,
        description="威尼斯商人马可·波罗的东方游记",
        source_text="The Travels of Marco Polo",
    )
    db_session.add(book)
    await db_session.flush()

    result = await db_session.execute(select(Book).where(Book.title == "马可·波罗游记"))
    fetched = result.scalar_one()
    assert fetched.id is not None
    assert fetched.title == "马可·波罗游记"
    assert fetched.dynasty == "元"
    assert fetched.era_start == 1271


@pytest.mark.asyncio
async def test_create_author(db_session):
    author = Author(
        name="马可·波罗",
        dynasty="元",
        birth_year=1254,
        death_year=1324,
        biography="威尼斯商人和探险家",
    )
    db_session.add(author)
    await db_session.flush()

    result = await db_session.execute(select(Author).where(Author.name == "马可·波罗"))
    fetched = result.scalar_one()
    assert fetched.id is not None
    assert fetched.birth_year == 1254


@pytest.mark.asyncio
async def test_create_location(db_session):
    location = Location(
        name="泉州",
        modern_name="泉州",
        ancient_name="刺桐城",
        latitude=24.8741,
        longitude=118.6759,
        location_type="古城",
        ancient_region="海上丝绸之路·福建",
        one_line_summary="马可·波罗描述的东方大港，当时世界最大的贸易中心之一",
    )
    db_session.add(location)
    await db_session.flush()

    result = await db_session.execute(select(Location).where(Location.name == "泉州"))
    fetched = result.scalar_one()
    assert fetched.id is not None
    assert fetched.latitude == 24.8741
    assert fetched.longitude == 118.6759
    assert fetched.location_type == "古城"
    assert fetched.ancient_region == "海上丝绸之路·福建"


@pytest.mark.asyncio
async def test_create_journal_entry(db_session):
    book = Book(title="Test Book", author="Test Author")
    db_session.add(book)
    await db_session.flush()

    entry = JournalEntry(
        book_id=book.id,
        title="泉州见闻",
        original_text="在这座城市里，你可以找到所有你能想到的香料和宝石",
        modern_translation="在这座城市中，能找到各种香料和宝石",
        english_translation="In this city, you can find all the spices and gems...",
        chapter_reference="第2卷第38章",
        keywords=["香料", "宝石", "港口", "贸易"],
        era_context="地理大发现",
        visit_date_approximate="1292",
    )
    db_session.add(entry)
    await db_session.flush()

    result = await db_session.execute(select(JournalEntry).where(JournalEntry.title == "泉州见闻"))
    fetched = result.scalar_one()
    assert fetched.id is not None
    assert fetched.book_id == book.id
    assert fetched.keywords == ["香料", "宝石", "港口", "贸易"]


@pytest.mark.asyncio
async def test_entry_location_association(db_session):
    book = Book(title="Test Book")
    location = Location(name="泉州", latitude=24.87, longitude=118.67)
    entry = JournalEntry(book_id=book.id, title="Test Entry", original_text="text")
    db_session.add_all([book, location])
    await db_session.flush()

    entry.book_id = book.id
    db_session.add(entry)
    await db_session.flush()

    # Insert association
    await db_session.execute(
        entry_locations.insert().values(
            entry_id=entry.id, location_id=location.id, location_order=1
        )
    )
    await db_session.flush()

    result = await db_session.execute(
        select(entry_locations).where(entry_locations.c.entry_id == entry.id)
    )
    row = result.one()
    assert row.location_id == location.id
    assert row.location_order == 1
