import asyncio
import uuid
from collections.abc import Coroutine
from typing import Any

from app.config import get_settings
from app.database.session import async_session_maker, engine
from app.worker.celery_app import celery_app
from app.workflows.executor import execute_workflow, resume_workflow


@celery_app.task(name="ping")
def ping() -> str:
    """Trivial task proving the worker container boots and can execute
    something — real tasks (execute_workflow, generate_workflow_plan) land
    here in their respective phases."""
    return "pong"


@celery_app.task(name="execute_workflow")
def execute_workflow_task(run_id: str) -> None:
    """Celery entrypoint (sync, per Celery's model) wrapping the real async
    executor. `POST /workflows/{id}/run` enqueues this rather than running
    execute_workflow() inline — Section 5's "enqueue, don't block the
    request" principle, same one Phase 3 already applies less strictly by
    running ingestion inline (a known, flagged simplification there)."""
    asyncio.run(_run_and_dispose(_execute_workflow_async(uuid.UUID(run_id))))


@celery_app.task(name="resume_workflow")
def resume_workflow_task(run_id: str, node_id: str) -> None:
    """Enqueued by POST /approvals/{id}/decide once an approval is granted —
    picks a paused run back up from the approval node it stopped at."""
    asyncio.run(_run_and_dispose(_resume_workflow_async(uuid.UUID(run_id), node_id)))


async def _run_and_dispose(coro: Coroutine[Any, Any, None]) -> None:
    """Every task call is its own `asyncio.run()` (Celery's prefork model),
    each spinning up a brand new event loop — but `engine` (app.database.
    session) is created once at import time and pools asyncpg connections
    bound to whichever loop first used them. A second task in the same
    worker process would otherwise hand those connections to a *new* loop
    and asyncpg raises "attached to a different loop". Disposing the pool
    after every task forces the next one to open fresh connections against
    its own loop — the standard fix for async SQLAlchemy under Celery's
    one-loop-per-task model."""
    try:
        await coro
    finally:
        await engine.dispose()


async def _execute_workflow_async(run_id: uuid.UUID) -> None:
    async with async_session_maker() as db:
        try:
            await execute_workflow(run_id, db, get_settings())
            await db.commit()
        except Exception:
            await db.rollback()
            raise


async def _resume_workflow_async(run_id: uuid.UUID, node_id: str) -> None:
    async with async_session_maker() as db:
        try:
            await resume_workflow(run_id, node_id, db, get_settings())
            await db.commit()
        except Exception:
            await db.rollback()
            raise
