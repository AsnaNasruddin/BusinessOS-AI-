import uuid

from fastapi import APIRouter, HTTPException, status

from app.agents.runner import run_agent_test
from app.config import get_settings
from app.deps import CurrentOrg, DbSession
from app.llm.base import ProviderNotConfiguredError
from app.schemas.agent import (
    AgentCreate,
    AgentOut,
    AgentTestRequest,
    AgentTestResponse,
    AgentUpdate,
)
from app.services import agent_service

router = APIRouter()


async def _get_agent_or_404(db: DbSession, ctx: CurrentOrg, agent_id: uuid.UUID):
    agent = await agent_service.get_agent(db, org_id=ctx.org.id, agent_id=agent_id)
    if agent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found.")
    return agent


@router.get("", response_model=list[AgentOut])
async def list_agents(ctx: CurrentOrg, db: DbSession) -> list[AgentOut]:
    agents = await agent_service.list_agents(db, org_id=ctx.org.id)
    return [AgentOut.model_validate(a, from_attributes=True) for a in agents]


@router.post("", response_model=AgentOut, status_code=status.HTTP_201_CREATED)
async def create_agent(body: AgentCreate, ctx: CurrentOrg, db: DbSession) -> AgentOut:
    agent = await agent_service.create_agent(db, org_id=ctx.org.id, data=body)
    return AgentOut.model_validate(agent, from_attributes=True)


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(agent_id: uuid.UUID, ctx: CurrentOrg, db: DbSession) -> AgentOut:
    agent = await _get_agent_or_404(db, ctx, agent_id)
    return AgentOut.model_validate(agent, from_attributes=True)


@router.patch("/{agent_id}", response_model=AgentOut)
async def update_agent(
    agent_id: uuid.UUID, body: AgentUpdate, ctx: CurrentOrg, db: DbSession
) -> AgentOut:
    agent = await _get_agent_or_404(db, ctx, agent_id)
    agent = await agent_service.update_agent(db, agent=agent, data=body)
    return AgentOut.model_validate(agent, from_attributes=True)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: uuid.UUID, ctx: CurrentOrg, db: DbSession) -> None:
    agent = await _get_agent_or_404(db, ctx, agent_id)
    await agent_service.delete_agent(db, agent=agent)


@router.post("/{agent_id}/test", response_model=AgentTestResponse)
async def test_agent(agent_id: uuid.UUID, body: AgentTestRequest, ctx: CurrentOrg, db: DbSession):
    agent = await _get_agent_or_404(db, ctx, agent_id)
    try:
        response = await run_agent_test(agent, body.message, get_settings())
    except ProviderNotConfiguredError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    return AgentTestResponse(
        reply=response.content, model_provider=agent.model_provider, model_name=agent.model_name
    )
