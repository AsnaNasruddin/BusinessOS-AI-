import uuid

from fastapi import APIRouter, HTTPException, status

from app.deps import CurrentOrg, DbSession
from app.schemas.workflow import RunOut, RunStepOut
from app.services import workflow_service

router = APIRouter()


@router.get("/{run_id}", response_model=RunOut)
async def get_run(run_id: uuid.UUID, ctx: CurrentOrg, db: DbSession) -> RunOut:
    result = await workflow_service.get_run(db, org_id=ctx.org.id, run_id=run_id)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found.")
    return RunOut(
        id=result.run.id,
        workflow_id=result.run.workflow_id,
        workflow_name=result.workflow_name,
        status=result.run.status,
        trigger_label=result.run.trigger_label,
        total_tokens=result.run.total_tokens,
        total_cost_usd=result.run.total_cost_usd,
        error_note=result.run.error_note,
        started_at=result.run.started_at,
        finished_at=result.run.finished_at,
    )


@router.get("/{run_id}/steps", response_model=list[RunStepOut])
async def get_run_steps(run_id: uuid.UUID, ctx: CurrentOrg, db: DbSession) -> list[RunStepOut]:
    result = await workflow_service.get_run(db, org_id=ctx.org.id, run_id=run_id)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found.")
    steps = await workflow_service.list_run_steps(db, run_id=run_id)
    return [RunStepOut.model_validate(s, from_attributes=True) for s in steps]
