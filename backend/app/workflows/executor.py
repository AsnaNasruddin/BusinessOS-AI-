"""Executes a validated workflow graph (app.workflows.graph.WorkflowGraph) —
Phase 4's linear trigger -> [agent|tool]* -> end chains, plus Phase 5's
branching: `condition` (evaluates and picks one of two outgoing edges),
`parallel`/`merge` (fan-out to N branches, all of which must complete before
the join continues), and `approval` (pauses the run for a human decision).

This is a worklist engine, not a fixed walk: a node becomes "ready" once its
incoming edges are satisfied (any one, for most kinds — all of them, for
`merge`), and each pass through the loop advances every node that's ready.
`parallel` branches run one after another within a pass, not concurrently —
the fan-out/join *semantics* are real, wall-clock concurrency isn't; running
each branch on its own asyncio task against a shared AsyncSession would add
real complexity for no observable difference at this scale.

A node failing, or an approval being rejected, marks the run `failed` with
`error_note` set rather than raising past this module — a Celery task (or a
test calling this directly) always sees a normal return; a failed *workflow*
is an expected outcome, not a crash. An `approval` node instead pauses:
`execute_workflow`/`resume_workflow` return with the run left in
`awaiting_approval`, and whichever calls `resume_workflow` after a decision
picks the worklist back up from exactly where it left off, using the
context/active-edges checkpoint written at pause time."""

import json
import uuid
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database.models import Approval, Workflow, WorkflowRun, WorkflowStep
from app.workflows.graph import GraphEdge, GraphNode, WorkflowGraph
from app.workflows.nodes import agent_node, condition_node, end_node, tool_node, trigger_node
from app.workflows.nodes.base import StepResult

