"""A real, bounded tool-calling loop for agents whose `allowed_tools`
include read-only lookups the model needs before it can answer — Phase 7's
Workflow Planner is the first (only) caller. Distinct from
app.agents.runner.run_agent_test() (a single completion, still used for the
plain "test this agent" UI action, no tool use) and from
app.workflows.executor (which runs a whole GRAPH of nodes, not one agent's
own reasoning loop).

Two-phase by construction, not one unified loop — confirmed empirically
against a real Ollama model: asking for both `tools` and a structured
`response_format` in the same call biases the model to skip tools
entirely and try to satisfy the schema immediately. So:

  Phase A — tool-gathering: call with `tools` only, in a bounded loop,
  until the model stops requesting tool calls.
  Phase B — final answer: if the caller wants structured output, make one
  more call with `response_format` only (no tools) to get schema-
  conforming JSON out of whatever Phase A concluded.
"""

import json
import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database.models.agent import Agent
from app.llm.base import LLMMessage, LLMResponse
from app.llm.factory import get_llm_provider
from app.tools.builtins.callable_tools import CALLABLE_TOOLS

MAX_TOOL_ITERATIONS = 6


class AgentExecutionError(Exception):
    """The loop hit its iteration cap without a final answer, or the model
    called a tool that isn't in the agent's allowed_tools / doesn't exist
    in CALLABLE_TOOLS."""


@dataclass
class AgentRunResult:
    response: LLMResponse
    messages: list[LLMMessage] = field(default_factory=list)  # full transcript, for logging
    tool_calls_made: int = 0


async def run_agent(
    agent: Agent,
    message: str,
    *,
    org_id: uuid.UUID,
    db: AsyncSession,
    settings: Settings,
    response_format: dict | None = None,
) -> AgentRunResult:
    provider = get_llm_provider(agent.model_provider, settings)
    tool_specs = [CALLABLE_TOOLS[name][0] for name in agent.allowed_tools if name in CALLABLE_TOOLS]

    messages = [
        LLMMessage(role="system", content=agent.system_prompt),
        LLMMessage(role="user", content=message),
    ]

    tool_calls_made = 0
    response: LLMResponse | None = None

    for _ in range(MAX_TOOL_ITERATIONS):
        response = await provider.complete(
            messages, model=agent.model_name, temperature=agent.temperature, tools=tool_specs
        )
        if not response.tool_calls:
            break

        messages.append(
            LLMMessage(role="assistant", content=response.content, tool_calls=response.tool_calls)
        )
        for call in response.tool_calls:
            if call.name not in agent.allowed_tools or call.name not in CALLABLE_TOOLS:
                raise AgentExecutionError(
                    f"Agent {agent.name!r} tried to call {call.name!r}, which isn't in its "
                    "allowed_tools."
                )
            _, tool_fn = CALLABLE_TOOLS[call.name]
            result = await tool_fn(call.arguments, org_id=org_id, db=db)
            messages.append(
                LLMMessage(
                    role="tool",
                    name=call.name,
                    tool_call_id=call.id,
                    content=json.dumps(result, default=str),
                )
            )
            tool_calls_made += 1
    else:
        raise AgentExecutionError(
            f"Agent {agent.name!r} exceeded {MAX_TOOL_ITERATIONS} tool-calling iterations "
            "without reaching a final answer."
        )

    if response_format is not None:
        messages.append(
            LLMMessage(role="user", content="Now provide your final answer in the required format.")
        )
        response = await provider.complete(
            messages,
            model=agent.model_name,
            temperature=agent.temperature,
            response_format=response_format,
        )
        messages.append(LLMMessage(role="assistant", content=response.content))

    return AgentRunResult(response=response, messages=messages, tool_calls_made=tool_calls_made)
