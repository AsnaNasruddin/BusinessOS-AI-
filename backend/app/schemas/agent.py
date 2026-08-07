import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ModelProvider = Literal["ollama", "anthropic", "openai", "groq"]
MemoryScope = Literal["none", "session", "persistent"]


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    system_prompt: str = Field(min_length=1)
    model_provider: ModelProvider = "ollama"
    model_name: str = Field(min_length=1)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    allowed_tools: list[str] = Field(default_factory=list)
    memory_scope: MemoryScope = "none"


class AgentUpdate(BaseModel):
    """All fields optional — a PATCH only touches what's provided."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    system_prompt: str | None = Field(default=None, min_length=1)
    model_provider: ModelProvider | None = None
    model_name: str | None = Field(default=None, min_length=1)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    allowed_tools: list[str] | None = None
    memory_scope: MemoryScope | None = None


class AgentOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    description: str
    system_prompt: str
    model_provider: str
    model_name: str
    temperature: float
    allowed_tools: list[str]
    memory_scope: str
    created_at: datetime
    updated_at: datetime


class ToolOut(BaseModel):
    id: str
    name: str
    display_name: str
    description: str
    category: str


class AgentTestRequest(BaseModel):
    message: str = Field(min_length=1)


class AgentTestResponse(BaseModel):
    reply: str
    model_provider: str
    model_name: str
