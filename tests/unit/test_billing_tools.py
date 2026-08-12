"""Unit tests for billing tools."""

from app.tools.billing.tools import get_invoice, list_charges, request_refund


def test_get_invoice_found() -> None:
    """Should return invoice when ID exists."""
    result = get_invoice.invoke({"invoice_id": "INV-1001"})
    assert result["invoice_id"] == "INV-1001"
    assert result["status"] == "paid"


def test_get_invoice_not_found() -> None:
    """Should return error for unknown invoice."""
    result = get_invoice.invoke({"invoice_id": "INV-9999"})
    assert "error" in result


def test_list_charges() -> None:
    """Should return demo charges."""
    result = list_charges.invoke({"customer_id": "default"})
    assert len(result) >= 1


def test_request_refund_paid_invoice() -> None:
    """Should approve refund for paid invoice."""
    result = request_refund.invoke({"invoice_id": "INV-1001", "reason": "duplicate"})
    assert result["status"] == "approved"
