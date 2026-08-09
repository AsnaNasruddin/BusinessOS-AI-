"""Read-only tool the Workflow Planner (Phase 7) calls to see what
knowledge bases already exist in the org, to decide whether an agent node
should have one attached (§16.18's implicit-KB-on-agent judgment call)."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.base import ToolSpec
from app.services import kb_service

SPEC = ToolSpec(
    name="list_knowledge_bases",
    description=(
        "Lists this organization's existing knowledge bases (name, description) — "
        "call this before proposing a new one."
    ),
    parameters={"type": "object", "properties": {}, "required": []},
)


async def run(arguments: dict, *, org_id: uuid.UUID, db: AsyncSession) -> list[dict]:
    kbs = await kb_service.list_kbs(db, org_id=org_id)
    return [{"name": kb.name, "description": kb.description} for kb, _doc_count in kbs]
