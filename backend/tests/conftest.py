import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database.models import Base
from app.database.session import get_db
from app.main import app


@pytest.fixture
async def db_engine():
    """A fresh in-memory SQLite database per test — StaticPool keeps every
    connection on the same in-memory DB for the test's lifetime, and a
    function-scoped engine avoids cross-event-loop connection reuse issues
    between tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def client(db_engine):
    """Async HTTP client bound to the FastAPI app, with `get_db` overridden
    to use this test's isolated database instead of the real one."""
    session_maker = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
