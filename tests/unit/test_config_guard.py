"""Unit tests for production settings guards."""

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_development_allows_dev_key() -> None:
    """Local defaults remain usable outside production."""
    settings = Settings(app_env="development", api_keys="dev-key:read,write")
    assert "dev-key" in settings.parsed_api_keys()


def test_production_rejects_dev_key() -> None:
    """Production must not boot with the documented development API key."""
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            openai_api_key="sk-test",
            api_keys="dev-key:read,write",
        )


def test_production_rejects_missing_openai_key() -> None:
    """Production requires an LLM key."""
    with pytest.raises(ValidationError):
        Settings(app_env="production", openai_api_key="", api_keys="prod-key:read,write")
