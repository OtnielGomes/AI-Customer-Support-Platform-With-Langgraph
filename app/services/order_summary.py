"""Present Order Facts for graph context, tools, and API DTOs."""

from __future__ import annotations

from typing import Any

from app.api.schemas import OrderItemSummary, OrderSummary
from app.models.order import Order
from app.policies.loader import load_cached_company_config

_ORD_PREFIX = "ORD-"


def order_display_number(public_id: str) -> str:
    """Numeric part of ``ORD-xxxxx`` for customer-facing copy."""
    if public_id.upper().startswith(_ORD_PREFIX):
        return public_id[4:]
    return public_id


def fact_label(group: str, value: str) -> str:
    """Portuguese label from ``company.yaml`` ``labels.*``, else the enum value."""
    company = load_cached_company_config()
    labels = company.get("labels") or {}
    group_map = labels.get(group) if isinstance(labels, dict) else None
    if isinstance(group_map, dict):
        labeled = group_map.get(value)
        if labeled:
            return str(labeled)
    return value


def payment_snapshot(order: Order) -> dict[str, Any]:
    """Primary Payment status and count of paid captures."""
    payments = list(getattr(order, "payments", None) or [])
    paid = [item for item in payments if _enum_value(item.status) == "paid"]
    if len(paid) >= 2:
        return {"payment_status": "paid", "paid_payment_count": len(paid)}
    if paid:
        return {"payment_status": "paid", "paid_payment_count": 1}
    if payments:
        return {
            "payment_status": _enum_value(payments[0].status),
            "paid_payment_count": 0,
        }
    return {"payment_status": "pending", "paid_payment_count": 0}


def order_to_dict(order: Order, *, include_items: bool = False) -> dict[str, Any]:
    """Serialize an Order header, optionally with line items."""
    snap = payment_snapshot(order)
    status = _enum_value(order.status)
    payload: dict[str, Any] = {
        "id": str(order.id),
        "public_id": order.public_id,
        "display_number": order_display_number(order.public_id),
        "customer_id": str(order.customer_id),
        "status": status,
        "status_label": fact_label("order_status", status),
        "total_amount": str(order.total_amount),
        "currency": order.currency,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "estimated_delivery": (
            order.estimated_delivery.isoformat() if order.estimated_delivery else None
        ),
        "actual_delivery": order.actual_delivery.isoformat() if order.actual_delivery else None,
        "payment_status": snap["payment_status"],
        "payment_status_label": fact_label("payment_status", snap["payment_status"]),
        "paid_payment_count": snap["paid_payment_count"],
    }
    if include_items:
        payload["items"] = _item_dicts(order)
    return payload


def order_to_api_summary(order: Order) -> OrderSummary:
    """Build the public OrderSummary DTO including line items."""
    data = order_to_dict(order, include_items=True)
    return OrderSummary(
        id=order.id,
        public_id=order.public_id,
        display_number=data["display_number"],
        status=data["status"],
        status_label=data["status_label"],
        payment_status=data["payment_status"],
        payment_status_label=data["payment_status_label"],
        paid_payment_count=int(data["paid_payment_count"]),
        total_amount=data["total_amount"],
        currency=data["currency"],
        created_at=order.created_at,
        estimated_delivery=order.estimated_delivery,
        actual_delivery=order.actual_delivery,
        items=[
            OrderItemSummary(
                product_name=str(item["product_name"]),
                quantity=int(item["quantity"]),
                line_total=str(item["line_total"]),
            )
            for item in data.get("items") or []
        ],
    )


def build_orders_summary(
    orders: list[Order],
    *,
    bound_order_id: Any | None = None,
) -> list[dict[str, Any]]:
    """Header rows for every Order; items and ETA detail only on the bound Order."""
    bound = str(bound_order_id) if bound_order_id is not None else None
    rows: list[dict[str, Any]] = []
    for order in orders:
        include_items = bound is not None and str(order.id) == bound
        row = order_to_dict(order, include_items=include_items)
        if not include_items:
            row.pop("estimated_delivery", None)
            row.pop("actual_delivery", None)
        rows.append(row)
    return rows


def _item_dicts(order: Order) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in getattr(order, "items", None) or []:
        product = getattr(item, "product", None)
        items.append(
            {
                "public_id": item.public_id,
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
                "line_total": str(item.line_total),
                "product_public_id": product.public_id if product else None,
                "product_name": product.name if product else None,
                "category": _enum_value(product.category) if product and product.category else None,
            }
        )
    return items


def _enum_value(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw)
