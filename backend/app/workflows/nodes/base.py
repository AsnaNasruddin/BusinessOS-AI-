from dataclasses import dataclass
from typing import Any


@dataclass
class StepResult:
    """What a node handler reports back to the executor — one becomes one
    WorkflowStep row. `output` is what downstream nodes see in `context`;
    it's not necessarily the same shape as `payload` (the display record)."""

    label: str
    sub: str
    latency_ms: int
    tokens_used: int | None
    payload: dict | list | None
    note: str | None
    output: Any
    # Only agent nodes ever set this (app.llm.pricing) — Ollama is always
    # $0 (local), cloud providers get a real, if approximate, estimate.
    cost_usd: float = 0.0


class WorkflowExecutionError(Exception):
    """A node couldn't run — e.g. a dangling agentId/toolName reference.
    Caught by the executor, recorded as the run's error_note, never raised
    past it (a failed workflow run is a normal outcome, not a crash)."""
