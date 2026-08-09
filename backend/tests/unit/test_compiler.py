import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.schemas.agent import AgentCreate
from app.schemas.kb import KnowledgeBaseCreate
from app.schemas.workflow_generation import CompileError, PlanEdge, PlanNode, WorkflowPlan
from app.services import agent_service, kb_service, org_service
from app.workflow_generation.compiler import compile_plan_to_graph
from app.workflows.graph import WorkflowGraph, validate_graph


@pytest.fixture
async def seeded(db_engine):
    """A real org with one real agent and one real knowledge base — no
    LLM, no API layer, just the DB rows the compiler resolves refs
    against."""
    session_maker = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_maker() as db:
        org = await org_service.create_org(db, owner=await _make_user(db), name="Compiler Test Org")
        agent = await agent_service.create_agent(
            db,
            org_id=org.org.id,
            data=AgentCreate(
                name="Support Agent",
                description="Handles tickets",
                system_prompt="Classify the ticket. Return JSON: {category, amount}.",
                model_provider="ollama",
                model_name="llama3.1:8b",
                temperature=0.2,
                allowed_tools=[],
                memory_scope="none",
            ),
        )
        kb = await kb_service.create_kb(
            db, org_id=org.org.id, data=KnowledgeBaseCreate(name="Policies", description="")
        )
        await db.commit()
        return session_maker, org.org.id, agent, kb


async def _make_user(db):
    from app.services import auth_service

    user, _ = await auth_service.register_user(
        db,
        email=f"{uuid.uuid4()}@example.com",
        password="correcthorsebatterystaple",
        full_name="Compiler Tester",
    )
    return user


def _node(ref, kind, **kwargs):
    return PlanNode(ref=ref, kind=kind, label=kwargs.pop("label", ref), **kwargs)


async def test_simple_plan_compiles_to_a_valid_graph(seeded):
    session_maker, org_id, agent, _kb = seeded
    plan = WorkflowPlan(
        summary="A simple triage flow.",
        nodes=[
            _node("t", "trigger", trigger_type="manual"),
            _node("a", "agent", agent_ref=agent.name),
            _node("e", "end"),
        ],
        edges=[PlanEdge(source_ref="t", target_ref="a"), PlanEdge(source_ref="a", target_ref="e")],
    )

    async with session_maker() as db:
        graph = await compile_plan_to_graph(plan, org_id=org_id, db=db)

    assert len(graph["nodes"]) == 3
    assert len(graph["edges"]) == 2
    agent_node = next(n for n in graph["nodes"] if n["type"] == "agent")
    assert agent_node["data"]["agentId"] == str(agent.id)
    validate_graph(WorkflowGraph.model_validate(graph))  # no raise — real graph, real validator


async def test_missing_agent_reference_raises_compile_error(seeded):
    session_maker, org_id, _agent, _kb = seeded
    plan = WorkflowPlan(
        summary="x",
        nodes=[
            _node("t", "trigger"),
            _node("a", "agent", agent_ref="Nonexistent Agent"),
            _node("e", "end"),
        ],
        edges=[PlanEdge(source_ref="t", target_ref="a"), PlanEdge(source_ref="a", target_ref="e")],
    )

    async with session_maker() as db:
        with pytest.raises(CompileError, match="doesn't exist yet"):
            await compile_plan_to_graph(plan, org_id=org_id, db=db)


async def test_new_agent_draft_resolves_once_a_matching_agent_is_created(seeded):
    """A plan referencing a not-yet-created agent via new_agent fails to
    compile until an agent with that exact name is created — then it
    resolves exactly like agent_ref would, no special-casing needed."""
    session_maker, org_id, _agent, _kb = seeded
    plan = WorkflowPlan(
        summary="x",
        nodes=[
            _node("t", "trigger"),
            _node(
                "a",
                "agent",
                new_agent={
                    "name": "Freshly Drafted Agent",
                    "description": "d",
                    "system_prompt": "p",
                },
            ),
            _node("e", "end"),
        ],
        edges=[PlanEdge(source_ref="t", target_ref="a"), PlanEdge(source_ref="a", target_ref="e")],
    )

    async with session_maker() as db:
        with pytest.raises(CompileError):
            await compile_plan_to_graph(plan, org_id=org_id, db=db)

    async with session_maker() as db:
        await agent_service.create_agent(
            db,
            org_id=org_id,
            data=AgentCreate(
                name="Freshly Drafted Agent",
                description="d",
                system_prompt="p",
                model_provider="ollama",
                model_name="llama3.1:8b",
                temperature=0.2,
                allowed_tools=[],
                memory_scope="none",
            ),
        )
        await db.commit()

    async with session_maker() as db:
        graph = await compile_plan_to_graph(plan, org_id=org_id, db=db)
    agent_node = next(n for n in graph["nodes"] if n["type"] == "agent")
    assert agent_node["data"]["agentId"]


async def test_condition_expression_resolves_against_upstream_required_output_field(seeded):
    session_maker, org_id, agent, _kb = seeded
    plan = WorkflowPlan(
        summary="x",
        nodes=[
            _node("t", "trigger"),
            _node("a", "agent", agent_ref=agent.name, required_output_fields=["amount"]),
            _node(
                "c",
                "condition",
                condition_expression="amount > 500",
                condition_description="Is it over $500?",
            ),
            _node("e", "end"),
        ],
        edges=[
            PlanEdge(source_ref="t", target_ref="a"),
            PlanEdge(source_ref="a", target_ref="c"),
            PlanEdge(source_ref="c", target_ref="e", branch="yes"),
            PlanEdge(source_ref="c", target_ref="e", branch="no"),
        ],
    )

    async with session_maker() as db:
        graph = await compile_plan_to_graph(plan, org_id=org_id, db=db)

    cond_node = next(n for n in graph["nodes"] if n["type"] == "condition")
    agent_node = next(n for n in graph["nodes"] if n["type"] == "agent")
    assert cond_node["data"]["field"] == f"{agent_node['id']}.amount"
    assert cond_node["data"]["operator"] == "gt"
    assert cond_node["data"]["value"] == 500
    validate_graph(WorkflowGraph.model_validate(graph))


