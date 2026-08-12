"""Security package."""

from app.security.authentication import Principal, get_current_principal, get_principal_from_api_key
from app.security.authorization import (
    AuthorizationError,
    authorize_route,
    authorize_tool,
    has_scope,
)
from app.security.guardrails import GuardrailViolation, sanitize_input, validate_output

__all__ = [
    "AuthorizationError",
    "GuardrailViolation",
    "Principal",
    "authorize_route",
    "authorize_tool",
    "get_current_principal",
    "get_principal_from_api_key",
    "has_scope",
    "sanitize_input",
    "validate_output",
]
