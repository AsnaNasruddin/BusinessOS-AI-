"""Evaluates a `condition` node against the run's accumulated context and
picks which of its two outgoing edges ("yes" / "no") the executor should
follow. Doesn't produce a normal StepResult on its own — the executor
special-cases condition nodes because, unlike every other node kind, this
one changes which node runs next rather than just what one node returns."""

from dataclasses import dataclass
from typing import Any

from app.workflows.graph import GraphNode
from app.workflows.nodes.base import WorkflowExecutionError


@dataclass
class ConditionResult:
    handle: str  # "yes" or "no" — which outgoing edge to follow
    field: str
    value: Any


def evaluate(node: GraphNode, context: dict) -> ConditionResult:
    field = node.data.get("field")
    if not field:
        raise WorkflowExecutionError(
            f"Condition node {node.id!r} is missing a 'field' to evaluate."
        )

    value = _resolve_path(context, field)
    operator = node.data.get("operator", "truthy")
    target = node.data.get("value")

    if operator == "truthy":
        matched = bool(value)
    elif operator == "equals":
        matched = value == target
    elif operator in ("gt", "lt"):
        matched = _compare(value, target, operator)
    else:
        raise WorkflowExecutionError(
            f"Condition node {node.id!r} has an unknown operator {operator!r}."
        )

    return ConditionResult(handle="yes" if matched else "no", field=field, value=value)


def _resolve_path(context: dict, path: str) -> Any:
    current: Any = context
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _compare(value: Any, target: Any, operator: str) -> bool:
    try:
        left, right = float(value), float(target)
    except (TypeError, ValueError):
        return False
    return left > right if operator == "gt" else left < right
