from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=settings.debug, future=True)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a scoped async session per request.

    Owns the transaction boundary: commits once the route handler returns
    successfully, rolls back on any exception. Services/routes should
    `db.add()` and `await db.flush()` as needed but never call
    `db.commit()` themselves — one commit point avoids partial-commit bugs
    when a service function is composed from other service functions
    (e.g. register_user calling create_org)."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
