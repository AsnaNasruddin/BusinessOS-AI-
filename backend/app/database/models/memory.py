import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base


class AgentMemory(Base):
    """A durable fact written by the `remember_fact` tool and readable by
    `recall_memories` in a *later, separate* run — the piece Phase 4/5's
    per-run `context` dict can't do on its own, since that dict dies with
    the run. Scoped to the org and a free-text `subject` (e.g. a customer
    name or email) rather than to the agent that wrote it — any agent in
    the org can recall a fact about a subject, not just the one that
    remembered it, matching "the business remembers this customer" rather
    than "this bot remembers.\""""

    __tablename__ = "agent_memories"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    fact: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # Nullable — traceability back to the run that wrote this fact, but not
    # every conceivable memory has to come from a workflow run (e.g. a
    # future manual-entry path), so this isn't a hard requirement.
    source_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workflow_runs.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
