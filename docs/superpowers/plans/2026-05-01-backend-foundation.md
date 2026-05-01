# HiSMap Backend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the FastAPI backend with PostgreSQL/PostGIS database, all data models, public API, admin API with JWT auth, and full-text search — fully functional and testable end-to-end.

**Architecture:** FastAPI app with SQLAlchemy 2.0 async ORM, Alembic migrations, Pydantic v2 schemas. Public API serves the frontend (no auth). Admin API uses JWT authentication. PostGIS handles geospatial queries. The backend serves both the frontend SPA and the future admin UI.

**Tech Stack:** conda environment `hismap`: Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2, python-jose (JWT), psycopg2 (PostGIS), pytest, httpx (test client)

---

## File Structure

```
backend/
├── pyproject.toml
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 001_initial.py
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app factory, CORS, routers
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Settings via pydantic-settings
│   │   ├── database.py            # async engine, session factory
│   │   └── security.py            # JWT encode/decode, password hashing
│   ├── models/
│   │   ├── __init__.py            # re-export all models
│   │   ├── base.py                # Base model with id, timestamps
│   │   ├── book.py
│   │   ├── author.py
│   │   ├── location.py
│   │   ├── journal_entry.py
│   │   └── associations.py        # entry_locations, entry_authors, relation_locations
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── book.py
│   │   ├── author.py
│   │   ├── location.py
│   │   ├── journal_entry.py
│   │   ├── search.py
│   │   └── filter.py
│   ├── crud/
│   │   ├── __init__.py
│   │   ├── book.py
│   │   ├── author.py
│   │   ├── location.py
│   │   └── journal_entry.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                # get_db, get_current_user dependencies
│   │   ├── public/
│   │   │   ├── __init__.py
│   │   │   ├── locations.py
│   │   │   ├── entries.py
│   │   │   ├── authors.py
│   │   │   ├── books.py
│   │   │   ├── search.py
│   │   │   └── filters.py
│   │   └── admin/
│   │       ├── __init__.py
│   │       ├── auth.py            # POST /api/admin/login
│   │       ├── entries.py
│   │       ├── locations.py
│   │       ├── authors.py
│   │       └── books.py
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py            # fixtures: test DB, test client, auth helpers
│       ├── test_models.py
│       ├── test_public_locations.py
│       ├── test_public_entries.py
│       ├── test_public_authors.py
│       ├── test_public_books.py
│       ├── test_search.py
│       ├── test_filters.py
│       ├── test_admin_auth.py
│       ├── test_admin_entries.py
│       ├── test_admin_locations.py
│       └── test_admin_authors.py
└── requirements.txt
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/database.py`
- Create: `backend/app/main.py`
- Create: `backend/app/tests/__init__.py`
- Create: `backend/app/tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
# backend/pyproject.toml
[project]
name = "hismap-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.30.0",
    "sqlalchemy[asyncio]>=2.0.30",
    "asyncpg>=0.29.0",
    "psycopg2-binary>=2.9.9",
    "alembic>=1.13.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.3.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
    "aiosqlite>=0.20.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["app/tests"]
```

- [ ] **Step 2: Create requirements.txt**

```
# backend/requirements.txt
fastapi>=0.111.0
uvicorn[standard]>=0.30.0
sqlalchemy[asyncio]>=2.0.30
asyncpg>=0.29.0
psycopg2-binary>=2.9.9
alembic>=1.13.0
pydantic>=2.7.0
pydantic-settings>=2.3.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.9
```

- [ ] **Step 3: Create config.py**

```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "HiSMap"
    API_V1_PREFIX: str = "/api"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://hismap:hismap@localhost:5432/hismap"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://hismap:hismap@localhost:5432/hismap"

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = {"env_prefix": "HISMAP_", "env_file": ".env"}


settings = Settings()
```

- [ ] **Step 4: Create database.py**

```python
# backend/app/core/database.py
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

- [ ] **Step 5: Create main.py**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.PROJECT_NAME)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 6: Create test fixtures**

```python
# backend/app/tests/conftest.py
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.main import create_app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(db_engine):
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
```

- [ ] **Step 7: Create __init__.py files**

Create empty files:
- `backend/app/__init__.py`
- `backend/app/core/__init__.py`
- `backend/app/tests/__init__.py`

- [ ] **Step 8: Run health check test**

Create `backend/app/tests/test_health.py`:

```python
# backend/app/tests/test_health.py
import pytest


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

Run: `cd backend && pip install -e ".[dev]" && pytest app/tests/test_health.py -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add backend/
git commit -m "feat: scaffold FastAPI project with config, database, and test fixtures"
```

---

## Task 2: SQLAlchemy Models — Base, Book, Author

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/base.py`
- Create: `backend/app/models/book.py`
- Create: `backend/app/models/author.py`
- Create: `backend/app/tests/test_models.py`

- [ ] **Step 1: Write failing test for Book model**

```python
# backend/app/tests/test_models.py
import pytest
from sqlalchemy import select

from app.models.book import Book
from app.models.author import Author


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest app/tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models'`

- [ ] **Step 3: Create base model**

```python
# backend/app/models/base.py
from datetime import datetime

from sqlalchemy import DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class BaseModel(Base, TimestampMixin):
    __abstract__ = True
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
```

- [ ] **Step 4: Create Book model**

