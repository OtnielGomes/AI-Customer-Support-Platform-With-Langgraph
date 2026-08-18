"""Unit tests for the NexaCommerce synthetic graph (no database)."""

from datetime import datetime
from decimal import Decimal

from app.models.enums import OrderStatus
from app.synthetic import generate_world
from app.synthetic.anomalies import ANOMALY_KINDS
from app.synthetic.graph import load_company_yaml, simulation_now


def test_demo_seed_is_deterministic() -> None:
    """The same seed must yield the same public ids."""
    first = generate_world(profile="demo", seed=42)
    second = generate_world(profile="demo", seed=42)
    assert [item.public_id for item in first.customers] == [item.public_id for item in second.customers]
    assert [item.public_id for item in first.orders] == [item.public_id for item in second.orders]
    assert [item.id for item in first.scenarios] == [item.id for item in second.scenarios]


def test_demo_contains_every_anomaly_kind() -> None:
    """Demo profile must include each labeled operational anomaly."""
    world = generate_world(profile="demo", seed=42)
    kinds = {item.kind for item in world.scenarios}
    for kind in ANOMALY_KINDS:
        assert kind in kinds, kind
    negatives = [item for item in world.scenarios if item.kind == "negative_security"]
    assert len(negatives) == 6


def test_double_payment_has_two_paid_rows() -> None:
    """Duplicate-charge orders must have two paid payments of the order total."""
    world = generate_world(profile="demo", seed=42)
    scenario = next(item for item in world.scenarios if item.kind == "double_payment")
    order = next(item for item in world.orders if item.id == scenario.order_id)
    paid = [
        payment
        for payment in world.payments
        if payment.order_id == order.id and payment.status == "paid"
    ]
    assert len(paid) == 2
    assert paid[0].amount == order.total_amount
    assert paid[1].amount == order.total_amount


def test_delayed_shipment_is_past_eta() -> None:
    """Delayed scenario ETA must be before the simulation clock."""
    company = load_company_yaml()
    now = simulation_now(company)
    world = generate_world(profile="demo", seed=42, company=company)
    scenario = next(item for item in world.scenarios if item.kind == "delayed_shipment")
    shipment = next(item for item in world.shipments if item.order_id == scenario.order_id)
    assert shipment.status in {"in_transit", "delayed"}
    assert shipment.estimated_delivery is not None
    assert shipment.estimated_delivery < now
    assert shipment.delivered_at is None


def test_delivered_missing_flags_customer_received_false() -> None:
    """Missing-delivery anomaly is delivered but not received."""
    world = generate_world(profile="demo", seed=42)
    scenario = next(item for item in world.scenarios if item.kind == "delivered_missing")
    shipment = next(item for item in world.shipments if item.order_id == scenario.order_id)
    assert shipment.status == "delivered"
    assert shipment.customer_received is False


def test_outside_window_delivery_older_than_policy() -> None:
    """Preference refund outside the yaml window is older than 30 days."""
    company = load_company_yaml()
    now = simulation_now(company)
    window = int(company["refund"]["standard_window_days"])
    world = generate_world(profile="demo", seed=42, company=company)
    scenario = next(item for item in world.scenarios if item.kind == "refund_outside_window")
    order = next(item for item in world.orders if item.id == scenario.order_id)
    assert order.actual_delivery is not None
    assert (now - order.actual_delivery).days > window


def test_high_value_refund_requires_human() -> None:
    """High-value refunds are pending approval."""
    world = generate_world(profile="demo", seed=42)
    scenario = next(item for item in world.scenarios if item.kind == "high_value_refund")
    refund = next(item for item in world.refunds if item.order_id == scenario.order_id)
    assert refund.requires_human_approval is True
    assert refund.status == "pending_approval"
    assert refund.amount > Decimal("1000")


def test_order_statuses_match_enum() -> None:
    """Generated orders must use OrderStatus values, not shipment-only states."""
    world = generate_world(profile="demo", seed=42)
    valid = {member.value for member in OrderStatus}
    for order in world.orders:
        assert order.status in valid


def test_shipped_orders_can_have_in_transit_shipment() -> None:
    """In-transit logistics state lives on shipments, not order rows."""
    world = generate_world(profile="demo", seed=42)
    shipped_orders = [item for item in world.orders if item.status == "shipped"]
    assert shipped_orders
    in_transit = [
        shipment
        for shipment in world.shipments
        if shipment.status == "in_transit"
    ]
    assert in_transit


def test_line_totals_reconcile() -> None:
    """Every order total equals the sum of its line items."""
    world = generate_world(profile="demo", seed=42)
    by_order: dict = {}
    for item in world.order_items:
        by_order.setdefault(item.order_id, Decimal("0.00"))
        by_order[item.order_id] += item.line_total
    for order in world.orders:
        assert abs(by_order[order.id] - order.total_amount) <= Decimal("0.01")


def test_demo_customer_email() -> None:
    """Local demo keeps a stable portal login email."""
    world = generate_world(profile="demo", seed=42)
    assert world.customers[0].email == "ana.costa@nexamail.com"
    assert all("@" in item.email for item in world.customers)
    assert not any(item.email.endswith("@example.com") for item in world.customers)
    assert all(
        sum(1 for order in world.orders if order.customer_id == customer.id) >= 1
        for customer in world.customers
    )


def test_simulation_now_parses() -> None:
    """company.yaml clock is timezone-aware."""
    now = simulation_now(load_company_yaml())
    assert isinstance(now, datetime)
    assert now.tzinfo is not None
