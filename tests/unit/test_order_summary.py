"""Unit tests for Order summary Facts, prompts, and logistics tool access."""

from types import SimpleNamespace
from uuid import uuid4

from app.agents.prompts import format_orders_summary
from app.security.authentication import Principal
from app.security.authorization import authorize_tool
from app.services.order_summary import (
    build_orders_summary,
    order_display_number,
    order_to_dict,
    payment_snapshot,
)
from app.tools.logistics.tools import LOGISTICS_TOOLS


def _order(**overrides: object) -> SimpleNamespace:
    """Build a duck-typed Order for summary helpers."""
    defaults = {
        "id": uuid4(),
        "public_id": "ORD-01042",
        "customer_id": uuid4(),
        "status": SimpleNamespace(value="delivered"),
        "total_amount": "199.90",
        "currency": "BRL",
        "created_at": SimpleNamespace(isoformat=lambda: "2026-08-20T12:00:00-03:00"),
        "estimated_delivery": SimpleNamespace(isoformat=lambda: "2026-08-25T18:00:00-03:00"),
        "actual_delivery": SimpleNamespace(isoformat=lambda: "2026-08-24T18:00:00-03:00"),
        "payments": [
            SimpleNamespace(status=SimpleNamespace(value="paid")),
        ],
        "items": [
            SimpleNamespace(
                public_id="ITM-00001",
                quantity=1,
                unit_price="199.90",
                line_total="199.90",
                product=SimpleNamespace(
                    public_id="PRD-00001",
                    name="Monitor 27 pol.",
                    category=SimpleNamespace(value="monitors"),
                ),
            )
        ],
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_display_number_strips_ord_prefix() -> None:
    """Customer-facing Pedido label is the numeric public_id suffix."""
    assert order_display_number("ORD-01042") == "01042"


def test_payment_snapshot_counts_duplicate_paid_captures() -> None:
    """Two paid Payments on one Order are a Fact, not a new Order status."""
    order = _order(
        payments=[
            SimpleNamespace(status=SimpleNamespace(value="paid")),
            SimpleNamespace(status=SimpleNamespace(value="paid")),
        ]
    )
    snap = payment_snapshot(order)
    assert snap["payment_status"] == "paid"
    assert snap["paid_payment_count"] == 2


def test_order_to_dict_omits_items_until_requested() -> None:
    """Graph headers stay compact unless the bound Order is expanded."""
    order = _order()
    header = order_to_dict(order, include_items=False)
    assert "items" not in header
    assert header["public_id"] == "ORD-01042"
    assert header["display_number"] == "01042"
    assert header["status_label"] == "Entregue"
    assert header["payment_status_label"] == "Pago"
    detailed = order_to_dict(order, include_items=True)
    assert detailed["items"][0]["product_name"] == "Monitor 27 pol."


def test_build_orders_summary_details_only_bound_order() -> None:
    """Items attach only to the Ticket's Order."""
    bound = _order(public_id="ORD-01001")
    other = _order(id=uuid4(), public_id="ORD-01002")
    rows = build_orders_summary([bound, other], bound_order_id=bound.id)
    by_id = {row["public_id"]: row for row in rows}
    assert "items" in by_id["ORD-01001"]
    assert "estimated_delivery" in by_id["ORD-01001"]
    assert "items" not in by_id["ORD-01002"]
    assert "estimated_delivery" not in by_id["ORD-01002"]


def test_format_orders_summary_marks_bound_order_items() -> None:
    """The worker prompt must cite line items for the Ticket's Order."""
    text = format_orders_summary(
        [
            {
                "public_id": "ORD-01001",
                "status": "delivered",
                "status_label": "Entregue",
                "payment_status": "paid",
                "payment_status_label": "Pago",
                "paid_payment_count": 2,
                "total_amount": "199.90",
                "currency": "BRL",
                "created_at": "2026-08-20T00:00:00+00:00",
                "estimated_delivery": "2026-08-25T00:00:00+00:00",
                "items": [{"quantity": 1, "product_name": "Monitor 27 pol."}],
            }
        ]
    )
    assert "ORD-01001" in text
    assert "Monitor 27 pol." in text
    assert "2 payments" in text
    assert "this Ticket's Order" in text
    assert "single order" in text.lower()


def test_logistics_tools_include_get_order_items() -> None:
    """Logistics workers can load line items without a billing hop."""
    names = {tool.name for tool in LOGISTICS_TOOLS}
    assert "get_order_items" in names
    assert "get_order" in names


def test_get_order_items_authorizes_logistics_read() -> None:
    """get_order_items accepts logistics:read as well as billing:read."""
    principal = Principal(key_id="test", scopes=["logistics:read"])
    authorize_tool(principal, "get_order_items")
