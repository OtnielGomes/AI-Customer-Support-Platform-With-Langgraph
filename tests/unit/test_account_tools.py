"""Unit tests for account tools without a live database."""

from app.tools.account.tools import get_customer, verify_identity


async def test_get_customer_without_context() -> None:
    """get_customer should return a structured error without context."""
    result = await get_customer.ainvoke({"customer_id": "CUST-00001"})
    assert "error" in result


async def test_verify_identity_without_context() -> None:
    """verify_identity should return a structured error without context."""
    result = await verify_identity.ainvoke({"customer_id": "CUST-00001"})
    assert "error" in result
