import uuid

from fastapi import APIRouter, HTTPException, status

from app.database.models.workflow import Workflow
from app.deps import CurrentOrg, CurrentUser, DbSession
from app.schemas.workflow import (
    RunOut,
    RunRequest,
    WorkflowCreate,
    WorkflowOut,
    WorkflowUpdate,
)
from app.schemas.workflow_generation import GenerateEditRequest, WorkflowGenerationRequestOut
from app.services import workflow_generation_service, workflow_service
from app.worker.tasks import execute_workflow_task, generate_workflow_plan_task
from app.workflows.graph import GraphValidationError

router = APIRouter()


def _workflow_out(workflow: Workflow) -> WorkflowOut:
    return WorkflowOut.model_validate(workflow, from_attributes=True)


def _run_out(run, workflow_name: str) -> RunOut:
    return RunOut(
        id=run.id,
        workflow_id=run.workflow_id,
        workflow_name=workflow_name,
        status=run.status,
        trigger_label=run.trigger_label,
        total_tokens=run.total_tokens,
        total_cost_usd=run.total_cost_usd,
        error_note=run.error_note,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


async def _get_workflow_or_404(db: DbSession, ctx: CurrentOrg, workflow_id: uuid.UUID) -> Workflow:
    workflow = await workflow_service.get_workflow(db, org_id=ctx.org.id, workflow_id=workflow_id)
    if workflow is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow not found.")
    return workflow


@router.get("", response_model=list[WorkflowOut])
async def list_workflows(ctx: CurrentOrg, db: DbSession) -> list[WorkflowOut]:
    workflows = await workflow_service.list_workflows(db, org_id=ctx.org.id)
    return [_workflow_out(w) for w in workflows]


@router.post("", response_model=WorkflowOut, status_code=status.HTTP_201_CREATED)
async def create_workflow(body: WorkflowCreate, ctx: CurrentOrg, db: DbSession) -> WorkflowOut:
    try:
        workflow = await workflow_service.create_workflow(db, org_id=ctx.org.id, data=body)
    except GraphValidationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "; ".join(exc.errors)) from exc
    return _workflow_out(workflow)


@router.get("/{workflow_id}", response_model=WorkflowOut)
async def get_workflow(workflow_id: uuid.UUID, ctx: CurrentOrg, db: DbSession) -> WorkflowOut:
    workflow = await _get_workflow_or_404(db, ctx, workflow_id)
    return _workflow_out(workflow)


@router.patch("/{workflow_id}", response_model=WorkflowOut)
async def update_workflow(
    workflow_id: uuid.UUID, body: WorkflowUpdate, ctx: CurrentOrg, db: DbSession
) -> WorkflowOut:
    workflow = await _get_workflow_or_404(db, ctx, workflow_id)
    try:
        workflow = await workflow_service.update_workflow(db, workflow=workflow, data=body)
    except GraphValidationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "; ".join(exc.errors)) from exc
    return _workflow_out(workflow)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(workflow_id: uuid.UUID, ctx: CurrentOrg, db: DbSession) -> None:
    workflow = await _get_workflow_or_404(db, ctx, workflow_id)
    await workflow_service.delete_workflow(db, workflow=workflow)


@router.post("/{workflow_id}/run", response_model=RunOut, status_code=status.HTTP_202_ACCEPTED)
async def run_workflow(
    workflow_id: uuid.UUID, body: RunRequest, ctx: CurrentOrg, db: DbSession
) -> RunOut:
    workflow = await _get_workflow_or_404(db, ctx, workflow_id)
    run = await workflow_service.create_run(
        db, workflow=workflow, trigger_payload=body.trigger_payload
    )
    # Commit explicitly, here, before enqueueing — the worker is a separate
    # process/connection and won't see this row until it's committed. If we
    # waited for get_db()'s post-handler commit instead, Celery could
    # deliver the task and the worker could look for the run before the
    # request's transaction ever lands, finding nothing and silently no-op'ing.
    await db.commit()
    execute_workflow_task.delay(str(run.id))
    return _run_out(run, workflow.name)


@router.get("/{workflow_id}/runs", response_model=list[RunOut])
async def list_runs(workflow_id: uuid.UUID, ctx: CurrentOrg, db: DbSession) -> list[RunOut]:
    workflow = await _get_workflow_or_404(db, ctx, workflow_id)
    runs = await workflow_service.list_runs(db, org_id=ctx.org.id, workflow_id=workflow.id)
    return [_run_out(r, workflow.name) for r in runs]


@router.post(
    "/{workflow_id}/edit-with-nl",
    response_model=WorkflowGenerationRequestOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def edit_workflow_with_nl(
    workflow_id: uuid.UUID,
    body: GenerateEditRequest,
    ctx: CurrentOrg,
    user: CurrentUser,
    db: DbSession,
) -> WorkflowGenerationRequestOut:
    workflow = await _get_workflow_or_404(db, ctx, workflow_id)
    request = await workflow_generation_service.create_edit_request(
        db, org_id=ctx.org.id, user_id=user.id, workflow=workflow, instruction=body.instruction
    )
    await db.commit()
    generate_workflow_plan_task.delay(str(request.id))
    return WorkflowGenerationRequestOut.model_validate(request, from_attributes=True)
