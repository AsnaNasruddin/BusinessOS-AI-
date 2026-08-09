import uuid

from fastapi import APIRouter, HTTPException, status

from app.deps import CurrentOrg, DbSession
from app.schemas.workflow import RunOut, RunStepOut
from app.services import workflow_service

router = APIRouter()


def _run_out(item: workflow_service.RunWithWorkflowName) -> RunOut:
    return RunOut(
        id=item.run.id,
        workflow_id=item.run.workflow_id,
        workflow_name=item.workflow_name,
        status=item.run.status,
        trigger_label=item.run.trigger_label,
        total_tokens=item.run.total_tokens,
        total_cost_usd=item.run.total_cost_usd,
        error_note=item.run.error_note,
        started_at=item.run.started_at,
        finished_at=item.run.finished_at,
    )


@router.get("", response_model=list[RunOut])
async def list_runs(ctx: CurrentOrg, db: DbSession) -> list[RunOut]:
    """Every run across every workflow, newest first — lets the Runs page
    show real runs instead of pointing at one hardcoded id."""
    runs = await workflow_service.list_runs_for_org(db, org_id=ctx.org.id)
    return [_run_out(r) for r in runs]


@router.get("/{run_id}", response_model=RunOut)
async def get_run(run_id: uuid.UUID, ctx: CurrentOrg, db: DbSession) -> RunOut:
    result = await workflow_service.get_run(db, org_id=ctx.org.id, run_id=run_id)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found.")
    return _run_out(result)


@router.get("/{run_id}/steps", response_model=list[RunStepOut])
async def get_run_steps(run_id: uuid.UUID, ctx: CurrentOrg, db: DbSession) -> list[RunStepOut]:
    result = await workflow_service.get_run(db, org_id=ctx.org.id, run_id=run_id)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found.")
    steps = await workflow_service.list_run_steps(db, run_id=run_id)
    return [RunStepOut.model_validate(s, from_attributes=True) for s in steps]
