from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Type-safe .env parsing (Section 4.1). Every setting the app reads goes
    through here — never `os.environ.get()` scattered across the codebase."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- app ---
    environment: str = "development"
    debug: bool = True
    cors_origins: list[str] = ["http://localhost:5173"]

    # --- database ---
    database_url: str = "sqlite+aiosqlite:///./businessos.db"

    # --- redis / celery ---
    redis_url: str = "redis://localhost:6379/0"

    # --- vector db ---
    chroma_host: str = "localhost"
    chroma_port: int = 8001

    # --- auth ---
    jwt_secret_key: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # --- LLM ---
    # Global default model; every Agent row can override this (Section 12, rule 4 —
    # never hardcode a model name outside this file).
    default_model_provider: str = "ollama"
    default_model_name: str = "llama3.1:8b"
    ollama_base_url: str = "http://localhost:11434"
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    groq_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
