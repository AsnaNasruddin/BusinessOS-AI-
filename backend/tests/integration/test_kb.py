import chromadb
import pytest

from app.rag import vectorstore
from app.rag.embeddings import OllamaEmbeddingProvider


def _fake_embed_vector(text: str) -> list[float]:
    h = hash(text)
    return [((h >> (8 * i)) & 0xFF) / 255.0 for i in range(8)]


@pytest.fixture(autouse=True)
def isolated_rag_backends(monkeypatch):
    """KB tests must not depend on a real Chroma server or a real Ollama
    embedding model — an in-process EphemeralClient + a deterministic fake
    embedder keep these hermetic, same spirit as the in-memory SQLite DB
    used for Postgres elsewhere in this suite."""
    chroma_client = chromadb.EphemeralClient()
    monkeypatch.setattr(vectorstore, "get_chroma_client", lambda settings: chroma_client)

    async def fake_embed(self, texts):
        return [_fake_embed_vector(t) for t in texts]

    monkeypatch.setattr(OllamaEmbeddingProvider, "embed", fake_embed)


async def _register_with_org(client, email, full_name):
    register = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correcthorsebatterystaple", "full_name": full_name},
    )
    token = register.json()["access_token"]
    orgs = (await client.get("/api/v1/orgs", headers=_auth(token))).json()
    return token, orgs[0]["id"]


def _auth(token, org_id=None):
    headers = {"Authorization": f"Bearer {token}"}
    if org_id:
        headers["X-Org-Id"] = org_id
    return headers


async def test_create_and_list_kb(client):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    created = await client.post(
        "/api/v1/kbs",
        json={"name": "Policy & Refunds", "description": "Returns policy."},
        headers=_auth(token, org_id),
    )
    assert created.status_code == 201
    assert created.json()["document_count"] == 0

    listed = await client.get("/api/v1/kbs", headers=_auth(token, org_id))
    assert listed.status_code == 200
    assert len(listed.json()) == 1


async def test_upload_document_gets_chunked_and_marked_ready(client):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    kb = (
        await client.post(
            "/api/v1/kbs", json={"name": "Policy & Refunds"}, headers=_auth(token, org_id)
        )
    ).json()

    text = "Refunds are available within 30 days. " * 200
    files = {"file": ("Returns-Policy.md", text.encode(), "text/markdown")}
    uploaded = await client.post(
        f"/api/v1/kbs/{kb['id']}/documents", files=files, headers=_auth(token, org_id)
    )
    assert uploaded.status_code == 201
    body = uploaded.json()
    assert body["status"] == "ready"
    assert body["chunk_count"] > 1

    kb_detail = (await client.get(f"/api/v1/kbs/{kb['id']}", headers=_auth(token, org_id))).json()
    assert kb_detail["document_count"] == 1


async def test_upload_unsupported_file_type_is_rejected(client):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    kb = (
        await client.post(
            "/api/v1/kbs", json={"name": "Product Docs"}, headers=_auth(token, org_id)
        )
    ).json()

    files = {"file": ("Manual.pdf", b"%PDF-1.4 fake", "application/pdf")}
    response = await client.post(
        f"/api/v1/kbs/{kb['id']}/documents", files=files, headers=_auth(token, org_id)
    )
    assert response.status_code == 400


async def test_query_kb_returns_ingested_chunks(client):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    kb = (
        await client.post(
            "/api/v1/kbs", json={"name": "Policy & Refunds"}, headers=_auth(token, org_id)
        )
    ).json()

    text = "Damaged items are refunded within 30 days of delivery, no return shipping required."
    files = {"file": ("Returns-Policy.md", text.encode(), "text/markdown")}
    await client.post(
        f"/api/v1/kbs/{kb['id']}/documents", files=files, headers=_auth(token, org_id)
    )

    response = await client.post(
        f"/api/v1/kbs/{kb['id']}/query",
        json={"query": "damaged item refund window", "k": 5},
        headers=_auth(token, org_id),
    )
    assert response.status_code == 200
    chunks = response.json()
    assert len(chunks) == 1
    assert chunks[0]["source"] == "Returns-Policy.md"
    assert "damaged" in chunks[0]["text"].lower()


async def test_delete_document_removes_it(client):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    kb = (
        await client.post(
            "/api/v1/kbs", json={"name": "Policy & Refunds"}, headers=_auth(token, org_id)
        )
    ).json()
    files = {"file": ("Returns-Policy.md", b"Some policy text.", "text/markdown")}
    doc = (
        await client.post(
            f"/api/v1/kbs/{kb['id']}/documents", files=files, headers=_auth(token, org_id)
        )
    ).json()

    deleted = await client.delete(
        f"/api/v1/kbs/{kb['id']}/documents/{doc['id']}", headers=_auth(token, org_id)
    )
    assert deleted.status_code == 204

    documents = (
        await client.get(f"/api/v1/kbs/{kb['id']}/documents", headers=_auth(token, org_id))
    ).json()
    assert documents == []


async def test_kb_from_other_org_is_not_visible(client):
    owner_token, owner_org = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    kb = (
        await client.post(
            "/api/v1/kbs", json={"name": "Policy & Refunds"}, headers=_auth(owner_token, owner_org)
        )
    ).json()

    outsider_token, outsider_org = await _register_with_org(
        client, "outsider@example.com", "Sam Rivera"
    )
    response = await client.get(
        f"/api/v1/kbs/{kb['id']}", headers=_auth(outsider_token, outsider_org)
    )
    assert response.status_code == 404
