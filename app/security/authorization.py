"""Authorization helpers."""

from app.security.authentication import Principal
from app.security.permissions import TOOL_PERMISSIONS


class AuthorizationError(Exception):
    """Raised when principal lacks required scope."""

    def __init__(self, resource: str, required: list[str]) -> None:
        self.resource = resource
        self.required = required
        super().__init__(f"Missing scopes for {resource}: {required}")


def has_scope(principal: Principal, required: str) -> bool:
    """Check if principal has a specific scope."""
    return required in principal.scopes


def authorize_tool(principal: Principal, tool_name: str) -> None:
    """Authorize tool execution for principal."""
    required = TOOL_PERMISSIONS.get(tool_name, ["read"])
    if not any(has_scope(principal, scope) for scope in required):
        raise AuthorizationError(tool_name, required)


def authorize_route(principal: Principal, required_scopes: list[str]) -> None:
    """Authorize route access for principal."""
    if not any(has_scope(principal, scope) for scope in required_scopes):
        raise AuthorizationError("route", required_scopes)
