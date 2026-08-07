"""Runs a single Agent in isolation against one message — lets the UI's
"test this agent" action prove an agent's system prompt + model actually
work, without needing the workflow engine (Phase 4) underneath it. Tool use
and multi-turn memory aren't wired in yet; this is a single completion."""

from app.config import Settings
from app.database.models.agent import Agent
from app.llm.base import LLMMessage, LLMResponse
from app.llm.factory import get_llm_provider


async def run_agent_test(agent: Agent, message: str, settings: Settings) -> LLMResponse:
    provider = get_llm_provider(agent.model_provider, settings)
    messages = [
        LLMMessage(role="system", content=agent.system_prompt),
        LLMMessage(role="user", content=message),
    ]
    return await provider.complete(messages, model=agent.model_name, temperature=agent.temperature)
