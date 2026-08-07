"""Business logic for approvals — deciding one either resumes the paused
workflow run (approved, via Celery) or ends it (rejected, handled directly
here since there's nothing left to execute)."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Approval, Workflow, WorkflowRun, WorkflowStep


@dataclass
class ApprovalWithWorkflowName:
    approval: Approval
    workflow_name: str


class ApprovalAlreadyDecidedError(Exception):
    pass


async def list_approvals(db: AsyncSession, *, org_id: uuid.UUID) -> list[ApprovalWithWorkflowName]:
    result = await db.execute(
        select(Approval, Workflow.name)
        .join(WorkflowRun, WorkflowRun.id == Approval.run_id)
        .join(Workflow, Workflow.id == WorkflowRun.workflow_id)
        .where(Approval.org_id == org_id)
        .order_by(Approval.created_at.desc())
    )
    return [ApprovalWithWorkflowName(approval=a, workflow_name=name) for a, name in result.all()]


async def get_approval(
    db: AsyncSession, *, org_id: uuid.UUID, approval_id: uuid.UUID
) -> ApprovalWithWorkflowName | None:
    result = await db.execute(
        select(Approval, Workflow.name)
        .join(WorkflowRun, WorkflowRun.id == Approval.run_id)
        .join(Workflow, Workflow.id == WorkflowRun.workflow_id)
        .where(Approval.org_id == org_id, Approval.id == approval_id)
    )
    row = result.first()
    if row is None:
        return None
    approval, workflow_name = row
    return ApprovalWithWorkflowName(approval=approval, workflow_name=workflow_name)


async def reject_approval(
    db: AsyncSession, *, approval: Approval, decided_by: str, comment: str | None
) -> None:
    """Rejection needs no Celery task — there's nothing to resume, just a
    run to mark failed and a step to record for visibility."""
    if approval.status != "pending":
        raise ApprovalAlreadyDecidedError(f"Approval {approval.id} was already {approval.status}.")

    approval.status = "rejected"
    approval.decided_by = decided_by
    approval.decided_at = datetime.now(UTC)

    run = await db.get(WorkflowRun, approval.run_id)
    run.status = "failed"
    note = f"Rejected by {decided_by}" + (f": {comment}" if comment else "")
    run.error_note = note
    run.finished_at = datetime.now(UTC)

    db.add(
        WorkflowStep(
            run_id=run.id,
            node_id=approval.node_id,
            node_type="approval",
            label=approval.title,
            sub="approval · rejected",
            latency_ms=0,
            tokens_used=None,
            payload=None,
            note=note,
        )
    )
    await db.flush()


async def approve_approval(db: AsyncSession, *, approval: Approval, decided_by: str) -> None:
    """Marks the decision; the caller (the API route) is responsible for
    committing and enqueueing resume_workflow_task — same "commit before
    enqueue" requirement as POST /workflows/{id}/run."""
    if approval.status != "pending":
        raise ApprovalAlreadyDecidedError(f"Approval {approval.id} was already {approval.status}.")

    approval.status = "approved"
    approval.decided_by = decided_by
    approval.decided_at = datetime.now(UTC)
    await db.flush()
