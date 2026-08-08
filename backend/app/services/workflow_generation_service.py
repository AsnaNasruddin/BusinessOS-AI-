"""Business logic for Phase 7 (Natural Language Workflow Generator) — CRUD
plus the round-by-round planning state machine. The actual LLM call lives
in app.workflow_generation.planner; this module only ever advances
WorkflowGenerationRequest state and hands off, in keeping with the
"enqueue, don't execute inline" principle used elsewhere (Phase 4's
workflow_service is the direct precedent)."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database.models import Workflow, WorkflowGenerationRequest
from app.schemas.workflow import WorkflowCreate
from app.schemas.workflow_generation import CompileError, WorkflowPlan
from app.services import workflow_service
from app.utils.db import scoped_query
from app.workflow_generation.compiler import compile_plan_to_graph
from app.workflow_generation.diff import compute_graph_diff
from app.workflow_generation.planner import generate_plan
from app.workflow_generation.validator_bridge import validate_compiled_graph
from app.workflows.graph import GraphValidationError

MAX_ROUNDS = 3


async def create_request(
    db: AsyncSession, *, org_id: uuid.UUID, user_id: uuid.UUID, description: str
) -> WorkflowGenerationRequest:
    request = WorkflowGenerationRequest(
        org_id=org_id, user_id=user_id, mode="create", raw_text=description, status="pending"
    )
    db.add(request)
    await db.flush()
    return request


async def create_edit_request(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    workflow: Workflow,
    instruction: str,
) -> WorkflowGenerationRequest:
    request = WorkflowGenerationRequest(
        org_id=org_id,
        user_id=user_id,
        mode="edit",
        target_workflow_id=workflow.id,
        raw_text=instruction,
        status="pending",
    )
    db.add(request)
    await db.flush()
    return request


async def get_request(
    db: AsyncSession, *, org_id: uuid.UUID, request_id: uuid.UUID
) -> WorkflowGenerationRequest | None:
    result = await db.execute(
        scoped_query(WorkflowGenerationRequest, org_id).where(
            WorkflowGenerationRequest.id == request_id
        )
    )
    return result.scalar_one_or_none()


async def submit_answer(
    db: AsyncSession, *, request: WorkflowGenerationRequest, answer: str
) -> bool:
    """Appends one answer. Returns True once every question asked so far
    has been answered — the caller's signal to enqueue the next planning
    round."""
    request.answers = [*(request.answers or []), answer]
    await db.flush()
    await db.refresh(request)
    return len(request.answers) >= len(request.clarifying_questions or [])


async def run_generation_round(
    db: AsyncSession,
    *,
    request: WorkflowGenerationRequest,
    settings: Settings,
    force_final: bool = False,
) -> None:
    """One planner call. Advances `request` to `awaiting_answers` (more
    questions, and rounds remain) or `ready` (a final plan, no pending
    questions — §16.7's cap: after MAX_ROUNDS, force a best-effort final
    plan instead of asking forever)."""
    request.status = "planning"
    await db.flush()

    try:
        current_graph_summary = None
        if request.mode == "edit" and request.target_workflow_id:
            workflow = await db.get(Workflow, request.target_workflow_id)
            if workflow is not None:
                current_graph_summary = _summarize_graph(workflow.graph)

        request.round += 1
        must_finalize = force_final or request.round >= MAX_ROUNDS

        plan = await generate_plan(
            raw_text=_effective_instruction(request, must_finalize),
            clarifying_questions=request.clarifying_questions or [],
            answers=request.answers or [],
            org_id=request.org_id,
            db=db,
            settings=settings,
            current_graph_summary=current_graph_summary,
        )
    except Exception as exc:  # noqa: BLE001 - a failed generation is a normal, recorded outcome
        request.status = "failed"
        request.error = str(exc)
        await db.flush()
        return

    if plan.clarifying_questions and not must_finalize:
        request.clarifying_questions = [
            *(request.clarifying_questions or []),
            *plan.clarifying_questions,
        ]
        request.status = "awaiting_answers"
        await db.flush()
        return

    request.plan = plan.model_dump(mode="json")
    request.missing_components = [m.model_dump(mode="json") for m in plan.missing_components]
    request.status = "ready"
    await db.flush()

    if request.mode == "edit":
        # Fold diff prep into the same round rather than a separate API
        # step — by the time a caller sees status="ready" on an edit
        # request, both the plan and its diff are already there together.
        try:
            await prepare_edit_diff(db, request=request)
        except CompileError:
            pass  # prepare_edit_diff already recorded status="failed" + error


def _effective_instruction(request: WorkflowGenerationRequest, must_finalize: bool) -> str:
    if not must_finalize:
        return request.raw_text
    return (
        f"{request.raw_text}\n\n(You must produce a complete plan now — do not ask any more "
        "clarifying questions, even if some things remain uncertain. Use missing_components "
        "for anything you're unsure about instead.)"
    )


def _summarize_graph(graph: dict) -> str:
    lines = []
    for node in graph.get("nodes", []):
        lines.append(f"- {node['type']}: {node['data'].get('label', node['id'])}")
    return "\n".join(lines)


async def compile_and_save(
    db: AsyncSession, *, request: WorkflowGenerationRequest, workflow_name: str
) -> Workflow:
    """§16.8/§16.9 — create mode only. Compiles `request.plan`, validates it
    through the exact same validator manual graphs use, and creates a real
    (but inactive) Workflow row — same as any manually-built one, just with
    `source="generated"`. Never sets `is_active` (ADR security rule 2).

    Callable with `status="failed"` too, as long as a plan exists — that's
    exactly the retry-after-fixing-a-missing-component path (§16.10):
    compiling failed once because a referenced agent didn't exist yet, the
    user created it, and now the *same* plan should just compile cleanly
    without re-running the planner."""
    if not request.plan or request.status not in ("ready", "failed"):
        raise CompileError(["Request isn't ready to compile yet."])

    plan = WorkflowPlan.model_validate(request.plan)
    try:
        graph = await compile_plan_to_graph(plan, org_id=request.org_id, db=db)
        validate_compiled_graph(graph)
    except (CompileError, GraphValidationError) as exc:
        request.status = "failed"
        request.error = "; ".join(exc.errors)
        await db.flush()
        raise

    workflow = await workflow_service.create_workflow(
        db,
        org_id=request.org_id,
        data=WorkflowCreate(name=workflow_name, description=plan.summary, graph=graph),
        source="generated",
        generation_request_id=request.id,
    )
    request.status = "applied"
    await db.flush()
    return workflow


async def prepare_edit_diff(db: AsyncSession, *, request: WorkflowGenerationRequest) -> None:
    """§16.11 — edit mode only. Compiles the (complete, desired-end-state)
    plan and diffs it against the target workflow's current graph. Never
    touches the live workflow — that only happens in apply_edit, after
    explicit user confirmation."""
    if request.status != "ready" or not request.plan:
        raise CompileError(["Request isn't ready to diff yet."])

    workflow = await db.get(Workflow, request.target_workflow_id)
    if workflow is None:
        request.status = "failed"
        request.error = "The workflow being edited no longer exists."
        await db.flush()
        raise CompileError([request.error])

    plan = WorkflowPlan.model_validate(request.plan)
    try:
        new_graph = await compile_plan_to_graph(plan, org_id=request.org_id, db=db)
        validate_compiled_graph(new_graph)
    except (CompileError, GraphValidationError) as exc:
        request.status = "failed"
        request.error = "; ".join(exc.errors)
        await db.flush()
        raise

    diff = compute_graph_diff(workflow.graph, new_graph, plan.summary)
    request.diff = diff.model_dump(mode="json")
    await db.flush()


async def apply_edit(db: AsyncSession, *, request: WorkflowGenerationRequest) -> Workflow:
    """Re-validates and re-compiles from scratch (deterministic, no LLM —
    cheap) rather than trusting the diff computed earlier, in case anything
    referenced has changed since. Writes through the EXISTING update path
    so `Workflow.version` increments exactly like a manual edit would."""
    if request.status != "ready" or not request.plan or request.diff is None:
        raise CompileError(["Edit isn't ready to apply yet."])

    workflow = await db.get(Workflow, request.target_workflow_id)
    if workflow is None:
        raise CompileError(["The workflow being edited no longer exists."])

    plan = WorkflowPlan.model_validate(request.plan)
    graph = await compile_plan_to_graph(plan, org_id=request.org_id, db=db)
    validate_compiled_graph(graph)

    workflow.graph = graph
    workflow.version += 1
    # A cheap, honest breadcrumb (§16.4): a workflow that started manual and
    # gets an AI edit becomes "hybrid". One already "generated" or "hybrid"
    # stays as-is — an AI edit on an already-AI-touched workflow doesn't
    # need a further category.
    if workflow.source == "manual":
        workflow.source = "hybrid"
    workflow.generation_request_id = request.id
    request.status = "applied"
    await db.flush()
    await db.refresh(workflow)
    return workflow


async def reject_request(
    db: AsyncSession, *, request: WorkflowGenerationRequest, reason: str | None
) -> None:
    request.status = "rejected"
    if reason:
        request.error = reason
    await db.flush()
    await db.refresh(request)
