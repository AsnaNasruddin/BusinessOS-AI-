from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.llm.base import LLMMessage, ProviderNotConfiguredError
from app.llm.cloud_providers import AnthropicProvider, GroqProvider, OpenAIProvider
from app.llm.ollama_provider import OllamaProvider


def _fake_response(json_data: dict) -> httpx.Response:
    return httpx.Response(200, json=json_data, request=httpx.Request("POST", "http://test"))


async def test_ollama_provider_parses_response():
    provider = OllamaProvider("http://localhost:11434")
    fake = _fake_response({"message": {"content": "hello"}})
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=fake)):
        result = await provider.complete(
            [LLMMessage(role="user", content="hi")], model="llama3.1:8b", temperature=0.2
        )
    assert result.content == "hello"
    assert result.model == "llama3.1:8b"


async def test_ollama_provider_unreachable_raises_not_configured():
    provider = OllamaProvider("http://localhost:11434")
    with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=httpx.ConnectError("refused"))):
        with pytest.raises(ProviderNotConfiguredError):
            await provider.complete(
                [LLMMessage(role="user", content="hi")], model="llama3.1:8b", temperature=0.2
            )


async def test_anthropic_provider_requires_api_key():
    provider = AnthropicProvider(api_key=None)
    with pytest.raises(ProviderNotConfiguredError):
        await provider.complete(
            [LLMMessage(role="user", content="hi")], model="claude-haiku", temperature=0.2
        )


async def test_anthropic_provider_parses_response():
    provider = AnthropicProvider(api_key="sk-test")
    fake = _fake_response({"content": [{"text": "hello from claude"}]})
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=fake)):
        result = await provider.complete(
            [LLMMessage(role="system", content="sys"), LLMMessage(role="user", content="hi")],
            model="claude-haiku",
            temperature=0.2,
        )
    assert result.content == "hello from claude"


async def test_openai_and_groq_require_api_key():
    with pytest.raises(ProviderNotConfiguredError):
        await OpenAIProvider(api_key=None).complete(
            [LLMMessage(role="user", content="hi")], model="gpt-4o-mini", temperature=0.2
        )
    with pytest.raises(ProviderNotConfiguredError):
        await GroqProvider(api_key=None).complete(
            [LLMMessage(role="user", content="hi")], model="llama-3.1-8b-instant", temperature=0.2
        )


async def test_openai_provider_parses_response():
    provider = OpenAIProvider(api_key="sk-test")
    fake = _fake_response({"choices": [{"message": {"content": "hello from gpt"}}]})
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=fake)):
        result = await provider.complete(
            [LLMMessage(role="user", content="hi")], model="gpt-4o-mini", temperature=0.2
        )
    assert result.content == "hello from gpt"
