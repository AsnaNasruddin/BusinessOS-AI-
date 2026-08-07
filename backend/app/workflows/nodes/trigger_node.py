from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.workflows.graph import GraphNode
from app.workflows.nodes.base import StepResult


async def run(node: GraphNode, context: dict, db: AsyncSession, settings: Settings) -> StepResult:
    payload = context.get("trigger")
    return StepResult(
        label=node.data.get("label", "Trigger"),
        sub=node.data.get("sub", "trigger"),
        latency_ms=0,
        tokens_used=None,
        payload=payload,
        note=None,
        output=payload,
    )
