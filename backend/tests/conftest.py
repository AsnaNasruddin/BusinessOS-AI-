import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.database.models import Base
from app.database.session import get_db
from app.main import app
from app.workflows.executor import execute_workflow, resume_workflow


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


@pytest.fixture
def run_pending_workflow(db_engine):
    """Executes a queued run against the test's own in-memory DB — standing
    in for what the Celery worker does in production. Calling execute_workflow()
    directly (rather than routing through Celery's eager mode) sidesteps
    asyncio.run() being invoked from inside pytest-asyncio's already-running
    event loop, which would otherwise raise. Shared across test files (Phase
    4's workflow tests, Phase 5's approval tests, Phase 6's memory tests)."""
    session_maker = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _run(run_id: uuid.UUID) -> None:
        async with session_maker() as db:
            await execute_workflow(run_id, db, get_settings())
            await db.commit()

    return _run


@pytest.fixture
def run_pending_resume(db_engine):
    """Same idea as run_pending_workflow, but for resuming a paused run —
    standing in for what resume_workflow_task does once Celery picks up the
    approval decision."""
    session_maker = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _resume(run_id: uuid.UUID, node_id: str) -> None:
        async with session_maker() as db:
            await resume_workflow(run_id, node_id, db, get_settings())
            await db.commit()

    return _resume
