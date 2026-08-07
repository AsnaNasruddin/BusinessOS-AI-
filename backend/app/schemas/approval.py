import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ApprovalStatus = Literal["pending", "approved", "rejected"]
Decision = Literal["approved", "rejected"]


class ApprovalDecision(BaseModel):
    status: Decision
    comment: str | None = Field(default=None, max_length=2000)


class ApprovalOut(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    workflow_name: str
    title: str
    requested_by: str
    status: ApprovalStatus
    payload_subject: str | None
    payload_body: str | None
    decided_by: str | None
    decided_at: datetime | None
    created_at: datetime
