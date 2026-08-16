"""World anomalies must match policy-engine decisions."""

from decimal import Decimal

from app.policies.engine import can_cancel, can_refund
from app.synthetic import generate_world


def test_double_payment_is_eligible_duplicate() -> None:
    """Labeled duplicate charge is eligible without restocking."""
    world = generate_world(profile="demo", seed=42)
    scenario = next(item for item in world.scenarios if item.kind == "double_payment")
    order = next(item for item in world.orders if item.id == scenario.order_id)
    decision = can_refund(
        days_since_delivery=12,
        amount=order.total_amount,
        product_category="headphones",
        final_sale=False,
        reason="customer_preference",
        identity_verified=True,
        warranty_days=90,
        duplicate_charge=True,
    )
    assert decision.eligible is True
    assert "DUPLICATE_CHARGE" in decision.reasons
    assert decision.restocking_fee_rate == Decimal("0")


def test_cancel_after_ship_world_matches_engine() -> None:
    """Shipped anomaly is not cancellable."""
    world = generate_world(profile="demo", seed=42)
    scenario = next(item for item in world.scenarios if item.kind == "cancel_after_ship")
    order = next(item for item in world.orders if item.id == scenario.order_id)
    shipment = next(item for item in world.shipments if item.order_id == order.id)
    decision = can_cancel(shipment_status=shipment.status, order_status=order.status)
    assert decision.eligible is False
