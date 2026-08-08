"""The LLM provider interface (Phase 2, extended Phase 7). Every provider —
local Ollama or a cloud API — implements this same shape, so nothing above
this layer (agent runner, workflow engine, Phase 7's planner) ever branches
on which provider is in play. Config always comes from app.config.Settings
(Section 12, rule 4 — never hardcode a model name/provider outside
config.py).

Phase 7 adds two optional capabilities on top of Phase 2's plain
completion, both opt-in via `complete()`'s keyword args so every existing
caller (agent test runs, workflow agent nodes) is unaffected:

- `response_format` — a JSON schema the model's reply must conform to
  (Pydantic's `.model_json_schema()`). Used for structured output like
  Phase 7's `WorkflowPlan`, instead of hoping a "return JSON" instruction
  in the prompt is obeyed.
- `tools` — function definitions the model may choose to call instead of
  answering directly. A response with `tool_calls` set means "run these
  and call me again with the results" — see app.agents.executor for the
  loop that does that.

Only Ollama actually implements both today (it's what's tested against a
running model); the cloud providers accept the same parameters but raise
`ProviderNotConfiguredError`-style "not implemented" errors if asked to use
them, rather than silently ignoring a schema/tools list an untested path
can't actually honor."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict  # JSON schema for the function's arguments object


@dataclass
class LLMMessage:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str = ""
    # Set on an "assistant" message that chose to call tool(s) instead of
    # answering — echoed back into history on the next loop turn.
    tool_calls: list[ToolCall] | None = None
    # Set on a "tool" message — the result of running one of the above.
    tool_call_id: str | None = None
    name: str | None = None


@dataclass
class LLMResponse:
    content: str
    model: str
    # Only Ollama populates this today (its /api/chat response reports it
    # directly) — left None for the cloud providers rather than faking a
    # number Phase 2 never parsed out of their responses.
    tokens_used: int | None = None
    # Set instead of a normal `content` answer when the model wants to call
    # one or more tools first — app.agents.executor's loop checks this.
    tool_calls: list[ToolCall] | None = None


class ProviderNotConfiguredError(Exception):
    """Raised when a provider needs something (an API key, a reachable
    Ollama host, a capability it doesn't implement) that isn't present — a
    config/capability problem, not a bug."""


class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        model: str,
        temperature: float,
        response_format: dict | None = None,
        tools: list[ToolSpec] | None = None,
    ) -> LLMResponse: ...
