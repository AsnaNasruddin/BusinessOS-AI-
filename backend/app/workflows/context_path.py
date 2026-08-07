"""Dot-path resolution against a run's accumulated context — e.g.
"trigger.customer" -> context["trigger"]["customer"]. Shared by any node
kind that reaches into context by a configured field path rather than
always consuming the immediately-preceding node's output: condition nodes
(Phase 5) and the memory tool nodes (Phase 6)."""

from typing import Any


def resolve_path(context: dict, path: str) -> Any:
    current: Any = context
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current
