import uuid
from unittest.mock import patch

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


def _edge(id_, source, target):
    return {"id": id_, "source": source, "target": target}


async def test_stats_are_all_zero_for_a_fresh_org(client):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    resp = await client.get("/api/v1/dashboard/stats", headers=_auth(token, org_id))
    assert resp.status_code == 200
    body = resp.json()
    assert body["active_workflows"] == 0
    assert body["total_workflows"] == 0
    assert body["runs_24h"] == 0
    assert body["success_rate_7d"] == 0.0
    assert body["tokens_30d"] == 0
    assert body["est_cost_30d"] == 0.0
    assert body["cost_note"] == "No runs in the last 30 days"


async def test_stats_reflect_a_real_completed_run(client, run_pending_workflow):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    agent = await client.post(
        "/api/v1/agents",
        json={
            "name": "Summarizer",
            "description": "d",
            "system_prompt": "Summarize.",
            "model_provider": "ollama",
            "model_name": "llama3.1:8b",
            "temperature": 0.2,
            "allowed_tools": [],
            "memory_scope": "none",
        },
        headers=_auth(token, org_id),
    )
    agent_id = agent.json()["id"]
    graph = {
        "nodes": [
            _node("t", "trigger"),
            _node("a", "agent", agentId=agent_id),
            _node("e", "end"),
        ],
        "edges": [_edge("e1", "t", "a"), _edge("e2", "a", "e")],
    }
    workflow = (
        await client.post(
            "/api/v1/workflows",
            json={"name": "Test WF", "graph": graph},
            headers=_auth(token, org_id),
        )
    ).json()
    await client.patch(
        f"/api/v1/workflows/{workflow['id']}",
        json={"is_active": True},
        headers=_auth(token, org_id),
    )

    async def fake_complete(self, messages, **kwargs):
        return LLMResponse(content="done", model=kwargs["model"], tokens_used=100)

    with patch.object(OllamaProvider, "complete", new=fake_complete):
        triggered = await client.post(
            f"/api/v1/workflows/{workflow['id']}/run", json={}, headers=_auth(token, org_id)
        )
        await run_pending_workflow(uuid.UUID(triggered.json()["id"]))

    resp = await client.get("/api/v1/dashboard/stats", headers=_auth(token, org_id))
    body = resp.json()
    assert body["total_workflows"] == 1
    assert body["active_workflows"] == 1
    assert body["runs_24h"] == 1
    assert body["success_rate_7d"] == 100.0
    assert body["tokens_30d"] == 100
    assert body["est_cost_30d"] == 0.0  # Ollama is always free
    assert body["cost_note"] == "All runs on Ollama (free)"


async def test_stats_are_org_scoped(client):
    owner_token, owner_org = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    graph = {
        "nodes": [_node("t", "trigger"), _node("e", "end")],
        "edges": [_edge("e1", "t", "e")],
    }
    await client.post(
        "/api/v1/workflows",
        json={"name": "Owner WF", "graph": graph},
        headers=_auth(owner_token, owner_org),
    )

    outsider_token, outsider_org = await _register_with_org(
        client, "sam@example.com", "Sam Rivera"
    )
    resp = await client.get(
        "/api/v1/dashboard/stats", headers=_auth(outsider_token, outsider_org)
    )
    assert resp.json()["total_workflows"] == 0
