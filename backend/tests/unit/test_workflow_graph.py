import pytest

from app.workflows.graph import GraphValidationError, WorkflowGraph, linear_order, validate_graph


def _node(id_, type_, **data):
    return {"id": id_, "type": type_, "position": {"x": 0, "y": 0}, "data": data}


def _edge(id_, source, target, source_handle=None):
    edge = {"id": id_, "source": source, "target": target}
    if source_handle is not None:
        edge["source_handle"] = source_handle
    return edge


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


def test_agent_node_with_two_incoming_edges_rejected():
    """Only `end` and `merge` may have more than one incoming edge — an
    ordinary processing node can't silently reconverge two branches (here,
    both of a condition's outputs point straight at the same agent node)."""
    graph = WorkflowGraph.model_validate(
        {
            "nodes": [
                _node("t", "trigger"),
                _node("c", "condition", field="trigger.x"),
                _node("a", "agent"),
                _node("e", "end"),
            ],
            "edges": [
                _edge("e1", "t", "c"),
                _edge("e2", "c", "a", source_handle="yes"),
                _edge("e3", "c", "a", source_handle="no"),
                _edge("e4", "a", "e"),
            ],
        }
    )
    with pytest.raises(GraphValidationError, match="incoming"):
        validate_graph(graph)


def test_end_node_may_have_multiple_incoming_edges():
    """Unlike agent/tool, `end` is a valid place for a condition's two
    mutually-exclusive branches to reconverge without an explicit merge."""
    graph = WorkflowGraph.model_validate(
        {
            "nodes": [
                _node("t", "trigger"),
                _node("c", "condition", field="trigger.x"),
                _node("a", "agent"),
                _node("e", "end"),
            ],
            "edges": [
                _edge("e1", "t", "c"),
                _edge("e2", "c", "a", source_handle="yes"),
                _edge("e3", "c", "e", source_handle="no"),
                _edge("e4", "a", "e"),
            ],
        }
    )
    validate_graph(graph)  # no raise


def test_condition_requires_field():
    graph = WorkflowGraph.model_validate(
        {
            "nodes": [_node("t", "trigger"), _node("c", "condition"), _node("e", "end")],
            "edges": [
                _edge("e1", "t", "c"),
                _edge("e2", "c", "e", source_handle="yes"),
                _edge("e3", "c", "e", source_handle="no"),
            ],
        }
    )
    with pytest.raises(GraphValidationError, match="field"):
        validate_graph(graph)


def test_condition_requires_yes_no_handles():
    graph = WorkflowGraph.model_validate(
        {
            "nodes": [
                _node("t", "trigger"),
                _node("c", "condition", field="trigger.x"),
                _node("e", "end"),
            ],
            "edges": [
                _edge("e1", "t", "c"),
                _edge("e2", "c", "e", source_handle="maybe"),
                _edge("e3", "c", "e"),
            ],
        }
    )
    with pytest.raises(GraphValidationError, match="yes"):
        validate_graph(graph)


def test_valid_condition_graph_passes():
    graph = WorkflowGraph.model_validate(
        {
            "nodes": [
                _node("t", "trigger"),
                _node("c", "condition", field="trigger.amount", operator="gt", value=100),
                _node("a", "agent"),
                _node("e", "end"),
            ],
            "edges": [
                _edge("e1", "t", "c"),
                _edge("e2", "c", "a", source_handle="yes"),
                _edge("e3", "c", "e", source_handle="no"),
                _edge("e4", "a", "e"),
            ],
        }
    )
    validate_graph(graph)  # no raise


def test_valid_approval_graph_passes():
    graph = WorkflowGraph.model_validate(
        {
            "nodes": [_node("t", "trigger"), _node("ap", "approval"), _node("e", "end")],
            "edges": [_edge("e1", "t", "ap"), _edge("e2", "ap", "e")],
        }
    )
    validate_graph(graph)  # no raise


def test_approval_with_two_outgoing_edges_rejected():
    graph = WorkflowGraph.model_validate(
        {
            "nodes": [
                _node("t", "trigger"),
                _node("ap", "approval"),
                _node("a", "agent"),
                _node("e", "end"),
            ],
            "edges": [
                _edge("e1", "t", "ap"),
                _edge("e2", "ap", "a"),
                _edge("e3", "ap", "e"),
            ],
        }
    )
    with pytest.raises(GraphValidationError, match="outgoing"):
        validate_graph(graph)


def test_valid_parallel_merge_pair_passes():
    graph = WorkflowGraph.model_validate(
        {
            "nodes": [
                _node("t", "trigger"),
                _node("p", "parallel"),
                _node("a", "tool"),
                _node("b", "tool"),
                _node("m", "merge"),
                _node("e", "end"),
            ],
            "edges": [
                _edge("e1", "t", "p"),
                _edge("e2", "p", "a"),
                _edge("e3", "p", "b"),
                _edge("e4", "a", "m"),
                _edge("e5", "b", "m"),
                _edge("e6", "m", "e"),
            ],
        }
    )
    validate_graph(graph)  # no raise


def test_merge_fed_by_condition_branch_rejected():
    """A merge fed by a `condition` branch (rather than a `parallel` fan-out)
    could wait forever on the branch that condition didn't take — that's
    exactly the hang the merge/parallel pairing rule exists to prevent."""
    graph = WorkflowGraph.model_validate(
        {
            "nodes": [
                _node("t", "trigger"),
                _node("c", "condition", field="trigger.x"),
                _node("a", "tool"),
                _node("m", "merge"),
                _node("e", "end"),
            ],
            "edges": [
                _edge("e1", "t", "c"),
                _edge("e2", "c", "a", source_handle="yes"),
                _edge("e3", "c", "m", source_handle="no"),
                _edge("e4", "a", "m"),
                _edge("e5", "m", "e"),
            ],
        }
    )
    with pytest.raises(GraphValidationError, match="parallel"):
        validate_graph(graph)


def test_merge_with_stray_parallel_branch_rejected():
    """Parallel fans out to 3 branches but merge only joins 2 of them —
    the third would just never be waited on."""
    graph = WorkflowGraph.model_validate(
        {
            "nodes": [
                _node("t", "trigger"),
                _node("p", "parallel"),
                _node("a", "tool"),
                _node("b", "tool"),
                _node("c", "tool"),
                _node("m", "merge"),
                _node("e", "end"),
            ],
            "edges": [
                _edge("e1", "t", "p"),
                _edge("e2", "p", "a"),
                _edge("e3", "p", "b"),
                _edge("e4", "p", "c"),
                _edge("e5", "a", "m"),
                _edge("e6", "b", "m"),
                _edge("e7", "c", "e"),
                _edge("e8", "m", "e"),
            ],
        }
    )
    with pytest.raises(GraphValidationError, match="fans out"):
        validate_graph(graph)


def test_cycle_rejected():
    """A cycle among nodes that each still satisfy their own in/out-degree
    rule (so the structural checks alone wouldn't catch it) — x/y/z loop
    back on each other, disconnected from the otherwise-valid t -> e path."""
    graph = WorkflowGraph.model_validate(
        {
            "nodes": [
                _node("t", "trigger"),
                _node("e", "end"),
                _node("x", "tool"),
                _node("y", "tool"),
                _node("z", "tool"),
            ],
            "edges": [
                _edge("e1", "t", "e"),
                _edge("e2", "x", "y"),
                _edge("e3", "y", "z"),
                _edge("e4", "z", "x"),
            ],
        }
    )
    with pytest.raises(GraphValidationError, match="cycle"):
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
