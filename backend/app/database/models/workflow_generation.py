import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base


class WorkflowGenerationRequest(Base):
    """Phase 7 (Natural Language Workflow Generator). One row per
    generate-or-edit request — `mode=create` with `target_workflow_id=NULL`
    behaves like a fresh draft; `mode=edit` additionally produces a `diff`
    instead of a bare `plan`. One shape serves both, mirroring how
    WorkflowRun already serves manual and scheduled triggers alike."""

    __tablename__ = "workflow_generation_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    mode: Mapped[str] = mapped_column(String(10), nullable=False, default="create")
    target_workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workflows.id"), nullable=True
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # How many planner calls have happened so far — not in the addendum's
    # original schema sketch, but needed to enforce §16.7's 3-round cap;
    # clarifying_questions/answers alone (below) don't distinguish "3 short
    # rounds" from "1 round with 3 questions."
    round: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Both accumulate across every round (extended, never overwritten) so
    # `zip(clarifying_questions, answers)` is always the full Q&A history
    # §16.7 says the next planner call should see.
    clarifying_questions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    answers: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # The WorkflowPlan IR (app.schemas.workflow_generation), once generated.
    plan: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Populated only when mode = edit — a WorkflowDiff, never applied until
    # the user explicitly confirms it.
    diff: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    missing_components: Mapped[list | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
