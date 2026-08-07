import asyncio
import uuid

from app.config import get_settings
from app.database.session import async_session_maker
from app.worker.celery_app import celery_app
from app.workflows.executor import execute_workflow


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
    asyncio.run(_execute_workflow_async(uuid.UUID(run_id)))


async def _execute_workflow_async(run_id: uuid.UUID) -> None:
    async with async_session_maker() as db:
        try:
            await execute_workflow(run_id, db, get_settings())
            await db.commit()
        except Exception:
            await db.rollback()
            raise
