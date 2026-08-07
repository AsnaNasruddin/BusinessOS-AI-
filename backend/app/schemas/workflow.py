import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

TriggerType = Literal["manual", "webhook", "schedule", "email"]
RunStatus = Literal["queued", "running", "awaiting_approval", "succeeded", "failed", "cancelled"]


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    trigger_type: TriggerType = "manual"
    graph: dict = Field(default_factory=lambda: {"nodes": [], "edges": []})


class WorkflowUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    trigger_type: TriggerType | None = None
    graph: dict | None = None
    is_active: bool | None = None


class WorkflowOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    description: str
    trigger_type: str
    graph: dict
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime


class RunRequest(BaseModel):
    trigger_payload: dict | None = None


class RunOut(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    workflow_name: str
    status: RunStatus
    trigger_label: str
    total_tokens: int
    total_cost_usd: float
    error_note: str | None
    started_at: datetime
    finished_at: datetime | None


class RunStepOut(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    node_id: str
    node_type: str
    label: str
    sub: str
    latency_ms: int
    tokens_used: int | None
    payload: Any | None
    note: str | None
