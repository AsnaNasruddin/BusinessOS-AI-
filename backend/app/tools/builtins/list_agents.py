"""Read-only tool the Workflow Planner (Phase 7) calls to see what agents
already exist in the org, so it can propose reusing one instead of
drafting a duplicate — the actual point of giving it tool access at all
(see the ADR's alternatives table)."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.base import ToolSpec
from app.services import agent_service

SPEC = ToolSpec(
    name="list_agents",
    description=(
        "Lists this organization's existing AI agents (name, description, allowed "
        "tools) — call this before drafting a new agent, to check whether an "
        "existing one already fits."
    ),
    parameters={"type": "object", "properties": {}, "required": []},
)


async def run(arguments: dict, *, org_id: uuid.UUID, db: AsyncSession) -> list[dict]:
    agents = await agent_service.list_agents(db, org_id=org_id)
    return [
        {"name": a.name, "description": a.description, "allowed_tools": a.allowed_tools}
        for a in agents
    ]
