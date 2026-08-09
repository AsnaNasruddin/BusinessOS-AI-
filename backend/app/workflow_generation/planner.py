"""§16.6 — the Workflow Planner Agent. An ordinary `Agent` row (seeded like
the demo org's other agents, see scripts/seed_dev_data.py) with
`allowed_tools = [list_agents, list_tools, list_knowledge_bases]` —
read-only, by construction (ADR security rule 5) — run through the same
real tool-calling loop (app.agents.executor) any tool-using agent would
use. Nothing bespoke to workflow generation lives in the execution path;
only the message-building below is specific to this feature.

Context is assembled fresh per call (§16.6 point 3) from the raw request
text plus the accumulated clarifying Q&A history — never a stale cached
agent/tool/KB list, which the executor's own tool-calling loop already
guarantees by querying live every time."""

import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.executor import run_agent
from app.config import Settings
from app.database.models.agent import Agent
from app.schemas.agent import AgentCreate
from app.schemas.workflow_generation import WorkflowPlan
from app.services import agent_service

PLANNER_AGENT_NAME = "Workflow Planner"
_PROMPT_PATH = Path(__file__).resolve().parent.parent / "agents" / "prompts" / "workflow_planner.md"


class PlannerNotSeededError(Exception):
    """No Workflow Planner agent exists for this org yet. Shouldn't normally
    happen — every org gets one via ensure_planner_agent() at registration
    time (see auth_service.register_user) — but kept as a distinct,
    gracefully-handled error rather than an assumption, since it's still
    reachable for orgs that existed before that was added."""


async def get_planner_agent(db: AsyncSession, *, org_id: uuid.UUID) -> Agent:
    result = await db.execute(
        select(Agent).where(Agent.org_id == org_id, Agent.name == PLANNER_AGENT_NAME)
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise PlannerNotSeededError(f"No {PLANNER_AGENT_NAME!r} agent exists for this org yet.")
    return agent


async def ensure_planner_agent(db: AsyncSession, *, org_id: uuid.UUID) -> Agent:
    """Idempotent: creates the org's Workflow Planner agent if it doesn't
    already have one. Called both at registration time (every new org needs
    this for the NL generator to work at all) and from the demo seed
    script, so there's exactly one place that knows how to build it."""
    try:
        return await get_planner_agent(db, org_id=org_id)
    except PlannerNotSeededError:
        pass

    return await agent_service.create_agent(
        db,
        org_id=org_id,
        data=AgentCreate(
            name=PLANNER_AGENT_NAME,
            description="Turns a plain-English request into a workflow plan.",
            system_prompt=_PROMPT_PATH.read_text(),
            model_provider="ollama",
            model_name="llama3.1:8b",
            temperature=0.2,
            allowed_tools=["list_agents", "list_tools", "list_knowledge_bases"],
            memory_scope="none",
        ),
    )


async def generate_plan(
    *,
    raw_text: str,
    clarifying_questions: list[str],
    answers: list[str],
    org_id: uuid.UUID,
    db: AsyncSession,
    settings: Settings,
    current_graph_summary: str | None = None,
) -> WorkflowPlan:
    agent = await get_planner_agent(db, org_id=org_id)
    message = _build_message(raw_text, clarifying_questions, answers, current_graph_summary)
    result = await run_agent(
        agent,
        message,
        org_id=org_id,
        db=db,
        settings=settings,
        response_format=WorkflowPlan.model_json_schema(),
    )
    return WorkflowPlan.model_validate_json(result.response.content)


def _build_message(
    raw_text: str,
    clarifying_questions: list[str],
    answers: list[str],
    current_graph_summary: str | None,
) -> str:
    parts = [f"Request: {raw_text}"]

    if current_graph_summary:
        parts.append(
            f"\nThe workflow being edited currently looks like this:\n{current_graph_summary}"
        )

    if clarifying_questions:
        parts.append("\nClarifying questions asked so far, and the user's answers:")
        for question, answer in zip(clarifying_questions, answers, strict=False):
            parts.append(f"- Q: {question}\n  A: {answer}")
        unanswered = clarifying_questions[len(answers) :]
        if unanswered:
            parts.append("\nStill unanswered:")
            for question in unanswered:
                parts.append(f"- {question}")

    return "\n".join(parts)
