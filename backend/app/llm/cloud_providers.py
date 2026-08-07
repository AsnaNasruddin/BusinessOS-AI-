"""Cloud providers, called directly over HTTPS rather than pulling in each
vendor's SDK — one extra dependency per provider isn't worth it for a
handful of REST calls, and it keeps every provider in this package the same
shape (plain httpx, like ollama_provider.py)."""

import httpx

from app.llm.base import LLMMessage, LLMProvider, LLMResponse, ProviderNotConfiguredError


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key

    async def complete(
        self, messages: list[LLMMessage], *, model: str, temperature: float
    ) -> LLMResponse:
        if not self._api_key:
            raise ProviderNotConfiguredError("ANTHROPIC_API_KEY is not set.")

        system = "\n".join(m.content for m in messages if m.role == "system") or None
        turns = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 1024,
                    "temperature": temperature,
                    "system": system,
                    "messages": turns,
                },
            )
        response.raise_for_status()
        data = response.json()
        return LLMResponse(content=data["content"][0]["text"], model=model)


class _OpenAICompatibleProvider(LLMProvider):
    """OpenAI and Groq both speak the same `/chat/completions` shape."""

    _base_url: str
    _env_key_name: str

    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key

    async def complete(
        self, messages: list[LLMMessage], *, model: str, temperature: float
    ) -> LLMResponse:
        if not self._api_key:
            raise ProviderNotConfiguredError(f"{self._env_key_name} is not set.")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self._base_url,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": model,
                    "temperature": temperature,
                    "messages": [{"role": m.role, "content": m.content} for m in messages],
                },
            )
        response.raise_for_status()
        data = response.json()
        return LLMResponse(content=data["choices"][0]["message"]["content"], model=model)


class OpenAIProvider(_OpenAICompatibleProvider):
    _base_url = "https://api.openai.com/v1/chat/completions"
    _env_key_name = "OPENAI_API_KEY"


class GroqProvider(_OpenAICompatibleProvider):
    _base_url = "https://api.groq.com/openai/v1/chat/completions"
    _env_key_name = "GROQ_API_KEY"
