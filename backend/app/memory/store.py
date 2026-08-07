"""Phase 6 (Memory). Read/write for AgentMemory — durable facts that
survive across separate workflow runs, unlike the per-run `context` dict
Phases 4/5 already have. Called from app.workflows.nodes.tool_node's
remember_fact/recall_memories handlers, matching how app.rag.retrieve is
called from the search_kb handler — the tool node stays a thin dispatcher,
the real logic lives in its own module."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AgentMemory


async def write_memory(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    subject: str,
    fact: str,
    importance: int = 1,
    source_run_id: uuid.UUID | None = None,
) -> AgentMemory:
    memory = AgentMemory(
        org_id=org_id,
        subject=subject,
        fact=fact,
        importance=importance,
        source_run_id=source_run_id,
    )
    db.add(memory)
    await db.flush()
    return memory


async def recall_memories(
    db: AsyncSession, *, org_id: uuid.UUID, subject: str, limit: int = 5
) -> list[AgentMemory]:
    result = await db.execute(
        select(AgentMemory)
        .where(AgentMemory.org_id == org_id, AgentMemory.subject == subject)
        .order_by(AgentMemory.importance.desc(), AgentMemory.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
