"""Business logic for Module 4 (Workflow engine) — CRUD plus run
bookkeeping. Actually running a workflow lives in app.workflows.executor;
this module only ever creates the WorkflowRun row and hands off, in keeping
with the "enqueue, don't execute inline" principle used elsewhere."""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Workflow, WorkflowRun, WorkflowStep
from app.schemas.workflow import WorkflowCreate, WorkflowUpdate
from app.utils.db import scoped_query
from app.workflows.graph import WorkflowGraph, validate_graph


@dataclass
class RunWithWorkflowName:
    run: WorkflowRun
    workflow_name: str


async def create_workflow(db: AsyncSession, *, org_id: uuid.UUID, data: WorkflowCreate) -> Workflow:
    validate_graph(WorkflowGraph.model_validate(data.graph))
    workflow = Workflow(org_id=org_id, **data.model_dump())
    db.add(workflow)
    await db.flush()
    return workflow


async def list_workflows(db: AsyncSession, *, org_id: uuid.UUID) -> list[Workflow]:
    result = await db.execute(scoped_query(Workflow, org_id))
    return list(result.scalars().all())


async def get_workflow(
    db: AsyncSession, *, org_id: uuid.UUID, workflow_id: uuid.UUID
) -> Workflow | None:
    result = await db.execute(scoped_query(Workflow, org_id).where(Workflow.id == workflow_id))
    return result.scalar_one_or_none()


async def update_workflow(
    db: AsyncSession, *, workflow: Workflow, data: WorkflowUpdate
) -> Workflow:
    changes = data.model_dump(exclude_unset=True)
    if "graph" in changes:
        validate_graph(WorkflowGraph.model_validate(changes["graph"]))
        workflow.version += 1
    for field, value in changes.items():
        setattr(workflow, field, value)
    await db.flush()
    await db.refresh(workflow)
    return workflow


async def delete_workflow(db: AsyncSession, *, workflow: Workflow) -> None:
    await db.delete(workflow)
    await db.flush()


async def create_run(
    db: AsyncSession, *, workflow: Workflow, trigger_payload: dict | None
) -> WorkflowRun:
    run = WorkflowRun(
        workflow_id=workflow.id,
        org_id=workflow.org_id,
        status="queued",
        trigger_label=workflow.trigger_type,
        trigger_payload=trigger_payload,
    )
    db.add(run)
    await db.flush()
    return run


async def get_run(
    db: AsyncSession, *, org_id: uuid.UUID, run_id: uuid.UUID
) -> RunWithWorkflowName | None:
    result = await db.execute(
        select(WorkflowRun, Workflow.name)
        .join(Workflow, Workflow.id == WorkflowRun.workflow_id)
        .where(WorkflowRun.org_id == org_id, WorkflowRun.id == run_id)
    )
    row = result.first()
    if row is None:
        return None
    run, workflow_name = row
    return RunWithWorkflowName(run=run, workflow_name=workflow_name)


async def list_runs(
    db: AsyncSession, *, org_id: uuid.UUID, workflow_id: uuid.UUID
) -> list[WorkflowRun]:
    result = await db.execute(
        select(WorkflowRun)
        .where(WorkflowRun.org_id == org_id, WorkflowRun.workflow_id == workflow_id)
        .order_by(WorkflowRun.started_at.desc())
    )
    return list(result.scalars().all())


async def list_runs_for_org(
    db: AsyncSession, *, org_id: uuid.UUID, limit: int = 50
) -> list[RunWithWorkflowName]:
    """Every run across every workflow, newest first — what the Runs page
    needs to let a user browse real runs instead of pointing at a single
    hardcoded id (the known gap flagged since Phase 4)."""
    result = await db.execute(
        select(WorkflowRun, Workflow.name)
        .join(Workflow, Workflow.id == WorkflowRun.workflow_id)
        .where(WorkflowRun.org_id == org_id)
        .order_by(WorkflowRun.started_at.desc())
        .limit(limit)
    )
    return [RunWithWorkflowName(run=run, workflow_name=name) for run, name in result.all()]


async def list_run_steps(db: AsyncSession, *, run_id: uuid.UUID) -> list[WorkflowStep]:
    result = await db.execute(
        select(WorkflowStep).where(WorkflowStep.run_id == run_id).order_by(WorkflowStep.created_at)
    )
    return list(result.scalars().all())