```python
# backend/app/models/book.py
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Book(BaseModel):
    __tablename__ = "books"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    author: Mapped[str | None] = mapped_column(String(200))
    dynasty: Mapped[str | None] = mapped_column(String(50))
    era_start: Mapped[int | None] = mapped_column(Integer)
    era_end: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    source_text: Mapped[str | None] = mapped_column(Text)
```

- [ ] **Step 5: Create Author model**

```python
# backend/app/models/author.py
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Author(BaseModel):
    __tablename__ = "authors"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    dynasty: Mapped[str | None] = mapped_column(String(50))
    birth_year: Mapped[int | None] = mapped_column(Integer)
    death_year: Mapped[int | None] = mapped_column(Integer)
    biography: Mapped[str | None] = mapped_column(Text)
```

- [ ] **Step 6: Create models __init__.py**

```python
# backend/app/models/__init__.py
from app.models.author import Author
from app.models.book import Book

__all__ = ["Author", "Book"]
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd backend && pytest app/tests/test_models.py -v`
Expected: PASS (2 tests)

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/ backend/app/tests/test_models.py
git commit -m "feat: add Book and Author SQLAlchemy models"
```

---

## Task 3: Location Model with PostGIS

**Files:**
- Create: `backend/app/models/location.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/tests/test_models.py`

- [ ] **Step 1: Write failing test for Location model**

Append to `backend/app/tests/test_models.py`:

```python
from app.models.location import Location


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest app/tests/test_models.py::test_create_location -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models.location'`

- [ ] **Step 3: Create Location model**

```python
# backend/app/models/location.py
from sqlalchemy import Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Location(BaseModel):
    __tablename__ = "locations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    modern_name: Mapped[str | None] = mapped_column(String(200))
    ancient_name: Mapped[str | None] = mapped_column(String(200))
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    # PostGIS geometry — stored as raw SQL in migrations, not in model
    location_type: Mapped[str | None] = mapped_column(String(50))
    ancient_region: Mapped[str | None] = mapped_column(String(200))
    one_line_summary: Mapped[str | None] = mapped_column(Text)
    location_rationale: Mapped[str | None] = mapped_column(Text)
    academic_disputes: Mapped[str | None] = mapped_column(Text)
    credibility_notes: Mapped[str | None] = mapped_column(Text)
    today_remains: Mapped[str | None] = mapped_column(Text)
```

- [ ] **Step 4: Update models __init__.py**

```python
# backend/app/models/__init__.py
from app.models.author import Author
from app.models.book import Book
from app.models.location import Location

__all__ = ["Author", "Book", "Location"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && pytest app/tests/test_models.py::test_create_location -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/location.py backend/app/models/__init__.py backend/app/tests/test_models.py
git commit -m "feat: add Location model with historical context fields"
```

---

## Task 4: JournalEntry Model and Association Tables

**Files:**
- Create: `backend/app/models/journal_entry.py`
- Create: `backend/app/models/associations.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/tests/test_models.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/app/tests/test_models.py`:

```python
from app.models.journal_entry import JournalEntry
from app.models.associations import entry_locations, entry_authors


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest app/tests/test_models.py::test_create_journal_entry -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create JournalEntry model**

```python
# backend/app/models/journal_entry.py
from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class JournalEntry(BaseModel):
    __tablename__ = "journal_entries"

    book_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("books.id"))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    modern_translation: Mapped[str | None] = mapped_column(Text)
    english_translation: Mapped[str | None] = mapped_column(Text)
    chapter_reference: Mapped[str | None] = mapped_column(String(200))
    keywords: Mapped[list | None] = mapped_column(JSON)
    keyword_annotations: Mapped[dict | None] = mapped_column(JSON)
    era_context: Mapped[str | None] = mapped_column(String(200))
    political_context: Mapped[str | None] = mapped_column(Text)
    religious_context: Mapped[str | None] = mapped_column(Text)
    social_environment: Mapped[str | None] = mapped_column(Text)
    visit_date_approximate: Mapped[str | None] = mapped_column(String(100))
```

- [ ] **Step 4: Create association tables**

```python
# backend/app/models/associations.py
from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text

from app.core.database import Base

entry_locations = Table(
    "entry_locations",
    Base.metadata,
    Column("entry_id", Integer, ForeignKey("journal_entries.id", ondelete="CASCADE"), primary_key=True),
    Column("location_id", Integer, ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True),
    Column("location_order", Integer, nullable=False, default=0),
)

entry_authors = Table(
    "entry_authors",
    Base.metadata,
    Column("entry_id", Integer, ForeignKey("journal_entries.id", ondelete="CASCADE"), primary_key=True),
    Column("author_id", Integer, ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True),
)

relation_locations = Table(
    "relation_locations",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("from_location_id", Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False),
    Column("to_location_id", Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False),
    Column("relation_type", String(100), nullable=False),
    Column("description", Text),
)
```

- [ ] **Step 5: Update models __init__.py**

```python
# backend/app/models/__init__.py
from app.models.associations import entry_authors, entry_locations, relation_locations
from app.models.author import Author
from app.models.book import Book
from app.models.journal_entry import JournalEntry
from app.models.location import Location

__all__ = [
    "Author",
    "Book",
    "JournalEntry",
    "Location",
    "entry_authors",
    "entry_locations",
    "relation_locations",
]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && pytest app/tests/test_models.py -v`
Expected: PASS (all tests)

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/
git commit -m "feat: add JournalEntry model and association tables"
```

---

