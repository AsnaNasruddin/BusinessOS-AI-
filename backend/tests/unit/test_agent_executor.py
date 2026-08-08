import uuid
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.agents.executor import MAX_TOOL_ITERATIONS, AgentExecutionError, run_agent
from app.config import get_settings
from app.database.models.agent import Agent
from app.llm.base import LLMResponse, ToolCall
from app.llm.ollama_provider import OllamaProvider


def _agent(**overrides) -> Agent:
    defaults = dict(
        org_id=uuid.uuid4(),
        name="Test Agent",
        description="d",
        system_prompt="You are a test agent.",
        model_provider="ollama",
        model_name="llama3.1:8b",
        temperature=0.2,
        allowed_tools=[],
        memory_scope="none",
    )
    defaults.update(overrides)
    return Agent(**defaults)


async def test_returns_final_answer_directly_when_no_tools_are_called():
    async def fake_complete(self, messages, **kwargs):
        return LLMResponse(content="all done", model=kwargs["model"], tokens_used=10)

    with patch.object(OllamaProvider, "complete", new=fake_complete):
        result = await run_agent(
            _agent(), "hello", org_id=uuid.uuid4(), db=None, settings=get_settings()
        )

    assert result.response.content == "all done"
    assert result.tool_calls_made == 0


async def test_calls_an_allowed_tool_and_feeds_the_result_back(db_engine):
    from app.database.models import Organization

    session_maker = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_maker() as db:
        org = Organization(name="Executor Test Org", slug="executor-test-org")
        db.add(org)
        await db.flush()
        await db.commit()
        org_id = org.id

    call_log = []

    async def fake_complete(self, messages, **kwargs):
        model = kwargs["model"]
        if not call_log:
            call_log.append("tool_call")
            return LLMResponse(
                content="",
                model=model,
                tool_calls=[ToolCall(id="call_0", name="list_tools", arguments={})],
            )
        call_log.append("final")
        return LLMResponse(content="Here are the tools.", model=model, tokens_used=8)

    agent = _agent(allowed_tools=["list_tools"])
    async with session_maker() as db:
        with patch.object(OllamaProvider, "complete", new=fake_complete):
            result = await run_agent(
                agent, "what tools exist?", org_id=org_id, db=db, settings=get_settings()
            )

    assert call_log == ["tool_call", "final"]
    assert result.tool_calls_made == 1
    assert result.response.content == "Here are the tools."
    tool_messages = [m for m in result.messages if m.role == "tool"]
    assert len(tool_messages) == 1
    assert tool_messages[0].name == "list_tools"


async def test_rejects_a_tool_call_outside_allowed_tools():
    async def fake_complete(self, messages, **kwargs):
        return LLMResponse(
            content="",
            model=kwargs["model"],
            tool_calls=[ToolCall(id="call_0", name="list_agents", arguments={})],
        )

    agent = _agent(allowed_tools=[])  # list_agents NOT allowed
    with patch.object(OllamaProvider, "complete", new=fake_complete):
        with pytest.raises(AgentExecutionError, match="allowed_tools"):
            await run_agent(agent, "x", org_id=uuid.uuid4(), db=None, settings=get_settings())


async def test_raises_after_exceeding_max_tool_iterations():
    async def fake_complete(self, messages, **kwargs):
        # Always wants another tool call — never settles on a final answer.
        return LLMResponse(
            content="",
            model=kwargs["model"],
            tool_calls=[ToolCall(id="call_0", name="list_tools", arguments={})],
        )

    agent = _agent(allowed_tools=["list_tools"])
    with patch.object(OllamaProvider, "complete", new=fake_complete):
        with pytest.raises(AgentExecutionError, match=str(MAX_TOOL_ITERATIONS)):
            await run_agent(agent, "x", org_id=uuid.uuid4(), db=None, settings=get_settings())


async def test_response_format_triggers_one_final_constrained_call():
    calls = []

    async def fake_complete(self, messages, **kwargs):
        calls.append(
            {"tools": kwargs.get("tools"), "response_format": kwargs.get("response_format")}
        )
        if kwargs.get("response_format") is None:
            return LLMResponse(content="thinking out loud", model=kwargs["model"])
        return LLMResponse(content='{"ok": true}', model=kwargs["model"])

    agent = _agent(allowed_tools=[])
    with patch.object(OllamaProvider, "complete", new=fake_complete):
        result = await run_agent(
            agent,
            "x",
            org_id=uuid.uuid4(),
            db=None,
            settings=get_settings(),
            response_format={"type": "object"},
        )

    assert result.response.content == '{"ok": true}'
    # Phase A (tool-gathering) call had no response_format; Phase B (final) had no tools.
    assert calls[0]["response_format"] is None
    assert calls[-1]["response_format"] == {"type": "object"}
    assert not calls[-1]["tools"]
