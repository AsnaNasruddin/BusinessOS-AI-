from app.workflow_generation.diff import compute_graph_diff


def _node(id_, type_, label, **data):
    return {
        "id": id_,
        "type": type_,
        "position": {"x": 0, "y": 0},
        "data": {"label": label, **data},
    }


def _edge(id_, source, target, source_handle=None):
    e = {"id": id_, "source": source, "target": target}
    if source_handle:
        e["sourceHandle"] = source_handle
    return e


def _graph(nodes, edges):
    return {"nodes": nodes, "edges": edges}


def test_identical_graphs_produce_an_empty_diff():
    graph = _graph(
        [_node("a", "trigger", "Start"), _node("b", "end", "Done")],
        [_edge("e1", "a", "b")],
    )
    same_graph_new_ids = _graph(
        [_node("x", "trigger", "Start"), _node("y", "end", "Done")],
        [_edge("e1", "x", "y")],
    )
    diff = compute_graph_diff(graph, same_graph_new_ids, "no real change")
    assert diff.nodes_added == []
    assert diff.nodes_removed == []
    assert diff.nodes_modified == []
    assert diff.edges_added == []
    assert diff.edges_removed == []


def test_added_node_is_reported():
    current = _graph([_node("a", "trigger", "Start")], [])
    new = _graph(
        [
            _node("x", "trigger", "Start"),
            _node("y", "tool", "log_activity", toolName="log_activity"),
        ],
        [_edge("e1", "x", "y")],
    )
    diff = compute_graph_diff(current, new, "added a logging step")
    assert len(diff.nodes_added) == 1
    assert diff.nodes_added[0]["data"]["label"] == "log_activity"
    assert len(diff.edges_added) == 1


def test_removed_node_is_reported():
    current = _graph(
        [
            _node("a", "trigger", "Start"),
            _node("b", "tool", "log_activity", toolName="log_activity"),
        ],
        [_edge("e1", "a", "b")],
    )
    new = _graph([_node("x", "trigger", "Start")], [])
    diff = compute_graph_diff(current, new, "removed the logging step")
    assert diff.nodes_removed == ["b"]
    assert diff.edges_removed == ["e1"]


def test_modified_node_data_is_reported():
    current = _graph(
        [_node("a", "condition", "Big enough?", field="x", operator="gt", value=200)], []
    )
    new = _graph([_node("x", "condition", "Big enough?", field="x", operator="gt", value=500)], [])
    diff = compute_graph_diff(current, new, "raised the threshold to 500")
    assert len(diff.nodes_modified) == 1
    assert diff.nodes_modified[0]["before"]["value"] == 200
    assert diff.nodes_modified[0]["after"]["value"] == 500


def test_change_summary_is_passed_through():
    graph = _graph([_node("a", "trigger", "Start")], [])
    diff = compute_graph_diff(graph, graph, "a specific summary")
    assert diff.change_summary == "a specific summary"
