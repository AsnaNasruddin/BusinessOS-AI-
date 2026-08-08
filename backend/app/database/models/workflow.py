import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    # {"nodes": [...], "edges": [...]} — validated against app.workflows.graph.WorkflowGraph
    # before it's ever stored (create/update route), never trusted as-is on read.
    graph: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # manual (built in the visual editor) | generated (Phase 7 NL planner,
    # never hand-edited since) | hybrid (started as one, a save from the
    # other path touched it too) — a cheap, honest breadcrumb for "what
    # fraction of generated workflows get hand-edited later," not an audit
    # table of its own.
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    # `use_alter` because WorkflowGenerationRequest.target_workflow_id (below)
    # points back at this table — a genuine circular FK between the two,
    # resolved by deferring this specific constraint to a post-create ALTER
    # TABLE rather than requiring the other table to already exist inline.
    generation_request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "workflow_generation_requests.id",
            use_alter=True,
            name="fk_workflows_generation_request_id",
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflows.id"), nullable=False, index=True
    )
    # Denormalized (also reachable via workflow_id) so scoped_query() — which
    # assumes a direct org_id column — works here like every other resource.
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    trigger_label: Mapped[str] = mapped_column(String(20), nullable=False)
    trigger_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    error_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Checkpoint written whenever the run pauses at an `approval` node (and
    # kept up to date otherwise) so app.workflows.executor.resume_workflow
    # can pick execution back up after a human decides — {node_id: output}
    # for every node that's already run, exactly what a fresh run's
    # in-memory `context` dict holds.
    context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Edge ids the executor has already marked "taken" — needed on resume so
    # a condition node's chosen branch (the one edge out of two) isn't
    # re-decided or lost.
    active_edge_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_runs.id"), nullable=False, index=True
    )
    node_id: Mapped[str] = mapped_column(String(100), nullable=False)
    node_type: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    sub: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
