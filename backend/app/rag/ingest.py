"""The real ingestion pipeline: parse -> chunk -> embed -> store (Module 6).
scripts/seed_dev_data.py runs seed-data/knowledge-base/ through this exact
path rather than hand-writing fake chunk rows."""

import asyncio
import uuid

from app.config import Settings
from app.rag import vectorstore
from app.rag.chunker import chunk_text
from app.rag.embeddings import OllamaEmbeddingProvider


async def ingest_document(
    *,
    kb_id: uuid.UUID,
    document_id: uuid.UUID,
    filename: str,
    text: str,
    settings: Settings,
    chroma_client: object | None = None,
) -> int:
    """Chunks, embeds, and stores a document's text in Chroma. Returns the
    chunk count — the caller (kb_service) owns updating the Document row's
    status/chunk_count from that. `chroma_client` is overridable for tests
    (an EphemeralClient instead of the real HttpClient)."""
    chunks = chunk_text(text)
    if not chunks:
        return 0

    embedder = OllamaEmbeddingProvider(settings.ollama_base_url, settings.embedding_model)
    embeddings = await embedder.embed(chunks)

    client = chroma_client if chroma_client is not None else vectorstore.get_chroma_client(settings)
    ids = [f"{document_id}-{i}" for i in range(len(chunks))]
    metadatas = [
        {"document_id": str(document_id), "filename": filename, "chunk_index": i}
        for i in range(len(chunks))
    ]
    await asyncio.to_thread(
        vectorstore.add_chunks,
        client,
        kb_id,
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )
    return len(chunks)
