import pytest

from app.workflows.graph import GraphValidationError, WorkflowGraph, linear_order, validate_graph


def _node(id_, type_, **data):
    return {"id": id_, "type": type_, "position": {"x": 0, "y": 0}, "data": data}


def _edge(id_, source, target):
    return {"id": id_, "source": source, "target": target}


def _linear_graph():
    """trigger -> agent -> tool -> end, the only shape v0 executes."""
    return WorkflowGraph.model_validate(
        {
            "nodes": [
                _node("t", "trigger", label="Start"),
                _node("a", "agent", label="Summarizer"),
                _node("k", "tool", label="log_activity"),
                _node("e", "end", label="Done"),
            ],
            "edges": [
                _edge("e1", "t", "a"),
                _edge("e2", "a", "k"),
                _edge("e3", "k", "e"),
            ],
        }
    )


def test_valid_linear_graph_passes():
    validate_graph(_linear_graph())  # no raise


def test_linear_order_follows_the_chain():
    order = linear_order(_linear_graph())
    assert [n.id for n in order] == ["t", "a", "k", "e"]


def test_missing_trigger_rejected():
    graph = _linear_graph()
    graph.nodes = [n for n in graph.nodes if n.type != "trigger"]
    with pytest.raises(GraphValidationError, match="trigger"):
        validate_graph(graph)


def test_missing_end_rejected():
    graph = _linear_graph()
    graph.nodes = [n for n in graph.nodes if n.type != "end"]
    with pytest.raises(GraphValidationError, match="end"):
        validate_graph(graph)


def test_multiple_triggers_rejected():
    graph = WorkflowGraph.model_validate(
        {
            "nodes": [
                _node("t1", "trigger"),
                _node("t2", "trigger"),
                _node("e", "end"),
            ],
            "edges": [_edge("e1", "t1", "e")],
        }
    )
    with pytest.raises(GraphValidationError, match="trigger"):
        validate_graph(graph)


@pytest.mark.parametrize("kind", ["condition", "approval", "parallel", "merge"])
def test_v0_unsupported_node_kinds_rejected(kind):
    graph = WorkflowGraph.model_validate(
        {
            "nodes": [_node("t", "trigger"), _node("x", kind), _node("e", "end")],
            "edges": [_edge("e1", "t", "x"), _edge("e2", "x", "e")],
        }
    )
    with pytest.raises(GraphValidationError, match="Phase 5"):
        validate_graph(graph)


def test_branching_node_rejected():
    """Two outgoing edges from one node is exactly the shape v0 refuses —
    that's a condition node's job, not a plain node's."""
    graph = WorkflowGraph.model_validate(
        {
            "nodes": [_node("t", "trigger"), _node("a", "agent"), _node("e", "end")],
            "edges": [
                _edge("e1", "t", "a"),
                _edge("e2", "t", "e"),  # trigger now has two outgoing edges
            ],
        }
    )
    with pytest.raises(GraphValidationError, match="outgoing"):
        validate_graph(graph)


def test_merging_node_rejected():
    graph = WorkflowGraph.model_validate(
        {
            "nodes": [
                _node("t1", "trigger"),
                _node("a", "agent"),
                _node("e", "end"),
            ],
            "edges": [
                _edge("e1", "t1", "a"),
                _edge("e2", "t1", "e"),  # target 'e' will get two incoming edges below
                _edge("e3", "a", "e"),
            ],
        }
    )
    with pytest.raises(GraphValidationError, match="incoming"):
        validate_graph(graph)


def test_orphan_node_rejected():
    graph = WorkflowGraph.model_validate(
        {
            "nodes": [
                _node("t", "trigger"),
                _node("a", "agent"),
                _node("orphan", "tool"),
                _node("e", "end"),
            ],
            # orphan has no edges at all, so it fails the outgoing/incoming
            # degree check already (not just the reachability check) — this
            # still proves it's caught, just via the earlier rule.
            "edges": [_edge("e1", "t", "a"), _edge("e2", "a", "e")],
        }
    )
    with pytest.raises(GraphValidationError):
        validate_graph(graph)


def test_edge_to_unknown_node_rejected():
    graph = WorkflowGraph.model_validate(
        {
            "nodes": [_node("t", "trigger"), _node("e", "end")],
            "edges": [_edge("e1", "t", "ghost")],
        }
    )
    with pytest.raises(GraphValidationError, match="unknown"):
        validate_graph(graph)


def test_duplicate_node_ids_rejected():
    graph = WorkflowGraph.model_validate(
        {
            "nodes": [_node("t", "trigger"), _node("t", "end")],
            "edges": [_edge("e1", "t", "t")],
        }
    )
    with pytest.raises(GraphValidationError, match="Duplicate"):
        validate_graph(graph)
