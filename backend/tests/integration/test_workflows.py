import uuid
from unittest.mock import patch

import pytest

from app.llm.base import LLMResponse
from app.llm.ollama_provider import OllamaProvider


async def _register_with_org(client, email, full_name):
    register = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correcthorsebatterystaple", "full_name": full_name},
    )
    token = register.json()["access_token"]
    orgs = (await client.get("/api/v1/orgs", headers=_auth(token))).json()
    return token, orgs[0]["id"]


def _auth(token, org_id=None):
    headers = {"Authorization": f"Bearer {token}"}
    if org_id:
        headers["X-Org-Id"] = org_id
    return headers


def _node(id_, type_, **data):
    return {"id": id_, "type": type_, "position": {"x": 0, "y": 0}, "data": data}


def _edge(id_, source, target, source_handle=None):
    edge = {"id": id_, "source": source, "target": target}
    if source_handle is not None:
        edge["source_handle"] = source_handle
    return edge


@pytest.fixture(autouse=True)
def fake_ollama():
    async def fake_complete(self, messages, *, model, temperature):
        return LLMResponse(content="Summary: everything looks fine.", model=model, tokens_used=42)

    with patch.object(OllamaProvider, "complete", new=fake_complete):
        yield


async def _create_agent(client, token, org_id):
    created = await client.post(
        "/api/v1/agents",
        json={
            "name": "Summarizer",
            "description": "Summarizes the trigger payload.",
            "system_prompt": "Summarize what happened in one sentence.",
            "model_provider": "ollama",
            "model_name": "llama3.1:8b",
            "temperature": 0.2,
            "allowed_tools": [],
            "memory_scope": "none",
        },
        headers=_auth(token, org_id),
    )
    return created.json()["id"]


def _linear_graph(agent_id):
    return {
        "nodes": [
            _node("t", "trigger", label="Manual trigger"),
            _node("a", "agent", label="Summarizer", agentId=agent_id),
            _node("k", "tool", label="log_activity", toolName="log_activity"),
            _node("e", "end", label="Done"),
        ],
        "edges": [_edge("e1", "t", "a"), _edge("e2", "a", "k"), _edge("e3", "k", "e")],
    }


async def test_create_workflow_rejects_invalid_graph(client):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    response = await client.post(
        "/api/v1/workflows",
        json={"name": "Broken", "graph": {"nodes": [_node("a", "agent")], "edges": []}},
        headers=_auth(token, org_id),
    )
    assert response.status_code == 400


async def test_create_workflow_rejects_malformed_condition_node(client):
    """condition/approval/parallel/merge are all real, supported node kinds
    as of Phase 5 — but a condition still needs a field to evaluate and
    exactly two ('yes'/'no') outgoing edges, same as any other structural
    rule in the validator."""
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    graph = {
        "nodes": [_node("t", "trigger"), _node("c", "condition"), _node("e", "end")],
        "edges": [_edge("e1", "t", "c"), _edge("e2", "c", "e")],
    }
    response = await client.post(
        "/api/v1/workflows",
        json={"name": "Has a condition", "graph": graph},
        headers=_auth(token, org_id),
    )
    assert response.status_code == 400
    assert "field" in response.json()["detail"]


async def test_create_and_get_workflow(client):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    agent_id = await _create_agent(client, token, org_id)
    created = await client.post(
        "/api/v1/workflows",
        json={"name": "Weekly Digest", "graph": _linear_graph(agent_id)},
        headers=_auth(token, org_id),
    )
    assert created.status_code == 201
    body = created.json()
    assert body["is_active"] is False
    assert body["version"] == 1

    fetched = await client.get(f"/api/v1/workflows/{body['id']}", headers=_auth(token, org_id))
    assert fetched.status_code == 200


