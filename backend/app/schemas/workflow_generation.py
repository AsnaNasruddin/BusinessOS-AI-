"""Phase 7 (Natural Language Workflow Generator) — addendum §16.5, §16.11,
§16.12. The planner never emits `Workflow.graph` directly (app.workflows.
graph.WorkflowGraph); it emits this smaller intermediate representation
(IR), referencing existing entities by name rather than id, with layout and
id-generation left entirely to the deterministic compiler
(app.workflow_generation.compiler) — see the ADR's alternatives table for
why."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.workflows.graph import NodeKind

GenerationMode = Literal["create", "edit"]
GenerationStatus = Literal[
    "pending", "awaiting_answers", "planning", "ready", "applied", "rejected", "failed"
]


class NewAgentDraft(BaseModel):
    """A proposed Agent config the planner wants created — always shown for
    review before any Agent row is written (Module 5 CRUD, not a bypass of
    it)."""

    name: str
    description: str
    system_prompt: str
    suggested_model: str = "ollama/llama3.1:8b"
    suggested_tools: list[str] = []
    memory_scope: Literal["none", "session", "persistent"] = "none"


class PlanNode(BaseModel):
    ref: str  # local id, e.g. "n1" — scoped to this plan only
    kind: NodeKind
    label: str  # human-readable, e.g. "Customer Support Agent"

    trigger_type: Literal["manual", "webhook", "schedule", "email"] | None = None

    agent_ref: str | None = None  # name of an EXISTING Agent, if reused
    new_agent: NewAgentDraft | None = None  # set instead of agent_ref if none fits
    required_output_fields: list[str] = []  # e.g. ["refund_amount"] — backward-threading, §16.6

    tool_ref: str | None = None  # name of an EXISTING built-in tool
    kb_ref: str | None = None  # name of a KnowledgeBase, attached to an agent node

    # Natural-language-friendly condition shape, e.g. "refund_amount > 500"
    # — the compiler parses this into the real engine's {field, operator,
    # value} shape (app.workflows.nodes.condition_node), resolving
    # `refund_amount` against whichever upstream node's
    # required_output_fields declared it. Kept as a free expression here
    # (not the engine's own shape) because it's both what the spec asks the
    # planner to produce and a more natural thing for an LLM to write than
    # a pre-split field/operator/value triple.
    condition_expression: str | None = None
    condition_description: str | None = None  # "Is the refund over $500?"

    approval_message: str | None = None


class PlanEdge(BaseModel):
    source_ref: str
    target_ref: str
    branch: Literal["yes", "no"] | None = None  # only meaningful when source is a condition


class MissingComponent(BaseModel):
    kind: Literal["agent", "tool", "knowledge_base"]
    name: str
    reason: str  # "This workflow requires access to Gmail, but Gmail has not been connected yet."


class WorkflowPlan(BaseModel):
    summary: str  # seeds the human-friendly preview
    nodes: list[PlanNode] = []
    edges: list[PlanEdge] = []
    missing_components: list[MissingComponent] = []
    clarifying_questions: list[str] = []  # non-empty ⇒ plan is a draft, not final


class WorkflowDiff(BaseModel):
    """§16.11 — what an NL edit request produces for review, never applied
    until the user explicitly confirms it."""

    change_summary: str  # "Refund threshold changed from $500 to $1,000"
    nodes_added: list[dict] = []
    nodes_removed: list[str] = []  # node ids
    nodes_modified: list[dict] = []  # {id, before, after}
    edges_added: list[dict] = []
    edges_removed: list[str] = []  # edge ids


class CompileError(Exception):
    """Raised by the compiler on any unresolvable reference or unthreaded
    required_output_field — never a silent best-effort (§16.8)."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


# --- API request/response shapes (§16.12) ---


class GenerateCreateRequest(BaseModel):
    description: str = Field(min_length=1)


class GenerateEditRequest(BaseModel):
    instruction: str = Field(min_length=1)


class AnswerRequest(BaseModel):
    answer: str = Field(min_length=1)


class RejectRequest(BaseModel):
    reason: str | None = None


class WorkflowGenerationRequestOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    user_id: uuid.UUID
    mode: GenerationMode
    target_workflow_id: uuid.UUID | None
    raw_text: str
    status: GenerationStatus
    round: int
    clarifying_questions: list[str] | None
    answers: list[str] | None
    plan: dict[str, Any] | None
    diff: dict[str, Any] | None
    missing_components: list[dict[str, Any]] | None
    error: str | None
    created_at: datetime
    updated_at: datetime
