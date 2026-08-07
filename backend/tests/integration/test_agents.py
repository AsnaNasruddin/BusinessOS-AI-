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


_AGENT_PAYLOAD = {
    "name": "Triage Classifier",
    "description": "Classifies incoming support email.",
    "system_prompt": "Classify the email.",
    "model_provider": "ollama",
    "model_name": "llama3.1:8b",
    "temperature": 0.2,
    "allowed_tools": [],
    "memory_scope": "none",
}


async def test_list_agents_empty_initially(client):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    response = await client.get("/api/v1/agents", headers=_auth(token, org_id))
    assert response.status_code == 200
    assert response.json() == []


async def test_create_and_get_agent(client):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    created = await client.post("/api/v1/agents", json=_AGENT_PAYLOAD, headers=_auth(token, org_id))
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Triage Classifier"
    assert body["org_id"] == org_id

    fetched = await client.get(f"/api/v1/agents/{body['id']}", headers=_auth(token, org_id))
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]


async def test_update_agent(client):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    created = (
        await client.post("/api/v1/agents", json=_AGENT_PAYLOAD, headers=_auth(token, org_id))
    ).json()

    updated = await client.patch(
        f"/api/v1/agents/{created['id']}",
        json={"temperature": 0.9},
        headers=_auth(token, org_id),
    )
    assert updated.status_code == 200
    assert updated.json()["temperature"] == 0.9
    assert updated.json()["name"] == "Triage Classifier"  # untouched fields survive a PATCH


async def test_delete_agent(client):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    created = (
        await client.post("/api/v1/agents", json=_AGENT_PAYLOAD, headers=_auth(token, org_id))
    ).json()

    deleted = await client.delete(f"/api/v1/agents/{created['id']}", headers=_auth(token, org_id))
    assert deleted.status_code == 204

    missing = await client.get(f"/api/v1/agents/{created['id']}", headers=_auth(token, org_id))
    assert missing.status_code == 404


async def test_agent_from_other_org_is_not_visible(client):
    owner_token, owner_org = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    created = (
        await client.post(
            "/api/v1/agents", json=_AGENT_PAYLOAD, headers=_auth(owner_token, owner_org)
        )
    ).json()

    outsider_token, outsider_org = await _register_with_org(
        client, "outsider@example.com", "Sam Rivera"
    )
    response = await client.get(
        f"/api/v1/agents/{created['id']}", headers=_auth(outsider_token, outsider_org)
    )
    assert response.status_code == 404


async def test_agent_test_endpoint_without_ollama_returns_503(client, monkeypatch):
    """Simulates an unreachable LLM backend (rather than relying on Ollama
    genuinely not running — it may well be running in dev, as it now is in
    this repo) to prove the provider-not-configured path returns a clean
    503 instead of a raw connection-error 500."""
    from app.llm.base import ProviderNotConfiguredError
    from app.llm.ollama_provider import OllamaProvider

    async def fake_complete(self, messages, *, model, temperature):
        raise ProviderNotConfiguredError("Can't reach Ollama — is it running?")

    monkeypatch.setattr(OllamaProvider, "complete", fake_complete)

    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    created = (
        await client.post("/api/v1/agents", json=_AGENT_PAYLOAD, headers=_auth(token, org_id))
    ).json()

    response = await client.post(
        f"/api/v1/agents/{created['id']}/test",
        json={"message": "hello"},
        headers=_auth(token, org_id),
    )
    assert response.status_code == 503


async def test_list_tools_returns_builtin_tools(client):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    response = await client.get("/api/v1/tools", headers=_auth(token, org_id))
    assert response.status_code == 200
    names = {t["name"] for t in response.json()}
    assert {"search_kb", "send_email", "log_activity", "http_request"} <= names
