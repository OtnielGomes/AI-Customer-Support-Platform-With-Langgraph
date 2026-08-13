"""Unit tests for API key parsing."""

from app.config import Settings


def test_parsed_api_keys_with_scoped_key() -> None:
    """Scopes after the first colon may themselves contain colons."""
    settings = Settings(api_keys="dev-key:read,write,billing:write")
    assert settings.parsed_api_keys() == {
        "dev-key": ["read", "write", "billing:write"],
    }


def test_parsed_api_keys_without_scopes() -> None:
    """Bare keys should receive default read/write scopes."""
    settings = Settings(api_keys="dev-key")
    assert settings.parsed_api_keys() == {"dev-key": ["read", "write"]}


def test_parsed_api_keys_multiple_keys() -> None:
    """Multiple keys are separated by semicolons."""
    settings = Settings(api_keys="dev-key:read,write;billing-bot:billing:write")
    assert settings.parsed_api_keys() == {
        "dev-key": ["read", "write"],
        "billing-bot": ["billing:write"],
    }
