"""Embeddings, kept separate from app.llm — a different concern (vectors,
not chat completions) even though today it's the same Ollama server. Only
one provider for now (no ABC/factory) since nothing else needs swapping in
yet — mirror app.llm's provider-interface pattern here if that changes."""

import httpx

from app.llm.base import ProviderNotConfiguredError


class OllamaEmbeddingProvider:
    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url
        self._model = model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self._base_url}/api/embed",
                    json={"model": self._model, "input": texts},
                )
        except httpx.ConnectError as exc:
            raise ProviderNotConfiguredError(
                f"Can't reach Ollama at {self._base_url} — is it running?"
            ) from exc

        response.raise_for_status()
        return response.json()["embeddings"]
