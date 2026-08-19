"""Unit tests for the dedicated demo@test.com.br showcase customer."""

from app.synthetic import generate_world
from app.synthetic.graph import DEMO_SHOWCASE_EMAIL, DEMO_SHOWCASE_NAME


def test_demo_showcase_has_ten_orders() -> None:
    """The documented portal tester owns ten labeled orders."""
    world = generate_world(profile="demo", seed=42)
    customer = next(item for item in world.customers if item.email == DEMO_SHOWCASE_EMAIL)
    assert customer.name == DEMO_SHOWCASE_NAME
    assert customer.customer_tier == "standard"
    orders = [item for item in world.orders if item.customer_id == customer.id]
    assert len(orders) == 10
    scenarios = [item for item in world.scenarios if item.id.startswith("SCN-DEMO-")]
    assert len(scenarios) == 10
    assert {item.order_id for item in scenarios} == {item.id for item in orders}


def test_demo_showcase_kinds_are_distinct() -> None:
    """Each showcase order maps to a different test kind."""
    world = generate_world(profile="demo", seed=42)
    scenarios = [item for item in world.scenarios if item.id.startswith("SCN-DEMO-")]
    kinds = [item.kind for item in scenarios]
    assert kinds == [
        "double_payment",
        "delayed_shipment",
        "delivered_missing",
        "refund_outside_window",
        "defective_warranty",
        "high_value_refund",
        "cancel_after_ship",
        "final_sale",
        "failed_payment",
        "happy_path",
    ]


def test_demo_showcase_is_deterministic() -> None:
    """Seed 42 keeps showcase public ids stable."""
    first = generate_world(profile="demo", seed=42)
    second = generate_world(profile="demo", seed=42)
    first_ids = [item.id for item in first.scenarios if item.id.startswith("SCN-DEMO-")]
    second_ids = [item.id for item in second.scenarios if item.id.startswith("SCN-DEMO-")]
    assert first_ids == second_ids
    first_orders = [
        next(order.public_id for order in first.orders if order.id == scenario.order_id)
        for scenario in first.scenarios
        if scenario.id.startswith("SCN-DEMO-")
    ]
    second_orders = [
        next(order.public_id for order in second.orders if order.id == scenario.order_id)
        for scenario in second.scenarios
        if scenario.id.startswith("SCN-DEMO-")
    ]
    assert first_orders == second_orders