async def test_update_workflow_graph_bumps_version(client):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    agent_id = await _create_agent(client, token, org_id)
    created = (
        await client.post(
            "/api/v1/workflows",
            json={"name": "Weekly Digest", "graph": _linear_graph(agent_id)},
            headers=_auth(token, org_id),
        )
    ).json()

    updated = await client.patch(
        f"/api/v1/workflows/{created['id']}",
        json={"graph": _linear_graph(agent_id)},
        headers=_auth(token, org_id),
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == 2


async def test_run_workflow_executes_linear_graph(client, run_pending_workflow):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    agent_id = await _create_agent(client, token, org_id)
    workflow = (
        await client.post(
            "/api/v1/workflows",
            json={"name": "Weekly Digest", "graph": _linear_graph(agent_id)},
            headers=_auth(token, org_id),
        )
    ).json()

    triggered = await client.post(
        f"/api/v1/workflows/{workflow['id']}/run",
        json={"trigger_payload": {"note": "weekly run"}},
        headers=_auth(token, org_id),
    )
    assert triggered.status_code == 202
    run_id = triggered.json()["id"]
    assert triggered.json()["status"] == "queued"

    await run_pending_workflow(uuid.UUID(run_id))

    run_detail = await client.get(f"/api/v1/runs/{run_id}", headers=_auth(token, org_id))
    assert run_detail.status_code == 200
    body = run_detail.json()
    assert body["status"] == "succeeded"
    assert body["total_tokens"] == 42  # only the agent node reports tokens
    assert body["workflow_name"] == "Weekly Digest"

    steps = (await client.get(f"/api/v1/runs/{run_id}/steps", headers=_auth(token, org_id))).json()
    assert [s["node_type"] for s in steps] == ["trigger", "agent", "tool", "end"]
    assert steps[1]["payload"]["reply"] == "Summary: everything looks fine."
    assert steps[2]["note"] == "written (logged — no live CRM configured)"


async def test_run_missing_agent_marks_run_failed(client, run_pending_workflow):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    graph = _linear_graph(str(uuid.uuid4()))  # references an agent that doesn't exist
    workflow = (
        await client.post(
            "/api/v1/workflows",
            json={"name": "Broken agent ref", "graph": graph},
            headers=_auth(token, org_id),
        )
    ).json()

    triggered = await client.post(
        f"/api/v1/workflows/{workflow['id']}/run", json={}, headers=_auth(token, org_id)
    )
    run_id = triggered.json()["id"]
    await run_pending_workflow(uuid.UUID(run_id))

    run_detail = (await client.get(f"/api/v1/runs/{run_id}", headers=_auth(token, org_id))).json()
    assert run_detail["status"] == "failed"
    assert "no longer exists" in run_detail["error_note"]


def _condition_graph():
    """trigger -> condition(amount > 100) -> yes: log_activity(A) / no:
    log_activity(B) -> end. Both branches converge on `end` directly (no
    merge needed — they're mutually exclusive, never both fire)."""
    return {
        "nodes": [
            _node("t", "trigger"),
            _node(
                "c",
                "condition",
                label="Big enough?",
                field="trigger.amount",
                operator="gt",
                value=100,
            ),
            _node("ky", "tool", label="log_activity (high)", toolName="log_activity"),
            _node("kn", "tool", label="log_activity (low)", toolName="log_activity"),
            _node("e", "end"),
        ],
        "edges": [
            _edge("e1", "t", "c"),
            _edge("e2", "c", "ky", source_handle="yes"),
            _edge("e3", "c", "kn", source_handle="no"),
            _edge("e4", "ky", "e"),
            _edge("e5", "kn", "e"),
        ],
    }


async def test_condition_takes_yes_branch_when_true(client, run_pending_workflow):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    workflow = (
        await client.post(
            "/api/v1/workflows",
            json={"name": "Refund Router", "graph": _condition_graph()},
            headers=_auth(token, org_id),
        )
    ).json()

    triggered = await client.post(
        f"/api/v1/workflows/{workflow['id']}/run",
        json={"trigger_payload": {"amount": 500}},
        headers=_auth(token, org_id),
    )
    run_id = triggered.json()["id"]
    await run_pending_workflow(uuid.UUID(run_id))

    run_detail = (await client.get(f"/api/v1/runs/{run_id}", headers=_auth(token, org_id))).json()
    assert run_detail["status"] == "succeeded"

    steps = (await client.get(f"/api/v1/runs/{run_id}/steps", headers=_auth(token, org_id))).json()
    assert [s["node_id"] for s in steps] == ["t", "c", "ky", "e"]  # 'kn' never ran
    assert steps[1]["payload"]["chosen"] == "yes"


async def test_condition_takes_no_branch_when_false(client, run_pending_workflow):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    workflow = (
        await client.post(
            "/api/v1/workflows",
            json={"name": "Refund Router", "graph": _condition_graph()},
            headers=_auth(token, org_id),
        )
    ).json()

    triggered = await client.post(
        f"/api/v1/workflows/{workflow['id']}/run",
        json={"trigger_payload": {"amount": 10}},
        headers=_auth(token, org_id),
    )
    run_id = triggered.json()["id"]
    await run_pending_workflow(uuid.UUID(run_id))

    steps = (await client.get(f"/api/v1/runs/{run_id}/steps", headers=_auth(token, org_id))).json()
    assert [s["node_id"] for s in steps] == ["t", "c", "kn", "e"]  # 'ky' never ran


def _approval_graph(agent_id):
    return {
        "nodes": [
            _node("t", "trigger"),
            _node("a", "agent", label="Summarizer", agentId=agent_id),
            _node("ap", "approval", label="Human Review", sub="approval · required"),
            _node("k", "tool", label="log_activity", toolName="log_activity"),
            _node("e", "end"),
        ],
        "edges": [
            _edge("e1", "t", "a"),
            _edge("e2", "a", "ap"),
            _edge("e3", "ap", "k"),
            _edge("e4", "k", "e"),
        ],
    }


async def test_run_pauses_at_approval_node(client, run_pending_workflow):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    agent_id = await _create_agent(client, token, org_id)
    workflow = (
        await client.post(
            "/api/v1/workflows",
            json={"name": "Needs Approval", "graph": _approval_graph(agent_id)},
            headers=_auth(token, org_id),
        )
    ).json()

    triggered = await client.post(
        f"/api/v1/workflows/{workflow['id']}/run", json={}, headers=_auth(token, org_id)
    )
    run_id = triggered.json()["id"]
    await run_pending_workflow(uuid.UUID(run_id))

    run_detail = (await client.get(f"/api/v1/runs/{run_id}", headers=_auth(token, org_id))).json()
    assert run_detail["status"] == "awaiting_approval"
    assert run_detail["total_tokens"] == 42  # tokens spent before the pause aren't lost

    approvals = (await client.get("/api/v1/approvals", headers=_auth(token, org_id))).json()
    assert len(approvals) == 1
    assert approvals[0]["status"] == "pending"
    assert approvals[0]["run_id"] == run_id
    assert approvals[0]["workflow_name"] == "Needs Approval"

    steps = (await client.get(f"/api/v1/runs/{run_id}/steps", headers=_auth(token, org_id))).json()
    assert [s["node_id"] for s in steps] == ["t", "a"]  # stopped before 'ap'


async def test_approving_resumes_the_run(client, run_pending_workflow, run_pending_resume):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    agent_id = await _create_agent(client, token, org_id)
    workflow = (
        await client.post(
            "/api/v1/workflows",
            json={"name": "Needs Approval", "graph": _approval_graph(agent_id)},
            headers=_auth(token, org_id),
        )
    ).json()
    run_id = (
        await client.post(
            f"/api/v1/workflows/{workflow['id']}/run", json={}, headers=_auth(token, org_id)
        )
    ).json()["id"]
    await run_pending_workflow(uuid.UUID(run_id))

    approval = (await client.get("/api/v1/approvals", headers=_auth(token, org_id))).json()[0]

    decided = await client.post(
        f"/api/v1/approvals/{approval['id']}/decide",
        json={"status": "approved"},
        headers=_auth(token, org_id),
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "approved"
    assert decided.json()["decided_by"] == "Jordan Avery"

    await run_pending_resume(uuid.UUID(run_id), "ap")

    run_detail = (await client.get(f"/api/v1/runs/{run_id}", headers=_auth(token, org_id))).json()
    assert run_detail["status"] == "succeeded"
    assert run_detail["total_tokens"] == 42

    steps = (await client.get(f"/api/v1/runs/{run_id}/steps", headers=_auth(token, org_id))).json()
    assert [s["node_id"] for s in steps] == ["t", "a", "ap", "k", "e"]


async def test_rejecting_ends_the_run_without_resuming(client, run_pending_workflow):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    agent_id = await _create_agent(client, token, org_id)
    workflow = (
        await client.post(
            "/api/v1/workflows",
            json={"name": "Needs Approval", "graph": _approval_graph(agent_id)},
            headers=_auth(token, org_id),
        )
    ).json()
    run_id = (
        await client.post(
            f"/api/v1/workflows/{workflow['id']}/run", json={}, headers=_auth(token, org_id)
        )
    ).json()["id"]
    await run_pending_workflow(uuid.UUID(run_id))
    approval = (await client.get("/api/v1/approvals", headers=_auth(token, org_id))).json()[0]

    decided = await client.post(
        f"/api/v1/approvals/{approval['id']}/decide",
        json={"status": "rejected", "comment": "not this week"},
        headers=_auth(token, org_id),
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "rejected"

    run_detail = (await client.get(f"/api/v1/runs/{run_id}", headers=_auth(token, org_id))).json()
    assert run_detail["status"] == "failed"
    assert "Jordan Avery" in run_detail["error_note"]
    assert "not this week" in run_detail["error_note"]

    steps = (await client.get(f"/api/v1/runs/{run_id}/steps", headers=_auth(token, org_id))).json()
    assert [s["node_id"] for s in steps] == ["t", "a", "ap"]  # 'k'/'e' never ran

    already_decided = await client.post(
        f"/api/v1/approvals/{approval['id']}/decide",
        json={"status": "approved"},
        headers=_auth(token, org_id),
    )
    assert already_decided.status_code == 409


def _parallel_merge_graph():
    return {
        "nodes": [
            _node("t", "trigger"),
            _node("p", "parallel", label="Notify"),
            _node("ka", "tool", label="send_email", toolName="send_email"),
            _node("kb", "tool", label="log_activity", toolName="log_activity"),
            _node("m", "merge", label="Join"),
            _node("e", "end"),
        ],
        "edges": [
            _edge("e1", "t", "p"),
            _edge("e2", "p", "ka"),
            _edge("e3", "p", "kb"),
            _edge("e4", "ka", "m"),
            _edge("e5", "kb", "m"),
            _edge("e6", "m", "e"),
        ],
    }


async def test_parallel_fans_out_and_merge_waits_for_both_branches(client, run_pending_workflow):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    workflow = (
        await client.post(
            "/api/v1/workflows",
            json={"name": "Fan-out Notify", "graph": _parallel_merge_graph()},
            headers=_auth(token, org_id),
        )
    ).json()

    triggered = await client.post(
        f"/api/v1/workflows/{workflow['id']}/run", json={}, headers=_auth(token, org_id)
    )
    run_id = triggered.json()["id"]
    await run_pending_workflow(uuid.UUID(run_id))

    run_detail = (await client.get(f"/api/v1/runs/{run_id}", headers=_auth(token, org_id))).json()
    assert run_detail["status"] == "succeeded"

    steps = (await client.get(f"/api/v1/runs/{run_id}/steps", headers=_auth(token, org_id))).json()
    assert [s["node_id"] for s in steps] == ["t", "p", "ka", "kb", "m", "e"]


async def test_workflow_from_other_org_is_not_visible(client):
    owner_token, owner_org = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    agent_id = await _create_agent(client, owner_token, owner_org)
    workflow = (
        await client.post(
            "/api/v1/workflows",
            json={"name": "Weekly Digest", "graph": _linear_graph(agent_id)},
            headers=_auth(owner_token, owner_org),
        )
    ).json()

    outsider_token, outsider_org = await _register_with_org(
        client, "outsider@example.com", "Sam Rivera"
    )
    response = await client.get(
        f"/api/v1/workflows/{workflow['id']}", headers=_auth(outsider_token, outsider_org)
    )
    assert response.status_code == 404
