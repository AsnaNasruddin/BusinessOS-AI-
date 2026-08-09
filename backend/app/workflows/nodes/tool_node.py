import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.memory.store import recall_memories as recall_memories_store
from app.memory.store import write_memory
from app.rag.retrieve import retrieve
from app.tools.builtins.registry import TOOL_NAMES
from app.workflows.context_path import resolve_path
from app.workflows.graph import GraphNode
from app.workflows.nodes.base import StepResult, WorkflowExecutionError

# search_kb, remember_fact, and recall_memories are the built-in tools with
# real implementations (Phase 3's RAG pipeline, Phase 6's memory store) —
# everything else in the registry is genuinely unbuilt (no email provider,
# no CRM, no outbound HTTP integration exists), so those stay honest stubs
# rather than pretending to have done something.
_STUB_NOTES = {
    "send_email": "sent (logged — no live email provider configured)",
    "log_activity": "written (logged — no live CRM configured)",
    "http_request": "request logged — no live outbound call made",
}


async def run(node: GraphNode, context: dict, db: AsyncSession, settings: Settings) -> StepResult:
    tool_name = node.data.get("toolName")
    if not tool_name or tool_name not in TOOL_NAMES:
        raise WorkflowExecutionError(
            f"Tool node {node.id!r} references an unknown tool {tool_name!r}."
        )

    if tool_name == "search_kb":
        return await _run_search_kb(node, settings)
    if tool_name == "remember_fact":
        return await _run_remember_fact(node, context, db)
    if tool_name == "recall_memories":
        return await _run_recall_memories(node, context, db)

    return StepResult(
        label=tool_name,
        sub=f"tool · {tool_name}",
        latency_ms=5,
        tokens_used=None,
        payload=None,
        note=_STUB_NOTES.get(tool_name, "stub tool — no real implementation yet"),
        output=None,
    )


async def _run_search_kb(node: GraphNode, settings: Settings) -> StepResult:
    kb_id = node.data.get("kbId")
    query = node.data.get("query")
    if not kb_id or not query:
        raise WorkflowExecutionError(
            f"search_kb node {node.id!r} needs both a kbId and a query configured (v0 doesn't "
            "infer a query from context automatically)."
        )

    start = time.monotonic()
    chunks = await retrieve(kb_id=uuid.UUID(kb_id), query=query, k=5, settings=settings)
    latency_ms = int((time.monotonic() - start) * 1000)

    payload = [{"source": c.source, "score": round(c.score, 3)} for c in chunks]
    return StepResult(
        label="search_kb",
        sub="tool · RAG retrieval",
        latency_ms=latency_ms,
        tokens_used=None,
        payload=payload,
        note=None,
        output=payload,
    )


async def _run_remember_fact(node: GraphNode, context: dict, db: AsyncSession) -> StepResult:
    """Writes one durable AgentMemory row, resolving `subjectField`/
    `factField` (dot-paths, same syntax as a condition node's `field`)
    against the run's context — e.g. subjectField="trigger.customer",
    factField="trigger.reason" remembers the reason under that customer's
    name. Unlike search_kb this needs `db` directly (Postgres, not Chroma)."""
    subject_field = node.data.get("subjectField")
    fact_field = node.data.get("factField")
    if not subject_field or not fact_field:
        raise WorkflowExecutionError(
            f"remember_fact node {node.id!r} needs both a subjectField and a factField "
            "(dot-paths into the run's context)."
        )

    subject = resolve_path(context, subject_field)
    fact = resolve_path(context, fact_field)
    if not subject or not fact:
        raise WorkflowExecutionError(
            f"remember_fact node {node.id!r}: {subject_field!r} or {fact_field!r} resolved to "
            "nothing in the current context."
        )

    importance = int(node.data.get("importance", 1))
    org_id = uuid.UUID(context["_org_id"])
    run_id = uuid.UUID(context["_run_id"]) if context.get("_run_id") else None

    memory = await write_memory(
        db,
        org_id=org_id,
        subject=str(subject),
        fact=str(fact),
        importance=importance,
        source_run_id=run_id,
    )

    return StepResult(
        label="remember_fact",
        sub=f"tool · remembered for {subject}",
        latency_ms=0,
        tokens_used=None,
        payload={"subject": str(subject), "fact": str(fact), "importance": importance},
        note=None,
        output={"memory_id": str(memory.id)},
    )


async def _run_recall_memories(node: GraphNode, context: dict, db: AsyncSession) -> StepResult:
    """Looks up AgentMemory rows for `subjectField`'s resolved value —
    exact match on subject, no fuzzy search in v0. Returns them as the
    node's output so a downstream agent node's prompt (built from the full
    context in app.workflows.nodes.agent_node) can see what's been
    remembered about this subject from *earlier, separate* runs."""
    subject_field = node.data.get("subjectField")
    if not subject_field:
        raise WorkflowExecutionError(
            f"recall_memories node {node.id!r} needs a subjectField (a dot-path into context)."
        )

    subject = resolve_path(context, subject_field)
    if not subject:
        raise WorkflowExecutionError(
            f"recall_memories node {node.id!r}: {subject_field!r} resolved to nothing in the "
            "current context."
        )

    limit = int(node.data.get("limit", 5))
    org_id = uuid.UUID(context["_org_id"])

    memories = await recall_memories_store(db, org_id=org_id, subject=str(subject), limit=limit)
    payload = [
        {"fact": m.fact, "importance": m.importance, "created_at": m.created_at.isoformat()}
        for m in memories
    ]

    return StepResult(
        label="recall_memories",
        sub=f"tool · {len(payload)} found for {subject}",
        latency_ms=0,
        tokens_used=None,
        payload=payload,
        note=None if payload else "no memories found for this subject yet",
        output=payload,
    )
