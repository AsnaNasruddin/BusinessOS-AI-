import json
import uuid
from unittest.mock import patch

import pytest

from app.llm.base import LLMResponse
from app.llm.ollama_provider import OllamaProvider
from app.services import workflow_generation_service


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


async def _create_agent(client, token, org_id, name="Support Agent"):
    created = await client.post(
        "/api/v1/agents",
        json={
            "name": name,
            "description": "handles tickets",
            "system_prompt": "Classify. Return JSON: {category}.",
            "model_provider": "ollama",
            "model_name": "llama3.1:8b",
            "temperature": 0.2,
            "allowed_tools": [],
            "memory_scope": "none",
        },
        headers=_auth(token, org_id),
    )
    return created.json()


def _simple_plan(agent_name):
    return {
        "summary": "Classifies incoming tickets.",
        "nodes": [
            {"ref": "t", "kind": "trigger", "label": "New Ticket", "trigger_type": "manual"},
            {"ref": "a", "kind": "agent", "label": agent_name, "agent_ref": agent_name},
            {"ref": "e", "kind": "end", "label": "Done"},
        ],
        "edges": [
            {"source_ref": "t", "target_ref": "a"},
            {"source_ref": "a", "target_ref": "e"},
        ],
        "missing_components": [],
        "clarifying_questions": [],
    }


@pytest.fixture
def planner_queue():
    """Populated by each test with the plan(s) the fake planner should
    return, one per round, popped in order."""
    return []


@pytest.fixture(autouse=True)
def fake_planner(planner_queue):
    async def fake_complete(
        self, messages, *, model, temperature, response_format=None, tools=None
    ):
        if response_format is not None:
            plan = planner_queue.pop(0)
            return LLMResponse(content=json.dumps(plan), model=model, tokens_used=42)
        # Tool-gathering phase — never actually calls a tool in these
        # tests, keeping them independent of AgentExecutor's own loop
        # (which has its own dedicated unit tests).
        return LLMResponse(content="", model=model, tokens_used=5, tool_calls=None)

    with patch.object(OllamaProvider, "complete", new=fake_complete):
        yield


@pytest.fixture
def run_pending_generation(db_engine):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.config import get_settings

    session_maker = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _run(request_id: uuid.UUID, force_final: bool = False) -> None:
        async with session_maker() as db:
            request = await db.get(
                workflow_generation_service.WorkflowGenerationRequest, request_id
            )
            await workflow_generation_service.run_generation_round(
                db, request=request, settings=get_settings(), force_final=force_final
            )
            await db.commit()

    return _run


async def test_generate_with_no_questions_compiles_directly(
    client, run_pending_generation, planner_queue
):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    agent = await _create_agent(client, token, org_id)
    planner_queue.append(_simple_plan(agent["name"]))

    started = await client.post(
        "/api/v1/workflows/generate",
        json={"description": "Classify incoming tickets."},
        headers=_auth(token, org_id),
    )
    assert started.status_code == 202
    request_id = started.json()["id"]
    assert started.json()["status"] == "pending"

    await run_pending_generation(uuid.UUID(request_id))

    polled = (
        await client.get(f"/api/v1/workflows/generate/{request_id}", headers=_auth(token, org_id))
    ).json()
    assert polled["status"] == "ready"
    assert polled["plan"]["summary"] == "Classifies incoming tickets."

    compiled = await client.post(
        f"/api/v1/workflows/generate/{request_id}/compile", headers=_auth(token, org_id)
    )
    assert compiled.status_code == 200
    body = compiled.json()
    assert body["source"] == "generated"
    assert body["generation_request_id"] == request_id
    assert body["is_active"] is False  # never auto-activated

    final = (
        await client.get(f"/api/v1/workflows/generate/{request_id}", headers=_auth(token, org_id))
    ).json()
    assert final["status"] == "applied"


