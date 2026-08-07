"""The workflow graph shape and its validator. Every graph — whether typed by
hand (Phase 4) or eventually AI-generated (Phase 7) — passes through
`validate_graph()` before it's ever stored or run. No second, "trusted"
path.

v0 is deliberately linear-only: exactly one trigger, exactly one end, and
every node in between has exactly one predecessor and one successor — a
straight chain, not a DAG. Condition/approval/parallel/merge node kinds are
part of the shared type vocabulary (matching the frontend's WorkflowNodeKind)
but are rejected here with a clear message until Phase 5 (Branches +
approvals) actually implements branching execution — silently ignoring a
condition node would be far worse than refusing to save one.
"""

from typing import Literal

from pydantic import BaseModel

NodeKind = Literal["trigger", "agent", "tool", "condition", "approval", "parallel", "merge", "end"]

_V0_UNSUPPORTED_KINDS = {"condition", "approval", "parallel", "merge"}


class GraphPosition(BaseModel):
    x: float
    y: float


class GraphNode(BaseModel):
    id: str
    type: NodeKind
    position: GraphPosition
    data: dict


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str


class WorkflowGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class GraphValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_graph(graph: WorkflowGraph) -> None:
    """Raises GraphValidationError with every problem found (not just the
    first) — a plan/graph author fixing one issue at a time against a
    single-error-at-a-time validator is a bad experience, AI or human."""
    errors: list[str] = []

    node_by_id = {n.id: n for n in graph.nodes}
    if len(node_by_id) != len(graph.nodes):
        errors.append("Duplicate node ids.")

    unsupported = [n.id for n in graph.nodes if n.type in _V0_UNSUPPORTED_KINDS]
    if unsupported:
        errors.append(
            f"Node kind(s) not supported until Phase 5 (Branches + approvals): {unsupported}. "
            "v0 only executes linear trigger → agent/tool → end chains."
        )

    triggers = [n for n in graph.nodes if n.type == "trigger"]
    ends = [n for n in graph.nodes if n.type == "end"]
    if len(triggers) != 1:
        errors.append(f"Expected exactly one trigger node, found {len(triggers)}.")
    if len(ends) != 1:
        errors.append(f"Expected exactly one end node, found {len(ends)}.")

    for edge in graph.edges:
        if edge.source not in node_by_id:
            errors.append(f"Edge {edge.id!r} references unknown source node {edge.source!r}.")
        if edge.target not in node_by_id:
            errors.append(f"Edge {edge.id!r} references unknown target node {edge.target!r}.")

    # Linear-chain shape: every node has at most one outgoing and one
    # incoming edge. Checked even if triggers/ends/unsupported kinds already
    # failed above, so a single validation pass surfaces everything at once.
    outgoing: dict[str, list[str]] = {n.id: [] for n in graph.nodes}
    incoming: dict[str, list[str]] = {n.id: [] for n in graph.nodes}
    for edge in graph.edges:
        if edge.source in outgoing:
            outgoing[edge.source].append(edge.id)
        if edge.target in incoming:
            incoming[edge.target].append(edge.id)

    for node in graph.nodes:
        if node.type != "end" and len(outgoing[node.id]) != 1:
            errors.append(
                f"Node {node.id!r} must have exactly one outgoing edge in a linear graph "
                f"(has {len(outgoing[node.id])})."
            )
        if node.type != "trigger" and len(incoming[node.id]) != 1:
            errors.append(
                f"Node {node.id!r} must have exactly one incoming edge in a linear graph "
                f"(has {len(incoming[node.id])})."
            )

    if errors:
        raise GraphValidationError(errors)

    # Everything reachable from the trigger, walking the (now confirmed)
    # single-chain edges — catches a disconnected/orphan sub-chain that the
    # in/out-degree check alone wouldn't.
    order = linear_order(graph)
    if len(order) != len(graph.nodes):
        unreachable = set(node_by_id) - {n.id for n in order}
        raise GraphValidationError([f"Node(s) unreachable from the trigger: {sorted(unreachable)}"])


def linear_order(graph: WorkflowGraph) -> list[GraphNode]:
    """Walks the chain from the trigger to the end node, in execution order.
    Assumes (but does not itself enforce — call validate_graph() first) that
    the graph is a single linear chain."""
    node_by_id = {n.id: n for n in graph.nodes}
    next_by_source = {e.source: e.target for e in graph.edges}

    trigger = next((n for n in graph.nodes if n.type == "trigger"), None)
    if trigger is None:
        return []

    order = [trigger]
    seen = {trigger.id}
    current = trigger
    while current.id in next_by_source:
        next_id = next_by_source[current.id]
        if next_id in seen or next_id not in node_by_id:
            break  # cycle or dangling edge — validate_graph() is what should catch this
        current = node_by_id[next_id]
        order.append(current)
        seen.add(current.id)

    return order
