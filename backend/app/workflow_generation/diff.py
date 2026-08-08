"""§16.11 — natural-language editing produces a reviewable diff, never a
silent live edit. The addendum describes the planner returning a
"partial" plan (only the changed nodes/edges) merged against the current
graph — but that needs stable identity between a partial plan's refs and
the live graph's real node ids, which the IR (scoped per-plan, §16.5) has
no way to express. This implementation instead has the edit-mode planner
call (app.workflow_generation.planner.generate_plan with
current_graph_summary set) describe the COMPLETE desired end-state, which
gets compiled the same way a fresh create does — then this module diffs
the two *compiled* graphs structurally. Genuinely simpler than a
partial-plan merge, and still a real diff the user must confirm before
anything is applied, which is the actual point of §16.11.

Nodes are matched between the two graphs by (type, label) rather than by
id — a fresh compile always mints new random node ids (app.workflow_
generation.compiler), even for a node that's conceptually unchanged, so
raw id equality would misreport every single node as removed-and-added."""

from app.schemas.workflow_generation import WorkflowDiff


def compute_graph_diff(current_graph: dict, new_graph: dict, change_summary: str) -> WorkflowDiff:
    current_nodes = current_graph.get("nodes", [])
    new_nodes = new_graph.get("nodes", [])
    current_by_key = {_node_key(n): n for n in current_nodes}
    new_by_key = {_node_key(n): n for n in new_nodes}
    current_id_to_key = {n["id"]: _node_key(n) for n in current_nodes}
    new_id_to_key = {n["id"]: _node_key(n) for n in new_nodes}

    nodes_added = [n for key, n in new_by_key.items() if key not in current_by_key]
    shared_keys = current_by_key.keys() & new_by_key.keys()
    nodes_removed = [current_by_key[key]["id"] for key in current_by_key if key not in new_by_key]
    nodes_modified = [
        {
            "id": new_by_key[key]["id"],
            "before": current_by_key[key]["data"],
            "after": new_by_key[key]["data"],
        }
        for key in shared_keys
        if current_by_key[key]["data"] != new_by_key[key]["data"]
    ]

    current_edges = current_graph.get("edges", [])
    new_edges = new_graph.get("edges", [])
    current_edge_by_identity = {_edge_identity(e, current_id_to_key): e for e in current_edges}
    new_edge_by_identity = {_edge_identity(e, new_id_to_key): e for e in new_edges}

    edges_added = [
        e for ident, e in new_edge_by_identity.items() if ident not in current_edge_by_identity
    ]
    edges_removed = [
        e["id"]
        for ident, e in current_edge_by_identity.items()
        if ident not in new_edge_by_identity
    ]

    return WorkflowDiff(
        change_summary=change_summary,
        nodes_added=nodes_added,
        nodes_removed=nodes_removed,
        nodes_modified=nodes_modified,
        edges_added=edges_added,
        edges_removed=edges_removed,
    )


def _node_key(node: dict) -> tuple:
    return (node["type"], node["data"].get("label"))


def _edge_identity(edge: dict, id_to_key: dict) -> tuple:
    return (
        id_to_key.get(edge["source"]),
        id_to_key.get(edge["target"]),
        edge.get("sourceHandle"),
    )