_STEP_HANDLERS = {
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

    run.status = "running"
    await db.flush()

    context: dict = {"trigger": run.trigger_payload}
    await _drive(
        run,
        workflow,
        graph,
        context=context,
        completed=set(),
        active_edges=set(),
        db=db,
        settings=settings,
    )


async def resume_workflow(
    run_id: uuid.UUID, node_id: str, db: AsyncSession, settings: Settings
) -> None:
    """Called once a human has approved the pending Approval sitting at
    `node_id` — records that node's step, activates its one outgoing edge,
    and continues the worklist from the checkpoint `execute_workflow` left
    in `run.context`/`run.active_edge_ids` when it paused."""
    run = await db.get(WorkflowRun, run_id)
    if run is None or run.status != "awaiting_approval":
        return

    workflow = await db.get(Workflow, run.workflow_id)
    graph = WorkflowGraph.model_validate(workflow.graph)
    node = next((n for n in graph.nodes if n.id == node_id), None)
    if node is None:
        return

    existing_steps = await db.execute(
        select(WorkflowStep.node_id).where(WorkflowStep.run_id == run.id)
    )
    completed = set(existing_steps.scalars().all())
    context = run.context or {"trigger": run.trigger_payload}
    active_edges = set(run.active_edge_ids or [])

    db.add(
        WorkflowStep(
            run_id=run.id,
            node_id=node.id,
            node_type=node.type,
            label=node.data.get("label", "Approval"),
            sub="approval · approved",
            latency_ms=0,
            tokens_used=None,
            payload=None,
            note="approved — execution resumed",
        )
    )
    completed.add(node.id)
    context[node.id] = None
    for edge in graph.edges:
        if edge.source == node.id:
            active_edges.add(edge.id)

    run.status = "running"
    await db.flush()

    await _drive(
        run,
        workflow,
        graph,
        context=context,
        completed=completed,
        active_edges=active_edges,
        db=db,
        settings=settings,
    )


async def _drive(
    run: WorkflowRun,
    workflow: Workflow,
    graph: WorkflowGraph,
    *,
    context: dict,
    completed: set[str],
    active_edges: set[str],
    db: AsyncSession,
    settings: Settings,
) -> None:
    # Reserved context keys (alongside "trigger") — run-scoped identifiers
    # a node handler might need but that aren't any node's output. Phase 6's
    # memory tool nodes are the first to need these (AgentMemory rows are
    # org-scoped and traced back to the run that wrote them).
    context["_org_id"] = str(run.org_id)
    context["_run_id"] = str(run.id)

    outgoing: dict[str, list[GraphEdge]] = defaultdict(list)
    incoming: dict[str, list[GraphEdge]] = defaultdict(list)
    for edge in graph.edges:
        outgoing[edge.source].append(edge)
        incoming[edge.target].append(edge)

    def is_ready(node: GraphNode) -> bool:
        if node.id in completed:
            return False
        edges_in = incoming[node.id]
        if not edges_in:
            return node.type == "trigger"
        if node.type == "merge":
            return all(e.id in active_edges for e in edges_in)
        return any(e.id in active_edges for e in edges_in)

    total_tokens = run.total_tokens or 0

    try:
        while True:
            ready = [n for n in graph.nodes if is_ready(n)]
            if not ready:
                break

            for node in ready:
                if node.type == "approval":
                    run.context = context
                    run.active_edge_ids = list(active_edges)
                    run.total_tokens = total_tokens
                    run.status = "awaiting_approval"
                    db.add(
                        Approval(
                            run_id=run.id,
                            org_id=run.org_id,
                            node_id=node.id,
                            title=node.data.get("label", "Approval required"),
                            requested_by=f"{workflow.name} workflow",
                            payload_subject=node.data.get("sub") or None,
                            payload_body=_context_snapshot(context, incoming[node.id]),
                            status="pending",
                        )
                    )
                    await db.flush()
                    return  # paused — resume_workflow() continues this later

                step, taken_handles = await _run_node(
                    node, context, outgoing[node.id], incoming[node.id], db, settings
                )
                db.add(
                    WorkflowStep(
                        run_id=run.id,
                        node_id=node.id,
                        node_type=node.type,
                        label=step.label,
                        sub=step.sub,
                        latency_ms=step.latency_ms,
                        tokens_used=step.tokens_used,
                        payload=step.payload,
                        note=step.note,
                    )
                )
                completed.add(node.id)
                total_tokens += step.tokens_used or 0
                context[node.id] = step.output
                for edge in outgoing[node.id]:
                    if taken_handles is None or edge.source_handle in taken_handles:
                        active_edges.add(edge.id)
                await db.flush()

        run.status = "succeeded"
    except Exception as exc:  # noqa: BLE001 - a failed run is a normal, recorded outcome
        run.status = "failed"
        run.error_note = str(exc)

    run.total_tokens = total_tokens
    run.finished_at = datetime.now(UTC)
    run.context = context
    run.active_edge_ids = list(active_edges)
    await db.flush()


async def _run_node(
    node: GraphNode,
    context: dict,
    out_edges: list[GraphEdge],
    in_edges: list[GraphEdge],
    db: AsyncSession,
    settings: Settings,
) -> tuple[StepResult, set[str] | None]:
    """Runs one non-approval node, returning its StepResult and which of its
    outgoing edges' handles to activate (None means "all of them" — every
    kind except `condition`, which only ever takes one of its two)."""
    if node.type == "condition":
        result = condition_node.evaluate(node, context)
        step = StepResult(
            label=node.data.get("label", "Condition"),
            sub=f"condition · {result.field} -> {result.handle}",
            latency_ms=0,
            tokens_used=None,
            payload={"field": result.field, "value": result.value, "chosen": result.handle},
            note=None,
            output=result.handle,
        )
        return step, {result.handle}

    if node.type == "parallel":
        step = StepResult(
            label=node.data.get("label", "Parallel"),
            sub="parallel · fan-out",
            latency_ms=0,
            tokens_used=None,
            payload={"branches": len(out_edges)},
            note=None,
            output=None,
        )
        return step, None

    if node.type == "merge":
        step = StepResult(
            label=node.data.get("label", "Merge"),
            sub="merge · join",
            latency_ms=0,
            tokens_used=None,
            payload=None,
            note=None,
            output={e.source: context.get(e.source) for e in in_edges},
        )
        return step, None

    handler = _STEP_HANDLERS[node.type]
    return await handler(node, context, db, settings), None


def _context_snapshot(context: dict, in_edges: list[GraphEdge]) -> str:
    """What the approval card shows a human — the trigger payload (the
    concrete "what is this actually about") plus whatever the immediate
    predecessor produced. The predecessor alone isn't always enough: a
    `condition` node's output is just "yes"/"no", meaningless without the
    request it was evaluated against. Not the whole run's context — that
    would include every node's output so far, too noisy for a review card."""
    snapshot: dict = {"request": context.get("trigger")}
    if in_edges:
        predecessor_id = in_edges[0].source
        snapshot[predecessor_id] = context.get(predecessor_id)
    return json.dumps(snapshot, indent=2, default=str)
