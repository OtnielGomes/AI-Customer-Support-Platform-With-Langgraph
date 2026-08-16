"""Unit tests for authorization."""

import pytest

from app.security.authentication import Principal
from app.security.authorization import AuthorizationError, authorize_tool, has_scope


def test_has_scope() -> None:
    """Principal with scope should pass check."""
    principal = Principal(key_id="test", scopes=["read", "billing:write"])
    assert has_scope(principal, "billing:write")


def test_authorize_tool_billing_read() -> None:
    """get_order should authorize with read scope."""
    principal = Principal(key_id="test", scopes=["read"])
    authorize_tool(principal, "get_order")


def test_authorize_tool_refund_requires_write() -> None:
    """create_refund_request should fail without billing:write."""
    principal = Principal(key_id="test", scopes=["read"])
    with pytest.raises(AuthorizationError):
        authorize_tool(principal, "create_refund_request")
