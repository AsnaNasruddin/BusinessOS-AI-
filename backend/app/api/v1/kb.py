import asyncio
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.config import get_settings
from app.database.models.kb import KnowledgeBase
from app.deps import CurrentOrg, DbSession
from app.llm.base import ProviderNotConfiguredError
from app.rag import vectorstore
from app.rag.ingest import ingest_document
from app.rag.retrieve import retrieve as retrieve_chunks
from app.schemas.kb import (
    DocumentOut,
    KnowledgeBaseCreate,
    KnowledgeBaseOut,
    RetrievalQuery,
    RetrievedChunkOut,
)
from app.services import kb_service

router = APIRouter()

# Only plain-text formats are parsed for now — PDF/DOCX need a real parser
# (pypdf/python-docx), deliberately out of scope until something needs it.
_TEXT_EXTENSIONS = {
    ".md": "Markdown",
    ".txt": "Text",
    ".html": "HTML",
    ".htm": "HTML",
}


def _kb_out(kb: KnowledgeBase, document_count: int) -> KnowledgeBaseOut:
    return KnowledgeBaseOut(
        id=kb.id,
        org_id=kb.org_id,
        name=kb.name,
        description=kb.description,
        document_count=document_count,
        created_at=kb.created_at,
    )


async def _get_kb_or_404(db: DbSession, ctx: CurrentOrg, kb_id: uuid.UUID) -> KnowledgeBase:
    kb = await kb_service.get_kb(db, org_id=ctx.org.id, kb_id=kb_id)
    if kb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Knowledge base not found.")
    return kb


@router.get("", response_model=list[KnowledgeBaseOut])
async def list_kbs(ctx: CurrentOrg, db: DbSession) -> list[KnowledgeBaseOut]:
    rows = await kb_service.list_kbs(db, org_id=ctx.org.id)
    return [_kb_out(kb, count) for kb, count in rows]


@router.post("", response_model=KnowledgeBaseOut, status_code=status.HTTP_201_CREATED)
async def create_kb(body: KnowledgeBaseCreate, ctx: CurrentOrg, db: DbSession) -> KnowledgeBaseOut:
    kb = await kb_service.create_kb(db, org_id=ctx.org.id, data=body)
    return _kb_out(kb, 0)


@router.get("/{kb_id}", response_model=KnowledgeBaseOut)
async def get_kb(kb_id: uuid.UUID, ctx: CurrentOrg, db: DbSession) -> KnowledgeBaseOut:
    kb = await _get_kb_or_404(db, ctx, kb_id)
    count = await kb_service.count_documents(db, kb_id=kb.id)
    return _kb_out(kb, count)


@router.get("/{kb_id}/documents", response_model=list[DocumentOut])
async def list_documents(kb_id: uuid.UUID, ctx: CurrentOrg, db: DbSession) -> list[DocumentOut]:
    await _get_kb_or_404(db, ctx, kb_id)
    documents = await kb_service.list_documents(db, kb_id=kb_id)
    return [DocumentOut.model_validate(d, from_attributes=True) for d in documents]


@router.post("/{kb_id}/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    kb_id: uuid.UUID,
    ctx: CurrentOrg,
    db: DbSession,
    file: Annotated[UploadFile, File()],
) -> DocumentOut:
    kb = await _get_kb_or_404(db, ctx, kb_id)

    extension = Path(file.filename or "").suffix.lower()
    if extension not in _TEXT_EXTENSIONS:
        supported = ", ".join(sorted(_TEXT_EXTENSIONS))
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unsupported file type {extension!r}. Supported: {supported}.",
        )

    raw = await file.read()
    text = raw.decode("utf-8", errors="replace")

    document = await kb_service.create_document(
        db,
        kb_id=kb.id,
        filename=file.filename or "untitled",
        mime_type=_TEXT_EXTENSIONS[extension],
        size_bytes=len(raw),
    )

    try:
        chunk_count = await ingest_document(
            kb_id=kb.id,
            document_id=document.id,
            filename=document.filename,
            text=text,
            settings=get_settings(),
        )
    except ProviderNotConfiguredError as exc:
        document = await kb_service.mark_document_failed(db, document=document, error=str(exc))
        return DocumentOut.model_validate(document, from_attributes=True)

    document = await kb_service.mark_document_ready(db, document=document, chunk_count=chunk_count)
    return DocumentOut.model_validate(document, from_attributes=True)


@router.delete("/{kb_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    kb_id: uuid.UUID, document_id: uuid.UUID, ctx: CurrentOrg, db: DbSession
) -> None:
    kb = await _get_kb_or_404(db, ctx, kb_id)
    document = await kb_service.get_document(db, kb_id=kb.id, document_id=document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")

    client = vectorstore.get_chroma_client(get_settings())
    await asyncio.to_thread(
        vectorstore.delete_document_chunks, client, kb.id, document_id=document.id
    )
    await kb_service.delete_document(db, document=document)


@router.post("/{kb_id}/query", response_model=list[RetrievedChunkOut])
async def query_kb(
    kb_id: uuid.UUID, body: RetrievalQuery, ctx: CurrentOrg, db: DbSession
) -> list[RetrievedChunkOut]:
    await _get_kb_or_404(db, ctx, kb_id)
    try:
        chunks = await retrieve_chunks(
            kb_id=kb_id, query=body.query, k=body.k, settings=get_settings()
        )
    except ProviderNotConfiguredError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    return [
        RetrievedChunkOut(source=c.source, chunk_index=c.chunk_index, score=c.score, text=c.text)
        for c in chunks
    ]
