import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

DocumentStatus = Literal["pending", "processing", "ready", "failed"]


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""


class KnowledgeBaseOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    description: str
    document_count: int
    created_at: datetime


class DocumentOut(BaseModel):
    id: uuid.UUID
    kb_id: uuid.UUID
    filename: str
    mime_type: str
    size_bytes: int
    status: DocumentStatus
    chunk_count: int | None
    error_message: str | None
    created_at: datetime


class RetrievalQuery(BaseModel):
    query: str = Field(min_length=1)
    k: int = Field(default=5, ge=1, le=20)


class RetrievedChunkOut(BaseModel):
    source: str
    chunk_index: int
    score: float
    text: str
