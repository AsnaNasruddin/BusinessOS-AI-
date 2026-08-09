import asyncio
import uuid


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


def _memory_graph():
    """trigger -> recall_memories(customer) -> remember_fact(customer, note)
    -> end. No agent node needed — the mechanism itself only touches
    context, so this stays fast and has no Ollama dependency."""
    return {
        "nodes": [
            _node("t", "trigger"),
            _node(
                "k_recall",
                "tool",
                label="recall_memories",
                toolName="recall_memories",
                subjectField="trigger.customer",
            ),
            _node(
                "k_remember",
                "tool",
                label="remember_fact",
                toolName="remember_fact",
                subjectField="trigger.customer",
                factField="trigger.note",
            ),
            _node("e", "end"),
        ],
        "edges": [
            _edge("e1", "t", "k_recall"),
            _edge("e2", "k_recall", "k_remember"),
            _edge("e3", "k_remember", "e"),
        ],
    }


async def _create_workflow(client, token, org_id, name="Memory Test"):
    return (
        await client.post(
            "/api/v1/workflows",
            json={"name": name, "graph": _memory_graph()},
            headers=_auth(token, org_id),
        )
    ).json()


async def _run_workflow(client, token, org_id, workflow_id, trigger_payload):
    triggered = await client.post(
        f"/api/v1/workflows/{workflow_id}/run",
        json={"trigger_payload": trigger_payload},
        headers=_auth(token, org_id),
    )
    return triggered.json()["id"]


async def _steps_by_node(client, token, org_id, run_id):
    steps = (await client.get(f"/api/v1/runs/{run_id}/steps", headers=_auth(token, org_id))).json()
    return {s["node_id"]: s for s in steps}


async def test_recall_returns_empty_before_anything_is_remembered(client, run_pending_workflow):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    workflow = await _create_workflow(client, token, org_id)

    run_id = await _run_workflow(
        client, token, org_id, workflow["id"], {"customer": "Jamie Fox", "note": "first contact"}
    )
    await run_pending_workflow(uuid.UUID(run_id))

    steps = await _steps_by_node(client, token, org_id, run_id)
    assert steps["k_recall"]["payload"] == []
    assert steps["k_recall"]["note"] == "no memories found for this subject yet"
    assert steps["k_remember"]["payload"] == {
        "subject": "Jamie Fox",
        "fact": "first contact",
        "importance": 1,
    }


async def test_recall_sees_a_fact_written_by_an_earlier_separate_run(client, run_pending_workflow):
    """The actual point of Phase 6: a fact written in one run is visible to
    a completely different, later run — not just within one run's own
    context (which Phases 4/5 already handle for free)."""
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    workflow = await _create_workflow(client, token, org_id)

    run1_id = await _run_workflow(
        client,
        token,
        org_id,
        workflow["id"],
        {"customer": "Jamie Fox", "note": "prefers email over phone"},
    )
    await run_pending_workflow(uuid.UUID(run1_id))

    run2_id = await _run_workflow(
        client, token, org_id, workflow["id"], {"customer": "Jamie Fox", "note": "wants a callback"}
    )
    await run_pending_workflow(uuid.UUID(run2_id))

    steps2 = await _steps_by_node(client, token, org_id, run2_id)
    recalled = steps2["k_recall"]["payload"]
    assert len(recalled) == 1
    assert recalled[0]["fact"] == "prefers email over phone"


async def test_recall_is_scoped_to_the_matching_subject_only(client, run_pending_workflow):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    workflow = await _create_workflow(client, token, org_id)

    run1_id = await _run_workflow(
        client, token, org_id, workflow["id"], {"customer": "Jamie Fox", "note": "fact about Jamie"}
    )
    await run_pending_workflow(uuid.UUID(run1_id))

    run2_id = await _run_workflow(
        client,
        token,
        org_id,
        workflow["id"],
        {"customer": "Morgan Lee", "note": "fact about Morgan"},
    )
    await run_pending_workflow(uuid.UUID(run2_id))

    steps2 = await _steps_by_node(client, token, org_id, run2_id)
    assert steps2["k_recall"]["payload"] == []  # Jamie's fact doesn't leak into Morgan's lookup


async def test_remember_fact_requires_both_fields_configured(client, run_pending_workflow):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    graph = {
        "nodes": [
            _node("t", "trigger"),
            _node("k", "tool", label="remember_fact", toolName="remember_fact"),  # missing fields
            _node("e", "end"),
        ],
        "edges": [_edge("e1", "t", "k"), _edge("e2", "k", "e")],
    }
    workflow = (
        await client.post(
            "/api/v1/workflows",
            json={"name": "Broken Memory", "graph": graph},
            headers=_auth(token, org_id),
        )
    ).json()

    run_id = await _run_workflow(client, token, org_id, workflow["id"], {})
    await run_pending_workflow(uuid.UUID(run_id))

    run_detail = (await client.get(f"/api/v1/runs/{run_id}", headers=_auth(token, org_id))).json()
    assert run_detail["status"] == "failed"
    assert "subjectField" in run_detail["error_note"]


async def test_list_runs_returns_every_run_newest_first(client, run_pending_workflow):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    workflow = await _create_workflow(client, token, org_id)

    run1_id = await _run_workflow(
        client, token, org_id, workflow["id"], {"customer": "A", "note": "first"}
    )
    await run_pending_workflow(uuid.UUID(run1_id))
    # SQLite's CURRENT_TIMESTAMP (used in tests) only has second-level
    # resolution, unlike Postgres in production — without this, two runs
    # started in the same second would tie on `started_at` and the
    # newest-first assertion below would be flaky for reasons that have
    # nothing to do with whether the ORDER BY itself is correct.
    await asyncio.sleep(1.1)
    run2_id = await _run_workflow(
        client, token, org_id, workflow["id"], {"customer": "B", "note": "second"}
    )
    await run_pending_workflow(uuid.UUID(run2_id))

    runs = (await client.get("/api/v1/runs", headers=_auth(token, org_id))).json()
    ids = [r["id"] for r in runs]
    assert ids.index(run2_id) < ids.index(run1_id)  # newest first
    assert all(r["workflow_name"] == "Memory Test" for r in runs)


async def test_list_runs_is_org_scoped(client, run_pending_workflow):
    owner_token, owner_org = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    workflow = await _create_workflow(client, owner_token, owner_org)
    run_id = await _run_workflow(
        client, owner_token, owner_org, workflow["id"], {"customer": "A", "note": "x"}
    )
    await run_pending_workflow(uuid.UUID(run_id))

    outsider_token, outsider_org = await _register_with_org(client, "sam@example.com", "Sam Rivera")
    runs = (await client.get("/api/v1/runs", headers=_auth(outsider_token, outsider_org))).json()
    assert runs == []
