"""Logistics domain tools."""

from typing import Any

from langchain_core.tools import tool

DEMO_SHIPMENTS: dict[str, dict[str, Any]] = {
    "ORD-5001": {
        "order_id": "ORD-5001",
        "status": "in_transit",
        "carrier": "FastShip",
        "eta": "2026-03-05",
    },
    "ORD-5002": {
        "order_id": "ORD-5002",
        "status": "delivered",
        "carrier": "FastShip",
        "eta": "2026-02-28",
    },
}


@tool
def get_shipment_status(order_id: str) -> dict[str, Any]:
    """Get shipment status for an order."""
    shipment = DEMO_SHIPMENTS.get(order_id)
    if shipment is None:
        return {"error": "Order not found", "order_id": order_id}
    return shipment


@tool
def update_delivery_address(order_id: str, address: str) -> dict[str, Any]:
    """Update delivery address for an in-transit order."""
    shipment = DEMO_SHIPMENTS.get(order_id)
    if shipment is None:
        return {"error": "Order not found", "order_id": order_id}
    if shipment["status"] == "delivered":
        return {"error": "Cannot update address for delivered order", "order_id": order_id}
    shipment["address"] = address
    return {"order_id": order_id, "status": "address_updated", "address": address}


LOGISTICS_TOOLS = [get_shipment_status, update_delivery_address]
