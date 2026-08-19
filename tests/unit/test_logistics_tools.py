"""Unit tests for logistics tools without a live database."""

from app.tools.logistics.tools import cancel_order, get_shipment


async def test_get_shipment_without_context() -> None:
    """get_shipment should return a structured error without context."""
    result = await get_shipment.ainvoke({"order_id": "ORD-01001"})
    assert "error" in result


async def test_cancel_order_without_context() -> None:
    """cancel_order should return a structured error without context."""
    result = await cancel_order.ainvoke({"order_id": "ORD-01001"})
    assert "error" in result
