"""Unit tests for account tools without a live database."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.enums import AccountStatus, CustomerTier
from app.security.permissions import TOOL_PERMISSIONS
from app.tools.account.tools import ACCOUNT_TOOLS, get_customer, verify_identity
from app.tools.context import (
    ToolContext,
    clear_tool_context,
    get_tool_context,
    set_tool_context,
)


class _FakeCustomer:
    """Minimal customer double for identity verification."""

    def __init__(self, status: str) -> None:
        self.id = uuid.uuid4()
        self.public_id = "CUST-00001"
        self.name = "Ana Costa"
        self.email = "ana.costa@nexamail.com"
        self.phone = None
        self.customer_tier = CustomerTier.STANDARD
        self.account_status = AccountStatus(status)


def _bind_context(customer: _FakeCustomer) -> ToolContext:
    context = ToolContext(session=MagicMock(), customer_id=customer.id)
    set_tool_context(context)
    return context


def _unbind_context() -> None:
    clear_tool_context()


async def test_get_customer_without_context() -> None:
    """get_customer should return a structured error without context."""
    result = await get_customer.ainvoke({"customer_id": "CUST-00001"})
    assert "error" in result


async def test_verify_identity_without_context() -> None:
    """verify_identity should return a structured error without context."""
    result = await verify_identity.ainvoke({"customer_id": "CUST-00001"})
    assert "error" in result


def test_account_tools_do_not_create_tickets() -> None:
    """The Assistant must not open a second Ticket from inside a turn."""
    names = {tool.name for tool in ACCOUNT_TOOLS}
    assert "create_support_ticket" not in names
    assert "get_customer" in names
    assert "verify_identity" in names
    assert "create_support_ticket" not in TOOL_PERMISSIONS


async def test_verify_identity_true_for_active_customer() -> None:
    """Portal identity is usable when the Customer record is active."""
    customer = _FakeCustomer("active")
    _bind_context(customer)
    try:
        with patch(
            "app.tools.account.tools.load_customer",
            new=AsyncMock(return_value=customer),
        ):
            result = await verify_identity.ainvoke({"customer_id": str(customer.id)})
        assert result["verified"] is True
        assert result["account_status"] == "active"
        assert get_tool_context() is not None
        assert get_tool_context().identity_verified is True
    finally:
        _unbind_context()


async def test_verify_identity_false_for_suspended_customer() -> None:
    """A suspended Customer cannot self-serve writes."""
    customer = _FakeCustomer("suspended")
    _bind_context(customer)
    try:
        with patch(
            "app.tools.account.tools.load_customer",
            new=AsyncMock(return_value=customer),
        ):
            result = await verify_identity.ainvoke({"customer_id": str(customer.id)})
        assert result["verified"] is False
        assert result["account_status"] == "suspended"
        assert get_tool_context().identity_verified is False
    finally:
        _unbind_context()