async def test_clarifying_questions_loop(client, run_pending_generation, planner_queue):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    agent = await _create_agent(client, token, org_id)
    planner_queue.append(
        {
            "summary": "",
            "nodes": [],
            "edges": [],
            "missing_components": [],
            "clarifying_questions": ["What triggers this — email or a schedule?"],
        }
    )
    planner_queue.append(_simple_plan(agent["name"]))

    started = await client.post(
        "/api/v1/workflows/generate",
        json={"description": "Classify tickets somehow."},
        headers=_auth(token, org_id),
    )
    request_id = started.json()["id"]
    await run_pending_generation(uuid.UUID(request_id))

    polled = (
        await client.get(f"/api/v1/workflows/generate/{request_id}", headers=_auth(token, org_id))
    ).json()
    assert polled["status"] == "awaiting_answers"
    assert polled["clarifying_questions"] == ["What triggers this — email or a schedule?"]

    answered = await client.post(
        f"/api/v1/workflows/generate/{request_id}/answer",
        json={"answer": "Email."},
        headers=_auth(token, org_id),
    )
    assert answered.status_code == 200

    await run_pending_generation(uuid.UUID(request_id))

    final = (
        await client.get(f"/api/v1/workflows/generate/{request_id}", headers=_auth(token, org_id))
    ).json()
    assert final["status"] == "ready"
    assert final["answers"] == ["Email."]


async def test_round_cap_forces_a_final_plan_even_if_model_keeps_asking(
    client, run_pending_generation, planner_queue
):
    """§16.7 — capped at 3 rounds. Even if the (fake, misbehaving) planner
    keeps returning clarifying_questions on round 3, the service must
    still land on `ready` rather than asking forever."""
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    agent = await _create_agent(client, token, org_id)
    for _ in range(2):
        planner_queue.append(
            {
                "summary": "",
                "nodes": [],
                "edges": [],
                "missing_components": [],
                "clarifying_questions": ["Still not sure — can you clarify?"],
            }
        )
    still_asking_but_forced = _simple_plan(agent["name"])
    still_asking_but_forced["clarifying_questions"] = ["I'm still unsure, but here's my best plan."]
    planner_queue.append(still_asking_but_forced)

    started = await client.post(
        "/api/v1/workflows/generate",
        json={"description": "Something vague."},
        headers=_auth(token, org_id),
    )
    request_id = started.json()["id"]

    await run_pending_generation(uuid.UUID(request_id))  # round 1 -> awaiting_answers
    await client.post(
        f"/api/v1/workflows/generate/{request_id}/answer",
        json={"answer": "still vague"},
        headers=_auth(token, org_id),
    )
    await run_pending_generation(uuid.UUID(request_id))  # round 2 -> awaiting_answers
    await client.post(
        f"/api/v1/workflows/generate/{request_id}/answer",
        json={"answer": "still vague"},
        headers=_auth(token, org_id),
    )
    await run_pending_generation(uuid.UUID(request_id))  # round 3 -> forced ready

    final = (
        await client.get(f"/api/v1/workflows/generate/{request_id}", headers=_auth(token, org_id))
    ).json()
    assert final["status"] == "ready"
    assert final["round"] == 3


async def test_missing_agent_reference_blocks_compile_until_created(
    client, run_pending_generation, planner_queue
):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    plan = _simple_plan("Nonexistent Agent")
    planner_queue.append(plan)

    started = await client.post(
        "/api/v1/workflows/generate",
        json={"description": "Do something with an agent that doesn't exist yet."},
        headers=_auth(token, org_id),
    )
    request_id = started.json()["id"]
    await run_pending_generation(uuid.UUID(request_id))

    blocked = await client.post(
        f"/api/v1/workflows/generate/{request_id}/compile", headers=_auth(token, org_id)
    )
    assert blocked.status_code == 400

    await _create_agent(client, token, org_id, name="Nonexistent Agent")

    compiled = await client.post(
        f"/api/v1/workflows/generate/{request_id}/compile", headers=_auth(token, org_id)
    )
    assert compiled.status_code == 200
    body = compiled.json()
    # A real created Workflow, not just a 200 — retrying compile on a
    # request that already has a plan (status="failed" from the earlier
    # attempt) must retry that SAME plan, not silently re-run the planner
    # and hand back a WorkflowGenerationRequestOut shape instead.
    assert body["source"] == "generated"
    assert "graph" in body


