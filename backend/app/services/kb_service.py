"""Business logic for Module 6 (Knowledge Base / RAG) — Postgres metadata
only. Chunk text/embeddings live in Chroma; see app.rag."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import KbDocument, KnowledgeBase
from app.schemas.kb import KnowledgeBaseCreate
from app.utils.db import scoped_query


async def create_kb(
    db: AsyncSession, *, org_id: uuid.UUID, data: KnowledgeBaseCreate
) -> KnowledgeBase:
    kb = KnowledgeBase(org_id=org_id, **data.model_dump())
    db.add(kb)
    await db.flush()
    return kb


async def list_kbs(db: AsyncSession, *, org_id: uuid.UUID) -> list[tuple[KnowledgeBase, int]]:
    result = await db.execute(
        select(KnowledgeBase, func.count(KbDocument.id))
        .outerjoin(KbDocument, KbDocument.kb_id == KnowledgeBase.id)
        .where(KnowledgeBase.org_id == org_id)
        .group_by(KnowledgeBase.id)
    )
    return list(result.all())


async def get_kb(db: AsyncSession, *, org_id: uuid.UUID, kb_id: uuid.UUID) -> KnowledgeBase | None:
    result = await db.execute(scoped_query(KnowledgeBase, org_id).where(KnowledgeBase.id == kb_id))
    return result.scalar_one_or_none()


async def count_documents(db: AsyncSession, *, kb_id: uuid.UUID) -> int:
    result = await db.execute(select(func.count(KbDocument.id)).where(KbDocument.kb_id == kb_id))
    return result.scalar_one()


async def create_document(
    db: AsyncSession, *, kb_id: uuid.UUID, filename: str, mime_type: str, size_bytes: int
) -> KbDocument:
    document = KbDocument(
        kb_id=kb_id,
        filename=filename,
        mime_type=mime_type,
        size_bytes=size_bytes,
        status="processing",
    )
    db.add(document)
    await db.flush()
    return document


async def mark_document_ready(
    db: AsyncSession, *, document: KbDocument, chunk_count: int
) -> KbDocument:
    document.status = "ready"
    document.chunk_count = chunk_count
    await db.flush()
    await db.refresh(document)
    return document


async def mark_document_failed(db: AsyncSession, *, document: KbDocument, error: str) -> KbDocument:
    document.status = "failed"
    document.error_message = error
    await db.flush()
    await db.refresh(document)
    return document


async def list_documents(db: AsyncSession, *, kb_id: uuid.UUID) -> list[KbDocument]:
    result = await db.execute(select(KbDocument).where(KbDocument.kb_id == kb_id))
    return list(result.scalars().all())


async def get_document(
    db: AsyncSession, *, kb_id: uuid.UUID, document_id: uuid.UUID
) -> KbDocument | None:
    result = await db.execute(
        select(KbDocument).where(KbDocument.kb_id == kb_id, KbDocument.id == document_id)
    )
    return result.scalar_one_or_none()


async def delete_document(db: AsyncSession, *, document: KbDocument) -> None:
    await db.delete(document)
    await db.flush()
