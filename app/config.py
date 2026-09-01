"""Application settings and LLM factory."""

from functools import lru_cache

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import Field, field_validator, model_validator
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

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5433/support"
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
    cors_origins: str = ""
    include_injection_corpus: bool = False
    chat_stream_heartbeat_seconds: int = 15
    portal_allow_unknown_email: bool = False
    simulation_as_of: str = "today"

    def parsed_cors_origins(self) -> list[str]:
        """Parse CORS_ORIGINS as a comma-separated origin list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @field_validator("include_injection_corpus", "portal_allow_unknown_email", mode="before")
    @classmethod
    def parse_include_injection(cls, value: object) -> bool:
        """Parse INCLUDE_INJECTION_CORPUS and PORTAL_ALLOW_UNKNOWN_EMAIL from env strings."""
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        """Ensure async SQLAlchemy URL uses psycopg driver."""
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @model_validator(mode="after")
    def reject_insecure_production(self) -> "Settings":
        """Refuse to boot production with development secrets or a missing LLM key."""
        if self.app_env.strip().lower() != "production":
            return self
        if not self.openai_api_key.strip():
            raise ValueError("OPENAI_API_KEY is required when APP_ENV=production")
        keys = self.parsed_api_keys()
        if not keys:
            raise ValueError("API_KEYS is required when APP_ENV=production")
        if any(key == "dev-key" for key in keys):
            raise ValueError("API_KEYS must not use the development key when APP_ENV=production")
        return self

    def parsed_api_keys(self) -> dict[str, list[str]]:
        """Parse API_KEYS into key -> scopes mapping.

        Format: ``key:scope1,scope2`` per entry. Multiple keys are separated by ``;``.
        A key without ``:`` receives default scopes ``read`` and ``write``.

        Example: ``dev-key:read,write,billing:write``
        """
        mapping: dict[str, list[str]] = {}
        if not self.api_keys.strip():
            return mapping
        for entry in self.api_keys.split(";"):
            entry = entry.strip()
            if not entry:
                continue
            if ":" not in entry:
                mapping[entry] = ["read", "write"]
                continue
            key, scopes_raw = entry.split(":", 1)
            scopes = [scope.strip() for scope in scopes_raw.split(",") if scope.strip()]
            mapping[key.strip()] = scopes or ["read", "write"]
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
