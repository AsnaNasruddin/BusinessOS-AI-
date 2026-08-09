"""§16.9 — every generated or edited graph passes through the exact same
validator manually-built graphs use (Instructions for Claude Code, rule
13: no second, "trusted because the AI made it" path). This module exists
only because §16.13 names it as part of the layout, keeping the
dependency direction one-way — workflow_generation depends on
workflows.graph, never the reverse."""

from app.workflows.graph import GraphValidationError, WorkflowGraph, validate_graph


def validate_compiled_graph(graph: dict) -> None:
    validate_graph(WorkflowGraph.model_validate(graph))


__all__ = ["GraphValidationError", "validate_compiled_graph"]