async def test_condition_referencing_undeclared_field_is_rejected(seeded):
    session_maker, org_id, agent, _kb = seeded
    plan = WorkflowPlan(
        summary="x",
        nodes=[
            _node("t", "trigger"),
            _node("a", "agent", agent_ref=agent.name),  # no required_output_fields
            _node("c", "condition", condition_expression="amount > 500"),
            _node("e", "end"),
        ],
        edges=[
            PlanEdge(source_ref="t", target_ref="a"),
            PlanEdge(source_ref="a", target_ref="c"),
            PlanEdge(source_ref="c", target_ref="e", branch="yes"),
        ],
    )

    async with session_maker() as db:
        with pytest.raises(CompileError, match="required_output_fields"):
            await compile_plan_to_graph(plan, org_id=org_id, db=db)


async def test_search_kb_tool_node_resolves_kb_and_uses_label_as_query(seeded):
    session_maker, org_id, _agent, kb = seeded
    plan = WorkflowPlan(
        summary="x",
        nodes=[
            _node("t", "trigger"),
            _node("k", "tool", tool_ref="search_kb", kb_ref=kb.name, label="Search refund policy"),
            _node("e", "end"),
        ],
        edges=[PlanEdge(source_ref="t", target_ref="k"), PlanEdge(source_ref="k", target_ref="e")],
    )

    async with session_maker() as db:
        graph = await compile_plan_to_graph(plan, org_id=org_id, db=db)

    tool_node = next(n for n in graph["nodes"] if n["type"] == "tool")
    assert tool_node["data"]["kbId"] == str(kb.id)
    assert tool_node["data"]["query"] == "Search refund policy"


async def test_search_kb_tool_node_without_kb_ref_is_rejected(seeded):
    session_maker, org_id, _agent, _kb = seeded
    plan = WorkflowPlan(
        summary="x",
        nodes=[
            _node("t", "trigger"),
            _node("k", "tool", tool_ref="search_kb"),
            _node("e", "end"),
        ],
        edges=[PlanEdge(source_ref="t", target_ref="k"), PlanEdge(source_ref="k", target_ref="e")],
    )

    async with session_maker() as db:
        with pytest.raises(CompileError, match="needs a kb_ref"):
            await compile_plan_to_graph(plan, org_id=org_id, db=db)


async def test_kb_ref_on_agent_node_is_rejected(seeded):
    """The 'implicit KB on agent' pattern the addendum describes was never
    actually built — only explicit search_kb tool nodes do real retrieval."""
    session_maker, org_id, agent, kb = seeded
    plan = WorkflowPlan(
        summary="x",
        nodes=[
            _node("t", "trigger"),
            _node("a", "agent", agent_ref=agent.name, kb_ref=kb.name),
            _node("e", "end"),
        ],
        edges=[PlanEdge(source_ref="t", target_ref="a"), PlanEdge(source_ref="a", target_ref="e")],
    )

    async with session_maker() as db:
        with pytest.raises(CompileError, match="explicit search_kb"):
            await compile_plan_to_graph(plan, org_id=org_id, db=db)


async def test_duplicate_refs_rejected(seeded):
    session_maker, org_id, _agent, _kb = seeded
    plan = WorkflowPlan(
        summary="x",
        nodes=[_node("t", "trigger"), _node("t", "end")],
        edges=[PlanEdge(source_ref="t", target_ref="t")],
    )

    async with session_maker() as db:
        with pytest.raises(CompileError, match="duplicate"):
            await compile_plan_to_graph(plan, org_id=org_id, db=db)


async def test_plan_with_open_clarifying_questions_cannot_compile(seeded):
    session_maker, org_id, _agent, _kb = seeded
    plan = WorkflowPlan(
        summary="x",
        nodes=[_node("t", "trigger"), _node("e", "end")],
        edges=[PlanEdge(source_ref="t", target_ref="e")],
        clarifying_questions=["What email address should this watch?"],
    )

    async with session_maker() as db:
        with pytest.raises(CompileError, match="clarifying questions"):
            await compile_plan_to_graph(plan, org_id=org_id, db=db)


async def test_layout_places_deeper_nodes_further_right(seeded):
    session_maker, org_id, agent, _kb = seeded
    plan = WorkflowPlan(
        summary="x",
        nodes=[
            _node("t", "trigger"),
            _node("a", "agent", agent_ref=agent.name),
            _node("e", "end"),
        ],
        edges=[PlanEdge(source_ref="t", target_ref="a"), PlanEdge(source_ref="a", target_ref="e")],
    )

    async with session_maker() as db:
        graph = await compile_plan_to_graph(plan, org_id=org_id, db=db)

    by_type = {n["type"]: n for n in graph["nodes"]}
    assert by_type["trigger"]["position"]["x"] < by_type["agent"]["position"]["x"]
    assert by_type["agent"]["position"]["x"] < by_type["end"]["position"]["x"]
