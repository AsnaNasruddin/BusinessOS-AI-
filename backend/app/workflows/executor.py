"""Executes a validated, linear (v0) workflow graph: trigger -> [agent |
tool]* -> end, one WorkflowStep row per node, updating the WorkflowRun's
status/totals as it goes. A node failing marks the run `failed` with
`error_note` set — it does not raise past this function, so a Celery task
(or a test calling this directly) always sees a normal return; a failed
*workflow* is an expected outcome, not a crash."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database.models import Workflow, WorkflowRun, WorkflowStep
from app.workflows.graph import WorkflowGraph, linear_order
from app.workflows.nodes import agent_node, end_node, tool_node, trigger_node
from app.workflows.nodes.base import WorkflowExecutionError

_HANDLERS = {
    "trigger": trigger_node.run,
    "agent": agent_node.run,
    "tool": tool_node.run,
    "end": end_node.run,
}


async def execute_workflow(run_id: uuid.UUID, db: AsyncSession, settings: Settings) -> None:
    run = await db.get(WorkflowRun, run_id)
    if run is None:
        return

    workflow = await db.get(Workflow, run.workflow_id)
    graph = WorkflowGraph.model_validate(workflow.graph)
    order = linear_order(graph)

    run.status = "running"
    await db.flush()

    context: dict = {"trigger": run.trigger_payload}
    total_tokens = 0

    try:
        for node in order:
            handler = _HANDLERS.get(node.type)
            if handler is None:
                raise WorkflowExecutionError(f"No v0 executor for node kind {node.type!r}.")

            result = await handler(node, context, db, settings)
            db.add(
                WorkflowStep(
                    run_id=run.id,
                    node_id=node.id,
                    node_type=node.type,
                    label=result.label,
                    sub=result.sub,
                    latency_ms=result.latency_ms,
                    tokens_used=result.tokens_used,
                    payload=result.payload,
                    note=result.note,
                )
            )
            await db.flush()

            total_tokens += result.tokens_used or 0
            context[node.id] = result.output

        run.status = "succeeded"
    except Exception as exc:  # noqa: BLE001 - a failed run is a normal, recorded outcome
        run.status = "failed"
        run.error_note = str(exc)

    run.total_tokens = total_tokens
    run.finished_at = datetime.now(UTC)
    await db.flush()
