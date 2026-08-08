"""Read-only tool the Workflow Planner (Phase 7) calls to see what built-in
tools exist, so a `tool` node it drafts references something real instead
of an invented integration."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.base import ToolSpec
from app.tools.builtins.registry import list_tools as list_builtin_tools

SPEC = ToolSpec(
    name="list_tools",
    description=(
        "Lists the built-in tools available to wire into a workflow (e.g. "
        "search_kb, send_email)."
    ),
    parameters={"type": "object", "properties": {}, "required": []},
)


async def run(arguments: dict, *, org_id: uuid.UUID, db: AsyncSession) -> list[dict]:
    return [
        {"name": t.name, "description": t.description, "category": t.category}
        for t in list_builtin_tools()
    ]
