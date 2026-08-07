import uuid

from fastapi import APIRouter, HTTPException, status

from app.deps import CurrentOrg, CurrentUser, DbSession
from app.schemas.approval import ApprovalDecision, ApprovalOut
from app.services import approval_service
from app.worker.tasks import resume_workflow_task

router = APIRouter()


def _approval_out(item: approval_service.ApprovalWithWorkflowName) -> ApprovalOut:
    a = item.approval
    return ApprovalOut(
        id=a.id,
        run_id=a.run_id,
        workflow_name=item.workflow_name,
        title=a.title,
        requested_by=a.requested_by,
        status=a.status,
        payload_subject=a.payload_subject,
        payload_body=a.payload_body,
        decided_by=a.decided_by,
        decided_at=a.decided_at,
        created_at=a.created_at,
    )


@router.get("", response_model=list[ApprovalOut])
async def list_approvals(ctx: CurrentOrg, db: DbSession) -> list[ApprovalOut]:
    approvals = await approval_service.list_approvals(db, org_id=ctx.org.id)
    return [_approval_out(a) for a in approvals]


@router.post("/{approval_id}/decide", response_model=ApprovalOut)
async def decide_approval(
    approval_id: uuid.UUID,
    body: ApprovalDecision,
    ctx: CurrentOrg,
    current_user: CurrentUser,
    db: DbSession,
) -> ApprovalOut:
    item = await approval_service.get_approval(db, org_id=ctx.org.id, approval_id=approval_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Approval not found.")

    if item.approval.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Already {item.approval.status}.")

    if body.status == "rejected":
        await approval_service.reject_approval(
            db, approval=item.approval, decided_by=current_user.full_name, comment=body.comment
        )
        await db.commit()
        return _approval_out(item)

    await approval_service.approve_approval(
        db, approval=item.approval, decided_by=current_user.full_name
    )
    node_id = item.approval.node_id
    run_id = item.approval.run_id
    # Commit before enqueueing — same reasoning as POST /workflows/{id}/run:
    # the worker is a separate connection and won't see this decision (or
    # the run's awaiting_approval -> running transition it triggers) until
    # the transaction lands.
    await db.commit()
    resume_workflow_task.delay(str(run_id), node_id)
    return _approval_out(item)
