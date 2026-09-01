"""Unit tests for the TechStore synthetic graph (no database)."""

from datetime import datetime
from decimal import Decimal

from app.models.enums import OrderStatus
from app.synthetic import generate_world
from app.synthetic.anomalies import ANOMALY_KINDS
from app.synthetic.graph import HAPPY_PATH_MAX_AGE_DAYS, load_company_yaml, simulation_now


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
    assert any(item.email == "demo@test.com.br" for item in world.customers)
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


def test_as_of_keeps_public_ids_and_shifts_dates() -> None:
    """The same seed with a later anchor keeps ids and shifts Order dates together."""
    company = load_company_yaml()
    frozen = generate_world(profile="demo", seed=42, company=company)
    shifted = generate_world(
        profile="demo",
        seed=42,
        company=company,
        as_of="2026-08-31T12:00:00-03:00",
    )
    assert [item.public_id for item in frozen.orders] == [item.public_id for item in shifted.orders]
    delta = shifted.orders[0].created_at - frozen.orders[0].created_at
    assert delta.days >= 16
    for left, right in zip(frozen.orders, shifted.orders, strict=True):
        assert (right.created_at - left.created_at) == delta


def test_happy_path_orders_stay_within_recent_window() -> None:
    """Non-SCN Orders are at most 15 days old and shipped ETAs stay in the future."""
    company = load_company_yaml()
    now = simulation_now(company)
    world = generate_world(profile="demo", seed=42, company=company)
    scn_customers = {item.customer_id for item in world.scenarios}
    happy = [order for order in world.orders if order.customer_id not in scn_customers]
    assert happy
    for order in happy:
        age = (now - order.created_at).days
        assert 0 <= age <= HAPPY_PATH_MAX_AGE_DAYS
        if order.status == "shipped":
            assert order.estimated_delivery is not None
            assert order.estimated_delivery >= now


def test_generated_payments_use_pix_or_credit_card() -> None:
    """v1.0 Facts never record boleto or debit as a Payment Method."""
    world = generate_world(profile="demo", seed=42)
    allowed = {"pix", "credit_card"}
    assert world.payments
    for payment in world.payments:
        assert payment.payment_method in allowed
    by_order: dict = {}
    for payment in world.payments:
        if payment.status == "paid":
            by_order.setdefault(payment.order_id, 0)
            by_order[payment.order_id] += 1
    double_pay_orders = {
        item.order_id for item in world.scenarios if item.kind == "double_payment"
    }
    assert double_pay_orders
    for order_id, count in by_order.items():
        if order_id in double_pay_orders:
            assert count == 2
        else:
            assert count == 1


def test_generated_product_names_are_generic() -> None:
    """Catalog names must not use the retired NexaPhone-style brands."""
    world = generate_world(profile="demo", seed=42)
    assert world.products
    for product in world.products:
        assert "NexaPhone" not in product.name
        assert "NexaCommerce" not in product.name
        assert not product.name.startswith("Nexa")
