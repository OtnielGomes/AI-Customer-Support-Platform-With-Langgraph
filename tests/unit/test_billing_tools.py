"""Unit tests for billing tools without a live database."""

from app.tools.billing.tools import check_refund_eligibility, get_order, get_payments
from app.tools.context import get_tool_context


def test_tools_require_context() -> None:
    """Operational tools error when no ToolContext is bound."""
    assert get_tool_context() is None


async def test_get_order_without_context() -> None:
    """get_order should return a structured error without context."""
    result = await get_order.ainvoke({"order_id": "ORD-01001"})
    assert "error" in result


async def test_get_payments_without_context() -> None:
    """get_payments should return a structured error without context."""
    result = await get_payments.ainvoke({"order_id": "ORD-01001"})
    assert "error" in result


async def test_check_refund_eligibility_without_context() -> None:
    """Policy wrapper still requires a session to load the order."""
    result = await check_refund_eligibility.ainvoke(
        {"order_id": "ORD-01001", "reason": "customer_preference"}
    )
    assert "error" in result
