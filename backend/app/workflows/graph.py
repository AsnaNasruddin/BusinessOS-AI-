"""The workflow graph shape and its validator. Every graph — whether typed by
hand (Phase 4/5) or eventually AI-generated (Phase 7) — passes through
`validate_graph()` before it's ever stored or run. No second, "trusted" path.

Phase 4 was linear-only. Phase 5 generalizes to a DAG that supports real
branching and a real human-approval pause point, while still keeping the
shape checkable (and therefore safe to execute without ever hanging):

- `condition` — exactly one incoming edge, exactly two outgoing edges whose
  `source_handle` is "yes"/"no". Exactly one branch runs per execution
  (app.workflows.nodes.condition_node picks it); the other branch's nodes
  simply never run for that run — that's normal, not an error.
- `approval` — exactly one incoming edge, exactly one outgoing edge. Pauses
  the run for a human decision (see app.workflows.executor); rejection ends
  the run without following that edge.
- `parallel` / `merge` — a matched pair. `parallel` fans out to two or more
  branches (all of them run). `merge` joins them back into one path, and
  *only* `merge` is allowed more than one incoming edge — and only from
  branches that all trace back, through a simple unbranched chain, to the
  same `parallel` node covering every one of its branches. That structural
  requirement is what keeps a `merge` from ever waiting on a branch that a
  `condition` upstream chose not to take, which would otherwise hang the run
  forever with no error and no timeout.
- `agent` / `tool`: still exactly one incoming, one outgoing edge — an
  ordinary processing step never silently reconverges more than one branch.
- `end`: one incoming edge is typical, but more are allowed — it's the
  natural place for mutually-exclusive `condition` branches (which will
  never both fire in the same run) to reconverge without needing a `merge`.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

NodeKind = Literal["trigger", "agent", "tool", "condition", "approval", "parallel", "merge", "end"]

CONDITION_HANDLES = {"yes", "no"}
CONDITION_OPERATORS = {"truthy", "equals", "gt", "lt"}


class GraphPosition(BaseModel):
    x: float
    y: float


class GraphNode(BaseModel):
    id: str
    type: NodeKind
    position: GraphPosition
    data: dict


class GraphEdge(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    source: str
    target: str
    # Which of the source node's outputs this edge carries — only meaningful
    # (and required) for `condition` node outgoing edges ("yes"/"no"), which
    # is why it's optional here rather than a required field on every edge.
    # Aliased to match React Flow's own Edge shape (`sourceHandle`), since
    # this graph blob is that shape verbatim, not a translated one.
    source_handle: str | None = Field(default=None, alias="sourceHandle")


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

    for edge in graph.edges:
        if edge.source not in node_by_id:
            errors.append(f"Edge {edge.id!r} references unknown source node {edge.source!r}.")
        if edge.target not in node_by_id:
            errors.append(f"Edge {edge.id!r} references unknown target node {edge.target!r}.")

    triggers = [n for n in graph.nodes if n.type == "trigger"]
    ends = [n for n in graph.nodes if n.type == "end"]
    if len(triggers) != 1:
        errors.append(f"Expected exactly one trigger node, found {len(triggers)}.")
    if len(ends) != 1:
        errors.append(f"Expected exactly one end node, found {len(ends)}.")

    # Built defensively (only for edges whose endpoints actually resolved
    # above) so a dangling edge can't KeyError this before its own error is
    # ever reported — everything else stays a plain `errors.append`.
    outgoing: dict[str, list[GraphEdge]] = {n.id: [] for n in graph.nodes}
    incoming: dict[str, list[GraphEdge]] = {n.id: [] for n in graph.nodes}
    for edge in graph.edges:
        if edge.source in outgoing:
            outgoing[edge.source].append(edge)
        if edge.target in incoming:
            incoming[edge.target].append(edge)

    for node in graph.nodes:
        errors.extend(_check_node_shape(node, outgoing[node.id], incoming[node.id]))

    if errors:
        # Structural problems (dangling edges, wrong degree, duplicate ids)
        # make cycle detection, merge-pairing, and reachability unreliable —
        # surface everything found so far and stop before attempting them.
        raise GraphValidationError(errors)

    if _has_cycle(graph, outgoing):
        raise GraphValidationError(["Graph contains a cycle — workflows must be acyclic."])

    for node in graph.nodes:
        if node.type == "merge":
            pairing_errors = _check_merge_pairing(node, incoming[node.id], node_by_id, incoming)
            if pairing_errors:
                raise GraphValidationError(pairing_errors)

    reachable = _reachable_from(triggers[0].id, outgoing)
    unreachable = set(node_by_id) - reachable
    if unreachable:
        raise GraphValidationError([f"Node(s) unreachable from the trigger: {sorted(unreachable)}"])


def _check_node_shape(
    node: GraphNode, out_edges: list[GraphEdge], in_edges: list[GraphEdge]
) -> list[str]:
    errors: list[str] = []
    n_out, n_in = len(out_edges), len(in_edges)

    if node.type == "trigger":
        if n_in != 0:
            errors.append(f"Trigger node {node.id!r} must have no incoming edges (has {n_in}).")
        if n_out != 1:
            errors.append(f"Node {node.id!r} must have exactly one outgoing edge (has {n_out}).")
    elif node.type == "end":
        if n_out != 0:
            errors.append(f"End node {node.id!r} must have no outgoing edges (has {n_out}).")
        if n_in < 1:
            errors.append(f"End node {node.id!r} must have at least one incoming edge.")
    elif node.type in ("agent", "tool", "approval"):
        if n_in != 1:
            errors.append(
                f"Node {node.id!r} must have exactly one incoming edge in a linear segment "
                f"(has {n_in})."
            )
        if n_out != 1:
            errors.append(f"Node {node.id!r} must have exactly one outgoing edge (has {n_out}).")
    elif node.type == "condition":
        if n_in != 1:
            errors.append(f"Condition node {node.id!r} must have exactly one incoming edge.")
        if not node.data.get("field"):
            errors.append(f"Condition node {node.id!r} needs a 'field' to evaluate in its data.")
        operator = node.data.get("operator", "truthy")
        if operator not in CONDITION_OPERATORS:
            errors.append(
                f"Condition node {node.id!r} has an unknown operator {operator!r} "
                f"(expected one of {sorted(CONDITION_OPERATORS)})."
            )
        handles = [e.source_handle for e in out_edges]
        if sorted(h for h in handles if h) != sorted(CONDITION_HANDLES) or len(handles) != 2:
            errors.append(
                f"Condition node {node.id!r} must have exactly two outgoing edges, handled "
                f"'yes' and 'no' (found {handles})."
            )
    elif node.type == "parallel":
        if n_in != 1:
            errors.append(f"Parallel node {node.id!r} must have exactly one incoming edge.")
        if n_out < 2:
            errors.append(f"Parallel node {node.id!r} must have at least two outgoing edges.")
    elif node.type == "merge":
        if n_in < 2:
            errors.append(f"Merge node {node.id!r} must have at least two incoming edges.")
        if n_out != 1:
            errors.append(f"Merge node {node.id!r} must have exactly one outgoing edge.")

    return errors


def _has_cycle(graph: WorkflowGraph, outgoing: dict[str, list[GraphEdge]]) -> bool:
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n.id: WHITE for n in graph.nodes}

    def visit(node_id: str) -> bool:
        color[node_id] = GRAY
        for edge in outgoing[node_id]:
            if color[edge.target] == GRAY:
                return True
            if color[edge.target] == WHITE and visit(edge.target):
                return True
        color[node_id] = BLACK
        return False

    return any(color[n.id] == WHITE and visit(n.id) for n in graph.nodes)


def _reachable_from(start_id: str, outgoing: dict[str, list[GraphEdge]]) -> set[str]:
    seen = {start_id}
    stack = [start_id]
    while stack:
        current = stack.pop()
        for edge in outgoing[current]:
            if edge.target not in seen:
                seen.add(edge.target)
                stack.append(edge.target)
    return seen


def _check_merge_pairing(
    merge_node: GraphNode,
    in_edges: list[GraphEdge],
    node_by_id: dict[str, GraphNode],
    incoming: dict[str, list[GraphEdge]],
) -> list[str]:
    """Every incoming edge of a merge node must trace back, through a simple
    (single-incoming) chain, to the same `parallel` node — and that
    parallel node's every outgoing branch must feed this exact merge. This
    is what guarantees a merge will always eventually see all its inputs:
    nothing upstream of it can be a `condition` that only sometimes fires."""
    if len(in_edges) < 2:
        return []  # already flagged by _check_node_shape

    ancestors: set[str] = set()
    for edge in in_edges:
        ancestor = _walk_back_to_parallel(edge.source, node_by_id, incoming)
        if ancestor is None:
            return [
                f"Merge node {merge_node.id!r} has a branch that doesn't trace back to a single "
                "`parallel` node through a simple chain — merge can only join branches that a "
                "parallel node fanned out (never a condition's branch, which may not fire)."
            ]
        ancestors.add(ancestor)

    if len(ancestors) != 1:
        return [f"Merge node {merge_node.id!r}'s incoming branches trace back to different nodes."]

    parallel_id = next(iter(ancestors))
    parallel_out_degree = sum(1 for e in _all_edges(incoming) if e.source == parallel_id)
    if parallel_out_degree != len(in_edges):
        return [
            f"Merge node {merge_node.id!r} joins {len(in_edges)} branch(es) but parallel node "
            f"{parallel_id!r} fans out to {parallel_out_degree} — every parallel branch must "
            "feed this merge, with no strays."
        ]
    return []


def _all_edges(incoming: dict[str, list[GraphEdge]]) -> list[GraphEdge]:
    return [e for edges in incoming.values() for e in edges]


def _walk_back_to_parallel(
    node_id: str, node_by_id: dict[str, GraphNode], incoming: dict[str, list[GraphEdge]]
) -> str | None:
    seen: set[str] = set()
    current = node_id
    while True:
        node = node_by_id[current]
        if node.type == "parallel":
            return node.id
        if node.type in ("trigger", "condition", "merge"):
            return None
        edges_in = incoming[current]
        if len(edges_in) != 1 or current in seen:
            return None
        seen.add(current)
        current = edges_in[0].source


def linear_order(graph: WorkflowGraph) -> list[GraphNode]:
    """Walks a pure trigger -> ... -> end chain in execution order. Only
    meaningful for graphs with no branching (every node exactly one in/out) —
    still correct for those (e.g. Phase 4-style workflows), but a graph
    using condition/parallel/merge/approval must be executed with
    app.workflows.executor's worklist engine instead, which resolves
    branches at runtime."""
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
            break  # cycle, dangling edge, or a branch — not this function's job to handle
        current = node_by_id[next_id]
        order.append(current)
        seen.add(current.id)

    return order