## Task 5: Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/book.py`
- Create: `backend/app/schemas/author.py`
- Create: `backend/app/schemas/location.py`
- Create: `backend/app/schemas/journal_entry.py`
- Create: `backend/app/schemas/search.py`
- Create: `backend/app/schemas/filter.py`

- [ ] **Step 1: Create Book schemas**

```python
# backend/app/schemas/book.py
from pydantic import BaseModel


class BookBase(BaseModel):
    title: str
    author: str | None = None
    dynasty: str | None = None
    era_start: int | None = None
    era_end: int | None = None
    description: str | None = None
    source_text: str | None = None


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: str | None = None
    author: str | None = None
    dynasty: str | None = None
    era_start: int | None = None
    era_end: int | None = None
    description: str | None = None
    source_text: str | None = None


class BookRead(BookBase):
    id: int

    model_config = {"from_attributes": True}


class BookDetail(BookRead):
    entries: list["JournalEntryRead"] = []

    model_config = {"from_attributes": True}


from app.schemas.journal_entry import JournalEntryRead  # noqa: E402

BookDetail.model_rebuild()
```

- [ ] **Step 2: Create Author schemas**

```python
# backend/app/schemas/author.py
from pydantic import BaseModel


class AuthorBase(BaseModel):
    name: str
    dynasty: str | None = None
    birth_year: int | None = None
    death_year: int | None = None
    biography: str | None = None


class AuthorCreate(AuthorBase):
    pass


class AuthorUpdate(BaseModel):
    name: str | None = None
    dynasty: str | None = None
    birth_year: int | None = None
    death_year: int | None = None
    biography: str | None = None


class AuthorRead(AuthorBase):
    id: int

    model_config = {"from_attributes": True}


class AuthorDetail(AuthorRead):
    entries: list["JournalEntryRead"] = []

    model_config = {"from_attributes": True}


from app.schemas.journal_entry import JournalEntryRead  # noqa: E402

AuthorDetail.model_rebuild()
```

- [ ] **Step 3: Create Location schemas**

```python
# backend/app/schemas/location.py
from pydantic import BaseModel


class RelatedLocation(BaseModel):
    id: int
    name: str
    relation_type: str
    description: str | None = None


class LocationBase(BaseModel):
    name: str
    modern_name: str | None = None
    ancient_name: str | None = None
    latitude: float
    longitude: float
    location_type: str | None = None
    ancient_region: str | None = None
    one_line_summary: str | None = None
    location_rationale: str | None = None
    academic_disputes: str | None = None
    credibility_notes: str | None = None
    today_remains: str | None = None


class LocationCreate(LocationBase):
    pass


class LocationUpdate(BaseModel):
    name: str | None = None
    modern_name: str | None = None
    ancient_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_type: str | None = None
    ancient_region: str | None = None
    one_line_summary: str | None = None
    location_rationale: str | None = None
    academic_disputes: str | None = None
    credibility_notes: str | None = None
    today_remains: str | None = None


class LocationRead(LocationBase):
    id: int

    model_config = {"from_attributes": True}


class LocationDetail(LocationRead):
    entries: list["JournalEntryRead"] = []
    related_locations: list[RelatedLocation] = []

    model_config = {"from_attributes": True}


from app.schemas.journal_entry import JournalEntryRead  # noqa: E402

LocationDetail.model_rebuild()
```

- [ ] **Step 4: Create JournalEntry schemas**

```python
# backend/app/schemas/journal_entry.py
from pydantic import BaseModel


class JournalEntryBase(BaseModel):
    book_id: int | None = None
    title: str
    original_text: str
    modern_translation: str | None = None
    english_translation: str | None = None
    chapter_reference: str | None = None
    keywords: list[str] | None = None
    keyword_annotations: dict | None = None
    era_context: str | None = None
    political_context: str | None = None
    religious_context: str | None = None
    social_environment: str | None = None
    visit_date_approximate: str | None = None


class JournalEntryCreate(JournalEntryBase):
    location_ids: list[int] = []
    author_ids: list[int] = []


class JournalEntryUpdate(BaseModel):
    title: str | None = None
    original_text: str | None = None
    modern_translation: str | None = None
    english_translation: str | None = None
    chapter_reference: str | None = None
    keywords: list[str] | None = None
    keyword_annotations: dict | None = None
    era_context: str | None = None
    political_context: str | None = None
    religious_context: str | None = None
    social_environment: str | None = None
    visit_date_approximate: str | None = None
    location_ids: list[int] | None = None
    author_ids: list[int] | None = None


class LocationBrief(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float

    model_config = {"from_attributes": True}


class AuthorBrief(BaseModel):
    id: int
    name: str
    dynasty: str | None = None

    model_config = {"from_attributes": True}


class BookBrief(BaseModel):
    id: int
    title: str

    model_config = {"from_attributes": True}


class JournalEntryRead(JournalEntryBase):
    id: int
    locations: list[LocationBrief] = []
    authors: list[AuthorBrief] = []

    model_config = {"from_attributes": True}


class JournalEntryDetail(JournalEntryRead):
    book: BookBrief | None = None

    model_config = {"from_attributes": True}
```

- [ ] **Step 5: Create Search and Filter schemas**

```python
# backend/app/schemas/search.py
from pydantic import BaseModel


class SearchResult(BaseModel):
    entries: list["JournalEntryRead"]
    total: int


from app.schemas.journal_entry import JournalEntryRead  # noqa: E402

SearchResult.model_rebuild()
```