async def test_edit_with_nl_produces_diff_then_apply(client, run_pending_generation, planner_queue):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    agent = await _create_agent(client, token, org_id)

    workflow = (
        await client.post(
            "/api/v1/workflows",
            json={"name": "Original", "graph": _compiled_shape(_simple_plan(agent["name"]))},
            headers=_auth(token, org_id),
        )
    ).json()
    assert workflow["source"] == "manual"

    edited_plan = _simple_plan(agent["name"])
    edited_plan["nodes"].insert(
        2, {"ref": "k", "kind": "tool", "label": "log_activity", "tool_ref": "log_activity"}
    )
    edited_plan["edges"] = [
        {"source_ref": "t", "target_ref": "a"},
        {"source_ref": "a", "target_ref": "k"},
        {"source_ref": "k", "target_ref": "e"},
    ]
    edited_plan["summary"] = "Classifies incoming tickets and logs them."
    planner_queue.append(edited_plan)

    started = await client.post(
        f"/api/v1/workflows/{workflow['id']}/edit-with-nl",
        json={"instruction": "Also log every ticket."},
        headers=_auth(token, org_id),
    )
    assert started.status_code == 202
    request_id = started.json()["id"]

    await run_pending_generation(uuid.UUID(request_id))

    polled = (
        await client.get(f"/api/v1/workflows/generate/{request_id}", headers=_auth(token, org_id))
    ).json()
    assert polled["status"] == "ready"
    assert polled["diff"] is not None
    assert len(polled["diff"]["nodes_added"]) == 1
    assert polled["diff"]["nodes_added"][0]["data"]["label"] == "log_activity"

    applied = await client.post(
        f"/api/v1/workflows/edit-with-nl/{request_id}/apply", headers=_auth(token, org_id)
    )
    assert applied.status_code == 200
    body = applied.json()
    assert body["version"] == 2
    assert body["source"] == "hybrid"  # started manual, an AI edit touched it


async def test_reject_edit_leaves_workflow_untouched(client, run_pending_generation, planner_queue):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    agent = await _create_agent(client, token, org_id)

    workflow = (
        await client.post(
            "/api/v1/workflows",
            json={"name": "Original", "graph": _compiled_shape(_simple_plan(agent["name"]))},
            headers=_auth(token, org_id),
        )
    ).json()

    planner_queue.append(_simple_plan(agent["name"]))
    started = await client.post(
        f"/api/v1/workflows/{workflow['id']}/edit-with-nl",
        json={"instruction": "Change something."},
        headers=_auth(token, org_id),
    )
    request_id = started.json()["id"]
    await run_pending_generation(uuid.UUID(request_id))

    rejected = await client.post(
        f"/api/v1/workflows/edit-with-nl/{request_id}/reject",
        json={"reason": "not what I wanted"},
        headers=_auth(token, org_id),
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    unchanged = (
        await client.get(f"/api/v1/workflows/{workflow['id']}", headers=_auth(token, org_id))
    ).json()
    assert unchanged["version"] == 1
    assert unchanged["source"] == "manual"


async def test_generation_request_is_org_scoped(client, planner_queue):
    owner_token, owner_org = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    started = await client.post(
        "/api/v1/workflows/generate",
        json={"description": "x"},
        headers=_auth(owner_token, owner_org),
    )
    request_id = started.json()["id"]

    outsider_token, outsider_org = await _register_with_org(client, "sam@example.com", "Sam Rivera")
    response = await client.get(
        f"/api/v1/workflows/generate/{request_id}", headers=_auth(outsider_token, outsider_org)
    )
    assert response.status_code == 404


def _compiled_shape(plan: dict) -> dict:
    """A minimal hand-compiled graph matching `plan`'s shape, for tests
    that need a real starting Workflow without going through the
    generation pipeline first."""
    ref_to_id = {n["ref"]: str(uuid.uuid4()) for n in plan["nodes"]}
    nodes = [
        {
            "id": ref_to_id[n["ref"]],
            "type": n["kind"],
            "position": {"x": i * 200, "y": 0},
            "data": {
                "label": n["label"],
                **({"agentId": n.get("agent_ref")} if n["kind"] == "agent" else {}),
            },
        }
        for i, n in enumerate(plan["nodes"])
    ]
    edges = [
        {
            "id": f"e{i + 1}",
            "source": ref_to_id[e["source_ref"]],
            "target": ref_to_id[e["target_ref"]],
        }
        for i, e in enumerate(plan["edges"])
    ]
    return {"nodes": nodes, "edges": edges}
