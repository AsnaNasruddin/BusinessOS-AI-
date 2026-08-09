from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.llm.base import ProviderNotConfiguredError
from app.rag.embeddings import OllamaEmbeddingProvider


async def test_embed_returns_empty_list_for_empty_input():
    provider = OllamaEmbeddingProvider("http://localhost:11434", "nomic-embed-text")
    assert await provider.embed([]) == []


async def test_embed_parses_response():
    provider = OllamaEmbeddingProvider("http://localhost:11434", "nomic-embed-text")
    fake = httpx.Response(
        200,
        json={"embeddings": [[0.1, 0.2], [0.3, 0.4]]},
        request=httpx.Request("POST", "http://test"),
    )
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=fake)):
        result = await provider.embed(["a", "b"])
    assert result == [[0.1, 0.2], [0.3, 0.4]]


async def test_embed_unreachable_raises_not_configured():
    provider = OllamaEmbeddingProvider("http://localhost:11434", "nomic-embed-text")
    with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=httpx.ConnectError("refused"))):
        with pytest.raises(ProviderNotConfiguredError):
            await provider.embed(["a"])
