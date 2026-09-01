"""Logistics domain tools backed by PostgreSQL."""

from __future__ import annotations

import uuid
from typing import Any

from langchain_core.tools import tool

from app.models.enums import InspectionStatus, ReturnReason, ReturnStatus
from app.models.return_request import ReturnRequest
from app.policies.engine import can_cancel
from app.tools.billing.tools import get_order, get_order_items
from app.tools.context import ToolContext, require_context
from app.tools.lookups import load_order, load_returns, load_shipment, scoped_to_customer


def _ctx() -> ToolContext | dict[str, Any]:
    return require_context()


@tool
async def get_shipment(order_id: str) -> dict[str, Any]:
    """Get shipment status for an order belonging to the ticket customer."""
    context = _ctx()
    if isinstance(context, dict):
        return context
    order = await load_order(context.session, order_id)
    if order is None or not scoped_to_customer(context, order.customer_id):
        return {"error": "Order not found", "order_id": order_id}
    shipment = await load_shipment(context.session, order.id)
    if shipment is None:
        return {"error": "Shipment not found", "order_id": order.public_id, "order_status": order.status.value}
    return {
        "order_id": order.public_id,
        "public_id": shipment.public_id,
        "carrier": shipment.carrier,
        "tracking_code": shipment.tracking_code,
        "status": shipment.status.value,
        "shipped_at": shipment.shipped_at.isoformat() if shipment.shipped_at else None,
        "estimated_delivery": (
            shipment.estimated_delivery.isoformat() if shipment.estimated_delivery else None
        ),
        "delivered_at": shipment.delivered_at.isoformat() if shipment.delivered_at else None,
        "customer_received": shipment.customer_received,
    }


@tool
async def get_shipping_status(order_id: str) -> dict[str, Any]:
    """Alias for get_shipment."""
    return await get_shipment.ainvoke({"order_id": order_id})


@tool
async def get_return_status(order_id: str) -> dict[str, Any]:
    """List return requests for an order."""
    context = _ctx()
    if isinstance(context, dict):
        return context
    order = await load_order(context.session, order_id)
    if order is None or not scoped_to_customer(context, order.customer_id):
        return {"error": "Order not found", "order_id": order_id}
    returns = await load_returns(context.session, order.id)
    return {
        "order_id": order.public_id,
        "returns": [
            {
                "public_id": item.public_id,
                "reason": item.reason.value,
                "status": item.status.value,
                "inspection_status": item.inspection_status.value,
            }
            for item in returns
        ],
    }


@tool
async def cancel_order(order_id: str) -> dict[str, Any]:
    """Cancel an order only if policy allows (before shipment)."""
    context = _ctx()
    if isinstance(context, dict):
        return context
    order = await load_order(context.session, order_id)
    if order is None or not scoped_to_customer(context, order.customer_id):
        return {"error": "Order not found", "order_id": order_id}
    shipment = await load_shipment(context.session, order.id)
    decision = can_cancel(
        shipment_status=shipment.status.value if shipment else None,
        order_status=order.status.value,
    )
    if not decision.eligible:
        return {
            "status": "denied",
            "order_id": order.public_id,
            "decision": decision.model_dump(mode="json"),
        }
    from app.models.enums import OrderStatus

    order.status = OrderStatus.CANCELLED
    await context.session.flush()
    return {
        "status": "cancelled",
        "order_id": order.public_id,
        "decision": decision.model_dump(mode="json"),
    }


@tool
async def create_return_request(
    order_id: str,
    reason: str = "customer_preference",
) -> dict[str, Any]:
    """Open a return request for a delivered or shipped order."""
    context = _ctx()
    if isinstance(context, dict):
        return context
    order = await load_order(context.session, order_id)
    if order is None or not scoped_to_customer(context, order.customer_id):
        return {"error": "Order not found", "order_id": order_id}
    try:
        parsed_reason = ReturnReason(reason)
    except ValueError:
        parsed_reason = ReturnReason.OTHER
    from datetime import datetime, timezone

    ret = ReturnRequest(
        id=uuid.uuid4(),
        public_id=f"RET-{uuid.uuid4().hex[:8].upper()}",
        order_id=order.id,
        customer_id=order.customer_id,
        reason=parsed_reason,
        status=ReturnStatus.REQUESTED,
        requested_at=datetime.now(timezone.utc),
        approved_at=None,
        inspection_status=InspectionStatus.PENDING
        if parsed_reason == ReturnReason.DEFECTIVE_PRODUCT
        else InspectionStatus.NOT_REQUIRED,
    )
    context.session.add(ret)
    await context.session.flush()
    return {
        "return_id": ret.public_id,
        "order_id": order.public_id,
        "status": ret.status.value,
        "reason": ret.reason.value,
    }


LOGISTICS_TOOLS = [
    get_order,
    get_order_items,
    get_shipment,
    get_shipping_status,
    get_return_status,
    cancel_order,
    create_return_request,
]
