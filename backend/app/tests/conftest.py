import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Set admin password env var BEFORE importing app modules (security.py reads at import time)
os.environ.setdefault("HISMAP_ADMIN_PASSWORD", "admin123")
os.environ.setdefault("HISMAP_SECRET_KEY", "test-secret-key-for-testing-only")

from app.core import database
from app.core.database import Base
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

    # Patch the module-level engine and session factory so get_db() uses the test DB
    old_engine = database.engine
    old_session = database.async_session
    database.engine = db_engine
    database.async_session = session_factory

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    database.engine = old_engine
    database.async_session = old_session
