import uuid
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import get_settings
from app.llm.base import LLMResponse
from app.llm.ollama_provider import OllamaProvider
from app.workflows.executor import execute_workflow


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


def _edge(id_, source, target):
    return {"id": id_, "source": source, "target": target}


@pytest.fixture
def run_pending_workflow(db_engine):
    """Executes a queued run against the test's own in-memory DB — standing
    in for what the Celery worker does in production. Calling execute_workflow()
    directly (rather than routing through Celery's eager mode) sidesteps
    asyncio.run() being invoked from inside pytest-asyncio's already-running
    event loop, which would otherwise raise."""
    session_maker = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _run(run_id: uuid.UUID) -> None:
        async with session_maker() as db:
            await execute_workflow(run_id, db, get_settings())
            await db.commit()

    return _run


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


async def test_create_workflow_rejects_condition_node_in_v0(client):
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
    assert "Phase 5" in response.json()["detail"]


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
