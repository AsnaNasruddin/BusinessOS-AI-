"""Callable tools an agent can actually invoke through app.agents.executor's
tool-calling loop — distinct from `registry.py`'s BUILTIN_TOOLS, which is
just display metadata for the Agents/Tools UI pages and for workflow `tool`
nodes (those are dispatched by app.workflows.nodes.tool_node instead, on a
graph edge, not by an agent's own reasoning). Only the three read-only
lookups Phase 7's planner needs are wired up here — nothing state-changing
is agent-callable, per the ADR's security rule ("planner tool access is
read-only by construction")."""

from collections.abc import Awaitable, Callable
from typing import Any

from app.llm.base import ToolSpec
from app.tools.builtins import list_agents, list_knowledge_bases, list_tools

ToolFn = Callable[..., Awaitable[Any]]

CALLABLE_TOOLS: dict[str, tuple[ToolSpec, ToolFn]] = {
    list_agents.SPEC.name: (list_agents.SPEC, list_agents.run),
    list_tools.SPEC.name: (list_tools.SPEC, list_tools.run),
    list_knowledge_bases.SPEC.name: (list_knowledge_bases.SPEC, list_knowledge_bases.run),
}
