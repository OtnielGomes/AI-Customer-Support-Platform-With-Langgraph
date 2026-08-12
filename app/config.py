"""Application settings and LLM factory."""

from functools import lru_cache

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ai-customer-support"
    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/support"
    redis_url: str = "redis://localhost:6379/0"

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    chat_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    api_keys: str = "dev-key:read,write,billing:write"

    otel_exporter_otlp_endpoint: str = ""
    otel_service_name: str = "ai-customer-support"

    supervisor_confidence_threshold: float = 0.7

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        """Ensure async SQLAlchemy URL uses psycopg driver."""
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    def parsed_api_keys(self) -> dict[str, list[str]]:
        """Parse API_KEYS into key -> scopes mapping."""
        mapping: dict[str, list[str]] = {}
        if not self.api_keys.strip():
            return mapping
        for entry in self.api_keys.split(","):
            entry = entry.strip()
            if not entry:
                continue
            if ":" in entry:
                key, scopes_raw = entry.split(":", 1)
                scopes = [s.strip() for s in scopes_raw.split(",") if s.strip()]
            else:
                key, scopes = entry, ["read", "write"]
            mapping[key.strip()] = scopes
        return mapping

    def langfuse_enabled(self) -> bool:
        """Return True when Langfuse credentials are configured."""
        return bool(self.langfuse_public_key and self.langfuse_secret_key)

    def checkpoint_database_url(self) -> str:
        """Return psycopg-compatible URL for LangGraph checkpointer."""
        url = self.database_url
        if url.startswith("postgresql+psycopg://"):
            return url.replace("postgresql+psycopg://", "postgresql://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


def build_chat_model(settings: Settings | None = None) -> ChatOpenAI:
    """Build configured chat model from settings."""
    cfg = settings or get_settings()
    return ChatOpenAI(
        model=cfg.chat_model,
        api_key=cfg.openai_api_key,
        temperature=0,
    )


def build_embeddings(settings: Settings | None = None) -> OpenAIEmbeddings:
    """Build configured embeddings model from settings."""
    cfg = settings or get_settings()
    return OpenAIEmbeddings(
        model=cfg.embedding_model,
        api_key=cfg.openai_api_key,
        dimensions=cfg.embedding_dimensions,
    )
