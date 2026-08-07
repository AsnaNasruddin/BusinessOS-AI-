import json
import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runner import run_agent_test
from app.config import Settings
from app.database.models.agent import Agent
from app.workflows.graph import GraphNode
from app.workflows.nodes.base import StepResult, WorkflowExecutionError


async def run(node: GraphNode, context: dict, db: AsyncSession, settings: Settings) -> StepResult:
    agent_id = node.data.get("agentId")
    if not agent_id:
        raise WorkflowExecutionError(f"Agent node {node.id!r} is missing an agentId.")

    agent = await db.get(Agent, uuid.UUID(agent_id))
    if agent is None:
        raise WorkflowExecutionError(
            f"Agent node {node.id!r} references an agent that no longer exists."
        )

    message = _build_message(context)
    start = time.monotonic()
    response = await run_agent_test(agent, message, settings)
    latency_ms = int((time.monotonic() - start) * 1000)

    return StepResult(
        label=agent.name,
        sub=f"agent · {agent.model_provider}/{agent.model_name}",
        latency_ms=latency_ms,
        tokens_used=response.tokens_used,
        payload={"reply": response.content},
        note=None,
        output=response.content,
    )


def _build_message(context: dict) -> str:
    """v0 gives every agent node the full context accumulated so far (the
    trigger payload plus prior nodes' outputs) rather than hand-wiring which
    upstream fields feed which node — simple, and sufficient for a linear
    chain where every node runs unconditionally in order anyway."""
    return "Workflow context so far:\n" + json.dumps(context, indent=2, default=str)
