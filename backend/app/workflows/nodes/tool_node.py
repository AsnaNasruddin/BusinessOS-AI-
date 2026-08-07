import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.rag.retrieve import retrieve
from app.tools.builtins.registry import TOOL_NAMES
from app.workflows.graph import GraphNode
from app.workflows.nodes.base import StepResult, WorkflowExecutionError

# search_kb is the one built-in tool with a real implementation (Phase 3's
# RAG pipeline) — everything else in the registry is genuinely unbuilt
# (no email provider, no CRM, no outbound HTTP integration exists), so
# those stay honest stubs rather than pretending to have done something.
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
