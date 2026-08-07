"""The LLM provider interface (Phase 2). Every provider — local Ollama or a
cloud API — implements this same shape, so nothing above this layer (agent
runner, and eventually the workflow engine) ever branches on which provider
is in play. Config always comes from app.config.Settings (Section 12, rule
4 — never hardcode a model name/provider outside config.py)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str
    # Only Ollama populates this today (its /api/chat response reports it
    # directly) — left None for the cloud providers rather than faking a
    # number Phase 2 never parsed out of their responses.
    tokens_used: int | None = None


class ProviderNotConfiguredError(Exception):
    """Raised when a provider needs something (an API key, a reachable
    Ollama host) that isn't present — a config problem, not a bug."""


class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self, messages: list[LLMMessage], *, model: str, temperature: float
    ) -> LLMResponse: ...
