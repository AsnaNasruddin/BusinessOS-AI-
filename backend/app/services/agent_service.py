"""Business logic for Module 5 (AI Agents) — CRUD only. Running an agent
lives in app.agents.runner; the LLM abstraction lives in app.llm."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Agent
from app.schemas.agent import AgentCreate, AgentUpdate
from app.utils.db import scoped_query


async def create_agent(db: AsyncSession, *, org_id: uuid.UUID, data: AgentCreate) -> Agent:
    agent = Agent(org_id=org_id, **data.model_dump())
    db.add(agent)
    await db.flush()
    return agent


async def list_agents(db: AsyncSession, *, org_id: uuid.UUID) -> list[Agent]:
    result = await db.execute(scoped_query(Agent, org_id))
    return list(result.scalars().all())


async def get_agent(db: AsyncSession, *, org_id: uuid.UUID, agent_id: uuid.UUID) -> Agent | None:
    result = await db.execute(scoped_query(Agent, org_id).where(Agent.id == agent_id))
    return result.scalar_one_or_none()


async def update_agent(db: AsyncSession, *, agent: Agent, data: AgentUpdate) -> Agent:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(agent, field, value)
    await db.flush()
    # `updated_at` is server-side (onupdate=func.now()) — refresh so the
    # in-memory object reflects it instead of triggering a lazy load once
    # we're back outside the async context (during response serialization).
    await db.refresh(agent)
    return agent


async def delete_agent(db: AsyncSession, *, agent: Agent) -> None:
    await db.delete(agent)
    await db.flush()
