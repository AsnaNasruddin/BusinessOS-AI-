"""Thin wrapper around chromadb's *sync* client, called via asyncio.to_thread
from app.rag.ingest/retrieve. Sync on purpose (not AsyncHttpClient): it lets
tests swap in chromadb.EphemeralClient() — a real in-process Chroma, no
server needed — for chromadb.HttpClient() without an async-only client gap,
same shape either way."""

import uuid

import chromadb
from chromadb.api import ClientAPI

from app.config import Settings


def get_chroma_client(settings: Settings) -> ClientAPI:
    return chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)


def _collection_name(kb_id: uuid.UUID) -> str:
    return f"kb_{kb_id}"


def _get_collection(client: ClientAPI, kb_id: uuid.UUID):
    # Cosine similarity so retrieval scores land in a readable ~0-1 range
    # (see app/rag/retrieve.py's `1 - distance`), instead of Chroma's
    # default squared-L2 distance.
    return client.get_or_create_collection(
        _collection_name(kb_id), metadata={"hnsw:space": "cosine"}
    )


def add_chunks(
    client: ClientAPI,
    kb_id: uuid.UUID,
    *,
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
) -> None:
    collection = _get_collection(client, kb_id)
    collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)


def query_collection(
    client: ClientAPI, kb_id: uuid.UUID, *, query_embedding: list[float], n_results: int
) -> dict:
    collection = _get_collection(client, kb_id)
    return collection.query(query_embeddings=[query_embedding], n_results=n_results)


def delete_document_chunks(client: ClientAPI, kb_id: uuid.UUID, *, document_id: uuid.UUID) -> None:
    collection = _get_collection(client, kb_id)
    collection.delete(where={"document_id": str(document_id)})
