from app.config import Settings
from app.llm.base import LLMProvider
from app.llm.cloud_providers import AnthropicProvider, GroqProvider, OpenAIProvider
from app.llm.ollama_provider import OllamaProvider


def get_llm_provider(provider: str, settings: Settings) -> LLMProvider:
    if provider == "ollama":
        return OllamaProvider(settings.ollama_base_url)
    if provider == "anthropic":
        return AnthropicProvider(settings.anthropic_api_key)
    if provider == "openai":
        return OpenAIProvider(settings.openai_api_key)
    if provider == "groq":
        return GroqProvider(settings.groq_api_key)
    raise ValueError(f"Unknown model provider: {provider!r}")
