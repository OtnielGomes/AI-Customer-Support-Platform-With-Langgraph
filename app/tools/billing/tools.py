"""Billing domain tools backed by PostgreSQL and the policy engine."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from langchain_core.tools import tool

from app.models.enums import RefundStatus
from app.models.refund import Refund
from app.policies.engine import can_refund
from app.tools.context import require_context, ToolContext
from app.tools.lookups import (
    days_since_delivery,
    load_order,
    load_payments,
    order_to_dict,
    primary_product,
    scoped_to_customer,
)


def _ctx() -> ToolContext | dict[str, Any]:
    return require_context()


@tool
async def get_order(order_id: str) -> dict[str, Any]:
    """Get an order by public_id (ORD-xxxxx) or UUID for the ticket customer."""
    context = _ctx()
    if isinstance(context, dict):
        return context
    order = await load_order(context.session, order_id)
    if order is None or not scoped_to_customer(context, order.customer_id):
        return {"error": "Order not found", "order_id": order_id}
    return order_to_dict(order)


@tool
async def get_order_items(order_id: str) -> dict[str, Any]:
    """List line items for an order belonging to the ticket customer."""
    context = _ctx()
    if isinstance(context, dict):
        return context
    order = await load_order(context.session, order_id)
    if order is None or not scoped_to_customer(context, order.customer_id):
        return {"error": "Order not found", "order_id": order_id}
    items = []
    for item in order.items:
        product = item.product
        items.append(
            {
                "public_id": item.public_id,
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
                "line_total": str(item.line_total),
                "product_public_id": product.public_id if product else None,
                "product_name": product.name if product else None,
                "category": product.category.value if product else None,
                "final_sale": product.final_sale if product else None,
                "warranty_days": product.warranty_days if product else None,
            }
        )
    return {"order_id": order.public_id, "items": items}


@tool
async def get_payments(order_id: str) -> dict[str, Any]:
    """List payments for an order. Does not return raw card data."""
    context = _ctx()
    if isinstance(context, dict):
        return context
    order = await load_order(context.session, order_id)
    if order is None or not scoped_to_customer(context, order.customer_id):
        return {"error": "Order not found", "order_id": order_id}
    payments = await load_payments(context.session, order.id)
    paid = [item for item in payments if item.status.value == "paid"]
    duplicate = len(paid) >= 2 and len({item.amount for item in paid}) == 1
    return {
        "order_id": order.public_id,
        "duplicate_charge": duplicate,
        "payments": [
            {
                "public_id": item.public_id,
                "status": item.status.value,
                "amount": str(item.amount),
                "payment_method": item.payment_method.value,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in payments
        ],
    }


@tool
async def get_payment_status(order_id: str) -> dict[str, Any]:
    """Summarize payment status for an order."""
    result = await get_payments.ainvoke({"order_id": order_id})
    if "error" in result:
        return result
    statuses = [item["status"] for item in result["payments"]]
    return {
        "order_id": result["order_id"],
        "statuses": statuses,
        "duplicate_charge": result["duplicate_charge"],
    }


@tool
async def check_refund_eligibility(
    order_id: str,
    reason: str = "customer_preference",
    identity_verified: bool = False,
) -> dict[str, Any]:
    """Evaluate refund eligibility with the deterministic policy engine."""
    context = _ctx()
    if isinstance(context, dict):
        return context
    order = await load_order(context.session, order_id)
    if order is None or not scoped_to_customer(context, order.customer_id):
        return {"error": "Order not found", "order_id": order_id}
    payments = await load_payments(context.session, order.id)
    paid = [item for item in payments if item.status.value == "paid"]
    duplicate = len(paid) >= 2
    product = primary_product(order)
    verified = identity_verified or context.identity_verified
    decision = can_refund(
        days_since_delivery=days_since_delivery(order),
        amount=order.total_amount if not duplicate else (paid[0].amount if paid else order.total_amount),
        product_category=product.category.value if product else "accessories",
        final_sale=bool(product.final_sale) if product else False,
        reason=reason,
        identity_verified=verified,
        warranty_days=product.warranty_days if product else 90,
        duplicate_charge=duplicate,
    )
    payload = decision.model_dump(mode="json")
    payload["order_id"] = order.public_id
    payload["reason"] = reason
    return payload


@tool
async def create_refund_request(
    order_id: str,
    reason: str = "customer_preference",
    identity_verified: bool = False,
) -> dict[str, Any]:
    """Create a refund request after policy evaluation. Does not auto-execute."""
    context = _ctx()
    if isinstance(context, dict):
        return context
    eligibility = await check_refund_eligibility.ainvoke(
        {
            "order_id": order_id,
            "reason": reason,
            "identity_verified": identity_verified or context.identity_verified,
        }
    )
    if "error" in eligibility:
        return eligibility
    if not eligibility.get("eligible"):
        return {
            "status": "denied",
            "refund_executed": False,
            "eligibility": eligibility,
        }
    order = await load_order(context.session, order_id)
    if order is None:
        return {"error": "Order not found", "order_id": order_id}
    payments = await load_payments(context.session, order.id)
    paid = [item for item in payments if item.status.value == "paid"]
    amount = Decimal(str(eligibility.get("max_amount") or order.total_amount))
    status = (
        RefundStatus.PENDING_APPROVAL
        if eligibility.get("requires_human")
        else RefundStatus.REQUESTED
    )
    refund = Refund(
        id=uuid.uuid4(),
        public_id=f"RFD-{uuid.uuid4().hex[:8].upper()}",
        order_id=order.id,
        return_id=None,
        payment_id=paid[0].id if paid else None,
        amount=amount,
        status=status,
        reason=reason,
        requires_human_approval=bool(eligibility.get("requires_human")),
    )
    context.session.add(refund)
    await context.session.flush()
    return {
        "refund_id": refund.public_id,
        "order_id": order.public_id,
        "status": refund.status.value,
        "amount": str(refund.amount),
        "refund_executed": False,
        "requires_human": refund.requires_human_approval,
        "eligibility": eligibility,
    }


BILLING_TOOLS = [
    get_order,
    get_order_items,
    get_payments,
    get_payment_status,
    check_refund_eligibility,
    create_refund_request,
]