```python
# backend/app/schemas/filter.py
from pydantic import BaseModel


class FilterOptions(BaseModel):
    dynasties: list[str]
    authors: list[str]
    location_types: list[str]
    era_contexts: list[str]
```

- [ ] **Step 6: Create schemas __init__.py**

```python
# backend/app/schemas/__init__.py
```

(Empty — imports are done where needed.)

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/
git commit -m "feat: add Pydantic v2 schemas for all entities"
```

---

## Task 6: CRUD Layer

**Files:**
- Create: `backend/app/crud/__init__.py`
- Create: `backend/app/crud/book.py`
- Create: `backend/app/crud/author.py`
- Create: `backend/app/crud/location.py`
- Create: `backend/app/crud/journal_entry.py`

- [ ] **Step 1: Create Book CRUD**

```python
# backend/app/crud/book.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.book import Book
from app.schemas.book import BookCreate, BookUpdate


async def get_book(db: AsyncSession, book_id: int) -> Book | None:
    result = await db.execute(
        select(Book).options(selectinload(Book.entries)).where(Book.id == book_id)
    )
    return result.scalar_one_or_none()


async def get_books(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Book]:
    result = await db.execute(select(Book).offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_book(db: AsyncSession, data: BookCreate) -> Book:
    book = Book(**data.model_dump())
    db.add(book)
    await db.flush()
    await db.refresh(book)
    return book


async def update_book(db: AsyncSession, book_id: int, data: BookUpdate) -> Book | None:
    book = await get_book(db, book_id)
    if not book:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(book, field, value)
    await db.flush()
    await db.refresh(book)
    return book


async def delete_book(db: AsyncSession, book_id: int) -> bool:
    book = await db.get(Book, book_id)
    if not book:
        return False
    await db.delete(book)
    await db.flush()
    return True
```

- [ ] **Step 2: Create Author CRUD**

```python
# backend/app/crud/author.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.author import Author
from app.schemas.author import AuthorCreate, AuthorUpdate


async def get_author(db: AsyncSession, author_id: int) -> Author | None:
    result = await db.execute(
        select(Author).options(selectinload(Author.entries)).where(Author.id == author_id)
    )
    return result.scalar_one_or_none()


async def get_authors(db: AsyncSession, dynasty: str | None = None, skip: int = 0, limit: int = 100) -> list[Author]:
    stmt = select(Author)
    if dynasty:
        stmt = stmt.where(Author.dynasty == dynasty)
    result = await db.execute(stmt.offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_author(db: AsyncSession, data: AuthorCreate) -> Author:
    author = Author(**data.model_dump())
    db.add(author)
    await db.flush()
    await db.refresh(author)
    return author


async def update_author(db: AsyncSession, author_id: int, data: AuthorUpdate) -> Author | None:
    author = await get_author(db, author_id)
    if not author:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(author, field, value)
    await db.flush()
    await db.refresh(author)
    return author
```

- [ ] **Step 3: Create Location CRUD**

```python
# backend/app/crud/location.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.associations import entry_locations, relation_locations
from app.models.location import Location
from app.schemas.location import LocationCreate, LocationUpdate


async def get_location(db: AsyncSession, location_id: int) -> Location | None:
    result = await db.execute(
        select(Location)
        .options(selectinload(Location.entries))
        .where(Location.id == location_id)
    )
    return result.scalar_one_or_none()


async def get_locations(
    db: AsyncSession,
    location_type: str | None = None,
    dynasty: str | None = None,
    skip: int = 0,
    limit: int = 1000,
) -> list[Location]:
    stmt = select(Location)
    if location_type:
        stmt = stmt.where(Location.location_type == location_type)
    result = await db.execute(stmt.offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_location(db: AsyncSession, data: LocationCreate) -> Location:
    location = Location(**data.model_dump())
    db.add(location)
    await db.flush()
    await db.refresh(location)
    return location


async def update_location(db: AsyncSession, location_id: int, data: LocationUpdate) -> Location | None:
    location = await get_location(db, location_id)
    if not location:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(location, field, value)
    await db.flush()
    await db.refresh(location)
    return location


async def add_location_relation(
    db: AsyncSession, from_id: int, to_id: int, relation_type: str, description: str | None = None
) -> None:
    await db.execute(
        relation_locations.insert().values(
            from_location_id=from_id,
            to_location_id=to_id,
            relation_type=relation_type,
            description=description,
        )
    )
    await db.flush()


async def delete_location_relation(db: AsyncSession, relation_id: int) -> bool:
    result = await db.execute(
        relation_locations.delete().where(relation_locations.c.id == relation_id)
    )
    await db.flush()
    return result.rowcount > 0


async def get_related_locations(db: AsyncSession, location_id: int) -> list[dict]:
    result = await db.execute(
        select(
            relation_locations.c.id,
            relation_locations.c.to_location_id,
            relation_locations.c.relation_type,
            relation_locations.c.description,
            Location.name,
        )
        .join(Location, Location.id == relation_locations.c.to_location_id)
        .where(relation_locations.c.from_location_id == location_id)
    )
    return [
        {
            "id": row.id,
            "to_location_id": row.to_location_id,
            "name": row.name,
            "relation_type": row.relation_type,
            "description": row.description,
        }
        for row in result.all()
    ]
```

- [ ] **Step 4: Create JournalEntry CRUD**

```python
# backend/app/crud/journal_entry.py
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.associations import entry_authors, entry_locations
from app.models.journal_entry import JournalEntry
from app.schemas.journal_entry import JournalEntryCreate, JournalEntryUpdate


def _base_query():
    return select(JournalEntry).options(
        selectinload(JournalEntry.locations),
        selectinload(JournalEntry.authors),
    )


async def get_entry(db: AsyncSession, entry_id: int) -> JournalEntry | None:
    result = await db.execute(_base_query().where(JournalEntry.id == entry_id))
    return result.scalar_one_or_none()


async def get_entries(
    db: AsyncSession,
    dynasty: str | None = None,
    author: str | None = None,
    keyword: str | None = None,
    era: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[JournalEntry]:
    stmt = _base_query()
    if era:
        stmt = stmt.where(JournalEntry.era_context == era)
    if keyword:
        stmt = stmt.where(
            or_(
                JournalEntry.original_text.ilike(f"%{keyword}%"),
                JournalEntry.modern_translation.ilike(f"%{keyword}%"),
                JournalEntry.title.ilike(f"%{keyword}%"),
            )
        )
    result = await db.execute(stmt.offset(skip).limit(limit))
    return list(result.scalars().unique().all())


async def create_entry(db: AsyncSession, data: JournalEntryCreate) -> JournalEntry:
    entry_data = data.model_dump(exclude={"location_ids", "author_ids"})
    entry = JournalEntry(**entry_data)
    db.add(entry)
    await db.flush()

    for order, loc_id in enumerate(data.location_ids):
        await db.execute(
            entry_locations.insert().values(entry_id=entry.id, location_id=loc_id, location_order=order)
        )
    for auth_id in data.author_ids:
        await db.execute(entry_authors.insert().values(entry_id=entry.id, author_id=auth_id))

    await db.flush()
    await db.refresh(entry, ["locations", "authors"])
    return entry


async def update_entry(db: AsyncSession, entry_id: int, data: JournalEntryUpdate) -> JournalEntry | None:
    entry = await get_entry(db, entry_id)
    if not entry:
        return None

    update_data = data.model_dump(exclude_unset=True, exclude={"location_ids", "author_ids"})
    for field, value in update_data.items():
        setattr(entry, field, value)

    if data.location_ids is not None:
        await db.execute(entry_locations.delete().where(entry_locations.c.entry_id == entry_id))
        for order, loc_id in enumerate(data.location_ids):
            await db.execute(
                entry_locations.insert().values(entry_id=entry.id, location_id=loc_id, location_order=order)
            )

    if data.author_ids is not None:
        await db.execute(entry_authors.delete().where(entry_authors.c.entry_id == entry_id))
        for auth_id in data.author_ids:
            await db.execute(entry_authors.insert().values(entry_id=entry.id, author_id=auth_id))

    await db.flush()
    await db.refresh(entry, ["locations", "authors"])
    return entry


async def delete_entry(db: AsyncSession, entry_id: int) -> bool:
    entry = await db.get(JournalEntry, entry_id)
    if not entry:
        return False
    await db.delete(entry)
    await db.flush()
    return True


async def search_entries(db: AsyncSession, query: str, limit: int = 50) -> list[JournalEntry]:
    stmt = (
        _base_query()
        .where(
            or_(
                JournalEntry.original_text.ilike(f"%{query}%"),
                JournalEntry.modern_translation.ilike(f"%{query}%"),
                JournalEntry.english_translation.ilike(f"%{query}%"),
                JournalEntry.title.ilike(f"%{query}%"),
                JournalEntry.era_context.ilike(f"%{query}%"),
                JournalEntry.political_context.ilike(f"%{query}%"),
            )
        )
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())
```

- [ ] **Step 5: Create crud __init__.py**

```python
# backend/app/crud/__init__.py
```

(Empty.)

- [ ] **Step 6: Commit**

```bash
git add backend/app/crud/
git commit -m "feat: add CRUD operations for all entities"
```

---

## Task 7: Public API Endpoints — Locations and Entries

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/app/api/public/__init__.py`
- Create: `backend/app/api/public/locations.py`
- Create: `backend/app/api/public/entries.py`
- Modify: `backend/app/main.py`
- Create: `backend/app/tests/test_public_locations.py`
- Create: `backend/app/tests/test_public_entries.py`

- [ ] **Step 1: Create dependency injection**

```python
# backend/app/api/deps.py
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db():
        yield session
```

- [ ] **Step 2: Create public locations router**

```python
# backend/app/api/public/locations.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.crud import location as location_crud
from app.schemas.location import LocationCreate, LocationDetail, LocationRead, LocationUpdate

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("", response_model=list[LocationRead])
async def list_locations(
    type: str | None = Query(None, description="地点类型"),
    dynasty: str | None = Query(None, description="朝代"),
    db: AsyncSession = Depends(get_session),
):
    return await location_crud.get_locations(db, location_type=type, dynasty=dynasty)


@router.get("/{location_id}", response_model=LocationDetail)
async def get_location(location_id: int, db: AsyncSession = Depends(get_session)):
    location = await location_crud.get_location(db, location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    related = await location_crud.get_related_locations(db, location_id)
    return LocationDetail(
        **{k: v for k, v in location.__dict__.items() if not k.startswith("_")},
        related_locations=related,
    )
```

- [ ] **Step 3: Create public entries router**

```python
# backend/app/api/public/entries.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.crud import journal_entry as entry_crud
from app.schemas.journal_entry import JournalEntryDetail, JournalEntryRead

router = APIRouter(prefix="/entries", tags=["entries"])


@router.get("", response_model=list[JournalEntryRead])
async def list_entries(
    dynasty: str | None = None,
    author: str | None = None,
    keyword: str | None = None,
    era: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
):
    return await entry_crud.get_entries(
        db, dynasty=dynasty, author=author, keyword=keyword, era=era, skip=skip, limit=limit
    )


@router.get("/{entry_id}", response_model=JournalEntryDetail)
async def get_entry(entry_id: int, db: AsyncSession = Depends(get_session)):
    entry = await entry_crud.get_entry(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry
```

- [ ] **Step 4: Wire routers into main.py**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.PROJECT_NAME)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    # Public API
    from app.api.public.entries import router as entries_router
    from app.api.public.locations import router as locations_router

    app.include_router(locations_router, prefix="/api")
    app.include_router(entries_router, prefix="/api")

    return app


app = create_app()
```

- [ ] **Step 5: Write tests for public locations API**

```python
# backend/app/tests/test_public_locations.py
import pytest

from app.models.location import Location


@pytest.mark.asyncio
async def test_list_locations_empty(client):
    resp = await client.get("/api/locations")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_locations(client, db_session):
    db_session.add(Location(name="泉州", latitude=24.87, longitude=118.67, location_type="古城"))
    db_session.add(Location(name="长安", latitude=34.26, longitude=108.94, location_type="古城"))
    await db_session.flush()

    resp = await client.get("/api/locations")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_list_locations_filter_type(client, db_session):
    db_session.add(Location(name="泉州", latitude=24.87, longitude=118.67, location_type="古城"))
    db_session.add(Location(name="泰山", latitude=36.25, longitude=117.10, location_type="山川"))
    await db_session.flush()

    resp = await client.get("/api/locations", params={"type": "山川"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "泰山"


@pytest.mark.asyncio
async def test_get_location_not_found(client):
    resp = await client.get("/api/locations/999")
    assert resp.status_code == 404
```

- [ ] **Step 6: Write tests for public entries API**

```python
# backend/app/tests/test_public_entries.py
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
```

- [ ] **Step 7: Run tests**

Run: `cd backend && pytest app/tests/test_public_locations.py app/tests/test_public_entries.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/api/ backend/app/main.py backend/app/tests/
git commit -m "feat: add public API endpoints for locations and entries"
```

---

## Task 8: Public API — Authors, Books, Search, Filters

**Files:**
- Create: `backend/app/api/public/authors.py`
- Create: `backend/app/api/public/books.py`
- Create: `backend/app/api/public/search.py`
- Create: `backend/app/api/public/filters.py`
- Modify: `backend/app/main.py`
- Create: `backend/app/tests/test_public_authors.py`
- Create: `backend/app/tests/test_public_books.py`
- Create: `backend/app/tests/test_search.py`
- Create: `backend/app/tests/test_filters.py`

- [ ] **Step 1: Create authors router**

```python
# backend/app/api/public/authors.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.crud import author as author_crud
from app.schemas.author import AuthorDetail, AuthorRead

router = APIRouter(prefix="/authors", tags=["authors"])


@router.get("", response_model=list[AuthorRead])
async def list_authors(
    dynasty: str | None = None,
    db: AsyncSession = Depends(get_session),
):
    return await author_crud.get_authors(db, dynasty=dynasty)


@router.get("/{author_id}", response_model=AuthorDetail)
async def get_author(author_id: int, db: AsyncSession = Depends(get_session)):
    author = await author_crud.get_author(db, author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    return author
```

- [ ] **Step 2: Create books router**

```python
# backend/app/api/public/books.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.crud import book as book_crud
from app.schemas.book import BookDetail, BookRead

router = APIRouter(prefix="/books", tags=["books"])


@router.get("", response_model=list[BookRead])
async def list_books(db: AsyncSession = Depends(get_session)):
    return await book_crud.get_books(db)


@router.get("/{book_id}", response_model=BookDetail)
async def get_book(book_id: int, db: AsyncSession = Depends(get_session)):
    book = await book_crud.get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book
```

- [ ] **Step 3: Create search router**

```python
# backend/app/api/public/search.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.crud import journal_entry as entry_crud
from app.schemas.journal_entry import JournalEntryRead

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[JournalEntryRead])
async def search(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_session),
):
    return await entry_crud.search_entries(db, query=q, limit=limit)
```

- [ ] **Step 4: Create filters router**

```python
# backend/app/api/public/filters.py
from fastapi import APIRouter, Depends
from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.author import Author
from app.models.journal_entry import JournalEntry
from app.models.location import Location
from app.schemas.filter import FilterOptions

router = APIRouter(prefix="/filters", tags=["filters"])


@router.get("", response_model=FilterOptions)
async def get_filters(db: AsyncSession = Depends(get_session)):
    dynasties_result = await db.execute(select(distinct(Author.dynasty)).where(Author.dynasty.isnot(None)))
    authors_result = await db.execute(select(distinct(Author.name)))
    types_result = await db.execute(select(distinct(Location.location_type)).where(Location.location_type.isnot(None)))
    era_result = await db.execute(
        select(distinct(JournalEntry.era_context)).where(JournalEntry.era_context.isnot(None))
    )

    return FilterOptions(
        dynasties=sorted([r[0] for r in dynasties_result.all()]),
        authors=sorted([r[0] for r in authors_result.all()]),
        location_types=sorted([r[0] for r in types_result.all()]),
        era_contexts=sorted([r[0] for r in era_result.all()]),
    )
```

- [ ] **Step 5: Wire new routers into main.py**

Add to the `create_app` function in `backend/app/main.py`, after the existing router imports:

```python
    from app.api.public.authors import router as authors_router
    from app.api.public.books import router as books_router
    from app.api.public.filters import router as filters_router
    from app.api.public.search import router as search_router

    app.include_router(authors_router, prefix="/api")
    app.include_router(books_router, prefix="/api")
    app.include_router(search_router, prefix="/api")
    app.include_router(filters_router, prefix="/api")
```

- [ ] **Step 6: Write tests for authors and books**

```python
# backend/app/tests/test_public_authors.py
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
```

```python
# backend/app/tests/test_public_books.py
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
```

- [ ] **Step 7: Write tests for search and filters**

```python
# backend/app/tests/test_search.py
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
```

```python
# backend/app/tests/test_filters.py
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
```

- [ ] **Step 8: Run all tests**

Run: `cd backend && pytest app/tests/ -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add backend/app/api/ backend/app/main.py backend/app/tests/
git commit -m "feat: add public API for authors, books, search, and filters"
```

---

## Task 9: JWT Authentication and Admin API

**Files:**
- Create: `backend/app/core/security.py`
- Create: `backend/app/api/admin/__init__.py`
- Create: `backend/app/api/admin/auth.py`
- Create: `backend/app/api/admin/entries.py`
- Create: `backend/app/api/admin/locations.py`
- Create: `backend/app/api/admin/authors.py`
- Create: `backend/app/api/admin/books.py`
- Modify: `backend/app/main.py`
- Create: `backend/app/tests/test_admin_auth.py`
- Create: `backend/app/tests/test_admin_entries.py`

- [ ] **Step 1: Create security module**

```python
# backend/app/core/security.py
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In production, store in DB. For v1, hardcoded admin.
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = pwd_context.hash("admin123")


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
```

- [ ] **Step 2: Write failing test for admin auth**

```python
# backend/app/tests/test_admin_auth.py
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && pytest app/tests/test_admin_auth.py -v`
Expected: FAIL — 404 (routes don't exist yet)

- [ ] **Step 4: Create admin auth router**

```python
# backend/app/api/admin/auth.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.security import ADMIN_PASSWORD_HASH, ADMIN_USERNAME, create_access_token, verify_password

router = APIRouter(prefix="/admin", tags=["admin-auth"])


@router.post("/login")
async def admin_login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username != ADMIN_USERNAME or not verify_password(form_data.password, ADMIN_PASSWORD_HASH):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": form_data.username})
    return {"access_token": token, "token_type": "bearer"}
```

- [ ] **Step 5: Create admin dependency**

Add to `backend/app/api/deps.py`:

```python
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from app.core.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/login")


async def get_current_admin(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload
```

- [ ] **Step 6: Create admin entries router**

```python
# backend/app/api/admin/entries.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_session
from app.crud import journal_entry as entry_crud
from app.schemas.journal_entry import JournalEntryCreate, JournalEntryRead, JournalEntryUpdate

router = APIRouter(prefix="/admin/entries", tags=["admin-entries"])


@router.post("", response_model=JournalEntryRead)
async def create_entry(
    data: JournalEntryCreate,
    db: AsyncSession = Depends(get_session),
    _admin: dict = Depends(get_current_admin),
):
    return await entry_crud.create_entry(db, data)


@router.put("/{entry_id}", response_model=JournalEntryRead)
async def update_entry(
    entry_id: int,
    data: JournalEntryUpdate,
    db: AsyncSession = Depends(get_session),
    _admin: dict = Depends(get_current_admin),
):
    entry = await entry_crud.update_entry(db, entry_id, data)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.delete("/{entry_id}")
async def delete_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_session),
    _admin: dict = Depends(get_current_admin),
):
    deleted = await entry_crud.delete_entry(db, entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"ok": True}
```

- [ ] **Step 7: Create admin locations router**

```python
# backend/app/api/admin/locations.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_session
from app.crud import location as location_crud
from app.schemas.location import LocationCreate, LocationRead, LocationUpdate

router = APIRouter(prefix="/admin/locations", tags=["admin-locations"])


@router.post("", response_model=LocationRead)
async def create_location(
    data: LocationCreate,
    db: AsyncSession = Depends(get_session),
    _admin: dict = Depends(get_current_admin),
):
    return await location_crud.create_location(db, data)


@router.put("/{location_id}", response_model=LocationRead)
async def update_location(
    location_id: int,
    data: LocationUpdate,
    db: AsyncSession = Depends(get_session),
    _admin: dict = Depends(get_current_admin),
):
    location = await location_crud.update_location(db, location_id, data)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location


@router.post("/{location_id}/relations")
async def add_relation(
    location_id: int,
    to_location_id: int,
    relation_type: str,
    description: str | None = None,
    db: AsyncSession = Depends(get_session),
    _admin: dict = Depends(get_current_admin),
):
    await location_crud.add_location_relation(db, location_id, to_location_id, relation_type, description)
    return {"ok": True}


@router.delete("/{location_id}/relations/{relation_id}")
async def delete_relation(
    location_id: int,
    relation_id: int,
    db: AsyncSession = Depends(get_session),
    _admin: dict = Depends(get_current_admin),
):
    deleted = await location_crud.delete_location_relation(db, relation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Relation not found")
    return {"ok": True}
```

- [ ] **Step 8: Create admin authors and books routers**

```python
# backend/app/api/admin/authors.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_session
from app.crud import author as author_crud
from app.schemas.author import AuthorCreate, AuthorRead

router = APIRouter(prefix="/admin/authors", tags=["admin-authors"])


@router.post("", response_model=AuthorRead)
async def create_author(
    data: AuthorCreate,
    db: AsyncSession = Depends(get_session),
    _admin: dict = Depends(get_current_admin),
):
    return await author_crud.create_author(db, data)
```

```python
# backend/app/api/admin/books.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_session
from app.crud import book as book_crud
from app.schemas.book import BookCreate, BookRead

router = APIRouter(prefix="/admin/books", tags=["admin-books"])


@router.post("", response_model=BookRead)
async def create_book(
    data: BookCreate,
    db: AsyncSession = Depends(get_session),
    _admin: dict = Depends(get_current_admin),
):
    return await book_crud.create_book(db, data)
```

- [ ] **Step 9: Wire admin routers into main.py**

Add to `backend/app/main.py` in `create_app`:

```python
    from app.api.admin.auth import router as admin_auth_router
    from app.api.admin.authors import router as admin_authors_router
    from app.api.admin.books import router as admin_books_router
    from app.api.admin.entries import router as admin_entries_router
    from app.api.admin.locations import router as admin_locations_router

    app.include_router(admin_auth_router, prefix="/api")
    app.include_router(admin_entries_router, prefix="/api")
    app.include_router(admin_locations_router, prefix="/api")
    app.include_router(admin_authors_router, prefix="/api")
    app.include_router(admin_books_router, prefix="/api")
```

- [ ] **Step 10: Run admin auth tests**

Run: `cd backend && pytest app/tests/test_admin_auth.py -v`
Expected: PASS

- [ ] **Step 11: Write admin entries test**

```python
# backend/app/tests/test_admin_entries.py
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
```

- [ ] **Step 12: Run all tests**

Run: `cd backend && pytest app/tests/ -v`
Expected: PASS

- [ ] **Step 13: Commit**

```bash
git add backend/app/core/security.py backend/app/api/admin/ backend/app/api/deps.py backend/app/main.py backend/app/tests/
git commit -m "feat: add JWT auth and admin API endpoints"
```

---

## Task 10: Alembic Migrations Setup

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/001_initial.py`

- [ ] **Step 1: Initialize Alembic**

Run: `cd backend && alembic init alembic`

- [ ] **Step 2: Configure alembic.ini**

Edit `backend/alembic.ini` — set `sqlalchemy.url` to empty (overridden in env.py):

```ini
sqlalchemy.url =
```

- [ ] **Step 3: Configure env.py**

Replace `backend/alembic/env.py`:

```python
# backend/alembic/env.py
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.database import Base

# Import all models so metadata is populated
import app.models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Generate initial migration**

Run: `cd backend && alembic revision --autogenerate -m "initial schema"`

- [ ] **Step 5: Review the generated migration**

Read the generated file in `backend/alembic/versions/` and verify it creates all tables: books, authors, locations, journal_entries, entry_locations, entry_authors, relation_locations.

- [ ] **Step 6: Commit**

```bash
git add backend/alembic.ini backend/alembic/
git commit -m "feat: add Alembic migrations with initial schema"
```

---

## Task 11: CORS and App Integration Polish

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/tests/conftest.py`

- [ ] **Step 1: Add CORS for production**

Update `backend/app/core/config.py` to read CORS_ORIGINS from env:

```python
CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]
```

This is already done in Task 1. No changes needed.

- [ ] **Step 2: Verify all API routes exist**

Run: `cd backend && python -c "from app.main import app; print([r.path for r in app.routes])"`

Expected output should include:
- `/api/health`
- `/api/locations`
- `/api/locations/{location_id}`
- `/api/entries`
- `/api/entries/{entry_id}`
- `/api/authors`
- `/api/authors/{author_id}`
- `/api/books`
- `/api/books/{book_id}`
- `/api/search`
- `/api/filters`
- `/api/admin/login`
- `/api/admin/entries`
- `/api/admin/entries/{entry_id}`
- `/api/admin/locations`
- `/api/admin/locations/{location_id}`
- `/api/admin/locations/{location_id}/relations`
- `/api/admin/locations/{location_id}/relations/{relation_id}`
- `/api/admin/authors`
- `/api/admin/books`

- [ ] **Step 3: Run full test suite**

Run: `cd backend && pytest app/tests/ -v --tb=short`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add backend/
git commit -m "feat: backend foundation complete — all public and admin API endpoints"
```

---

## Summary

This plan produces a fully functional FastAPI backend with:

- **6 data models** (Book, Author, Location, JournalEntry + 3 association tables)
- **10 public API endpoints** (locations, entries, authors, books, search, filters)
- **8 admin API endpoints** (CRUD for entries, locations, authors, books + auth)
- **JWT authentication** for admin endpoints
- **Full test suite** with async test fixtures using SQLite in-memory
- **Alembic migrations** for PostgreSQL schema management
- **Pydantic v2 schemas** for request/response validation

**Next plans to write:**
1. **Frontend Foundation** — Vite + React + Leaflet map with markers
2. **Frontend Features** — Search, filters, detail panels, responsive layout
3. **Admin CMS UI** — Simple admin interface for content management
4. **Data Pipeline** — PDF processing, LLM extraction, geocoding
