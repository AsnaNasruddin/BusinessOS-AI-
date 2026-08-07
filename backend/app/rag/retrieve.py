import asyncio
import uuid
from dataclasses import dataclass

from app.config import Settings
from app.rag import vectorstore
from app.rag.embeddings import OllamaEmbeddingProvider


@dataclass
class RetrievedChunk:
    source: str
    chunk_index: int
    score: float
    text: str


async def retrieve(
    *,
    kb_id: uuid.UUID,
    query: str,
    k: int,
    settings: Settings,
    chroma_client: object | None = None,
) -> list[RetrievedChunk]:
    embedder = OllamaEmbeddingProvider(settings.ollama_base_url, settings.embedding_model)
    [query_embedding] = await embedder.embed([query])

    client = chroma_client if chroma_client is not None else vectorstore.get_chroma_client(settings)
    result = await asyncio.to_thread(
        vectorstore.query_collection, client, kb_id, query_embedding=query_embedding, n_results=k
    )

    documents = result["documents"][0] if result["documents"] else []
    metadatas = result["metadatas"][0] if result["metadatas"] else []
    distances = result["distances"][0] if result["distances"] else []

    return [
        RetrievedChunk(
            source=meta["filename"],
            chunk_index=meta["chunk_index"],
            score=1 - distance,
            text=doc,
        )
        for doc, meta, distance in zip(documents, metadatas, distances, strict=True)
    ]
