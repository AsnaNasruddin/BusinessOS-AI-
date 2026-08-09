from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.workflows.graph import GraphNode
from app.workflows.nodes.base import StepResult


async def run(node: GraphNode, context: dict, db: AsyncSession, settings: Settings) -> StepResult:
    return StepResult(
        label=node.data.get("label", "End"),
        sub=node.data.get("sub", "end"),
        latency_ms=0,
        tokens_used=None,
        payload=None,
        note=None,
        output=None,
    )
