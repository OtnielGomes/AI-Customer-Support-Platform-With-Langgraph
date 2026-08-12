"""Billing domain tools."""

from dataclasses import dataclass
from typing import Any

from langchain_core.tools import tool


@dataclass
class BillingContext:
    """Runtime context for billing tools."""

    customer_id: str
    principal_scopes: list[str]


# Demo in-memory billing data for vertical slice
DEMO_INVOICES: dict[str, list[dict[str, Any]]] = {
    "default": [
        {
            "invoice_id": "INV-1001",
            "amount": 99.99,
            "status": "paid",
            "date": "2026-01-15",
        },
        {
            "invoice_id": "INV-1002",
            "amount": 49.50,
            "status": "pending",
            "date": "2026-02-01",
        },
    ]
}


@tool
def get_invoice(invoice_id: str) -> dict[str, Any]:
    """Get invoice details by invoice ID."""
    for invoices in DEMO_INVOICES.values():
        for invoice in invoices:
            if invoice["invoice_id"] == invoice_id:
                return invoice
    return {"error": "Invoice not found", "invoice_id": invoice_id}


@tool
def list_charges(customer_id: str = "default") -> list[dict[str, Any]]:
    """List all charges and invoices for a customer."""
    return DEMO_INVOICES.get(customer_id, DEMO_INVOICES["default"])


@tool
def request_refund(invoice_id: str, reason: str) -> dict[str, Any]:
    """Request a refund for a paid invoice. Requires billing:write scope."""
    invoice = get_invoice.invoke({"invoice_id": invoice_id})
    if "error" in invoice:
        return invoice
    if invoice.get("status") != "paid":
        return {
            "error": "Only paid invoices can be refunded",
            "invoice_id": invoice_id,
        }
    return {
        "refund_id": f"REF-{invoice_id}",
        "invoice_id": invoice_id,
        "status": "approved",
        "reason": reason,
    }


BILLING_TOOLS = [get_invoice, list_charges, request_refund]
