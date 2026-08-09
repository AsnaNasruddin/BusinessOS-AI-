import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base


class Approval(Base):
    """One pause point created when app.workflows.executor hits an
    `approval` node — a human decides via POST /approvals/{id}/decide,
    which either resumes the run (approved) or ends it (rejected)."""

    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_runs.id"), nullable=False, index=True
    )
    # Denormalized (also reachable via run_id -> workflow_id) so
    # scoped_query() works here like every other org-scoped resource.
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    node_id: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    decided_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
