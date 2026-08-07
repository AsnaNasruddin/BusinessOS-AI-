import httpx

from app.llm.base import LLMMessage, LLMProvider, LLMResponse, ProviderNotConfiguredError


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    async def complete(
        self, messages: list[LLMMessage], *, model: str, temperature: float
    ) -> LLMResponse:
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "options": {"temperature": temperature},
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(f"{self._base_url}/api/chat", json=payload)
        except httpx.ConnectError as exc:
            raise ProviderNotConfiguredError(
                f"Can't reach Ollama at {self._base_url} — is it running?"
            ) from exc

        response.raise_for_status()
        data = response.json()
        tokens_used = data.get("prompt_eval_count", 0) + data.get("eval_count", 0) or None
        return LLMResponse(content=data["message"]["content"], model=model, tokens_used=tokens_used)
