"""Dedicated portal customer with ten labeled orders for manual agent tests."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from app.synthetic.anomalies import _add_return_and_optional_refund, _product_by_category
from app.synthetic.graph import (
    DEMO_SHOWCASE_EMAIL,
    DEMO_SHOWCASE_NAME,
    add_order_bundle,
    build_customer,
)
from app.synthetic.records import ScenarioRecord, World
from app.synthetic.rng import SeededRNG


def build_demo_showcase(
    world: World,
    rng: SeededRNG,
    now: datetime,
    company: dict[str, Any],
) -> None:
    """Attach one standard-tier customer with ten scenario-mapped orders.

    The customer email is the documented portal login ``demo@test.com.br``.
    Existing per-kind customers from ``overlay_anomalies`` are left intact.
    """
    window = int(company["refund"]["standard_window_days"])
    threshold = Decimal(str(company["refund"]["approval_threshold_brl"]))
    customer = build_customer(
        world,
        rng,
        now,
        index=len(world.customers) + 1,
        tier="standard",
        email=DEMO_SHOWCASE_EMAIL,
        name=DEMO_SHOWCASE_NAME,
    )
    world.customers.append(customer)

    _double_payment(world, rng, now, company, customer)
    _delayed_shipment(world, rng, now, company, customer)
    _delivered_missing(world, rng, now, company, customer)
    _refund_outside_window(world, rng, now, company, customer, window)
    _defective_warranty(world, rng, now, company, customer, window)
    _high_value_refund(world, rng, now, company, customer, threshold)
    _cancel_after_ship(world, rng, now, company, customer)
    _final_sale(world, rng, now, company, customer)
    _failed_payment(world, rng, now, company, customer)
    _happy_path(world, rng, now, company, customer)


def _scenario(
    world: World,
    *,
    scenario_id: str,
    kind: str,
    customer_id,
    order_id,
    message: str,
    expected_intent: str,
    expected_resolution: str,
    expected_tools: list[str],
    expected_policy: str,
    requires_human: bool = False,
    payload: dict[str, Any] | None = None,
) -> None:
    """Append a labeled scenario for the showcase customer."""
    world.scenarios.append(
        ScenarioRecord(
            id=scenario_id,
            kind=kind,
            customer_id=customer_id,
            order_id=order_id,
            payload=payload or {},
            user_message_pt=message,
            expected_intent=expected_intent,
            expected_resolution=expected_resolution,
            requires_human=requires_human,
            expected_tools=expected_tools,
            expected_policy=expected_policy,
        )
    )


def _double_payment(world, rng, now, company, customer) -> None:
    product = _product_by_category(world, "headphones", final_sale=False)
    order = add_order_bundle(
        world,
        rng,
        now,
        company,
        customer,
        product,
        status="delivered",
        created_at=now - timedelta(days=12),
        extra_paid_payment=True,
        delivered_offset_days=5,
    )
    paid = [
        payment
        for payment in world.payments
        if payment.order_id == order.id and payment.status == "paid"
    ]
    _scenario(
        world,
        scenario_id="SCN-DEMO-01",
        kind="double_payment",
        customer_id=customer.id,
        order_id=order.id,
        message="Fui cobrado duas vezes pelo mesmo pedido.",
        expected_intent="billing",
        expected_resolution="refund_duplicate_charge",
        expected_tools=["get_order", "get_payments"],
        expected_policy="payment_policy",
        payload={"payment_ids": [str(item.id) for item in paid]},
    )


def _delayed_shipment(world, rng, now, company, customer) -> None:
    product = _product_by_category(world, "accessories")
    order = add_order_bundle(
        world,
        rng,
        now,
        company,
        customer,
        product,
        status="shipped",
        created_at=now - timedelta(days=20),
        shipment_status="in_transit",
        estimated_offset_days=5,
        customer_received=None,
    )
    _scenario(
        world,
        scenario_id="SCN-DEMO-02",
        kind="delayed_shipment",
        customer_id=customer.id,
        order_id=order.id,
        message="Meu pedido esta atrasado.",
        expected_intent="logistics",
        expected_resolution="explain_delay",
        expected_tools=["get_order", "get_shipment"],
        expected_policy="shipping_policy",
    )


def _delivered_missing(world, rng, now, company, customer) -> None:
    product = _product_by_category(world, "keyboards")
    order = add_order_bundle(
        world,
        rng,
        now,
        company,
        customer,
        product,
        status="delivered",
        created_at=now - timedelta(days=8),
        shipment_status="delivered",
        delivered_offset_days=4,
        customer_received=False,
    )
    _scenario(
        world,
        scenario_id="SCN-DEMO-03",
        kind="delivered_missing",
        customer_id=customer.id,
        order_id=order.id,
        message="Aparece como entregue, mas nao recebi.",
        expected_intent="logistics",
        expected_resolution="investigate_missing_delivery",
        expected_tools=["get_order", "get_shipment"],
        expected_policy="shipping_policy",
        requires_human=True,
    )


def _refund_outside_window(world, rng, now, company, customer, window: int) -> None:
    product = _product_by_category(world, "accessories", final_sale=False)
    created = now - timedelta(days=window + 20)
    order = add_order_bundle(
        world,
        rng,
        now,
        company,
        customer,
        product,
        status="delivered",
        created_at=created,
        delivered_offset_days=5,
    )
    _add_return_and_optional_refund(
        world,
        rng,
        now,
        order_id=order.id,
        customer_id=customer.id,
        reason="customer_preference",
        refund_status="denied",
        amount=order.total_amount,
        requires_human=False,
    )
    _scenario(
        world,
        scenario_id="SCN-DEMO-04",
        kind="refund_outside_window",
        customer_id=customer.id,
        order_id=order.id,
        message="Quero meu dinheiro de volta.",
        expected_intent="billing",
        expected_resolution="deny_outside_window",
        expected_tools=["get_order", "check_refund_eligibility"],
        expected_policy="refund_policy",
        payload={"days_since_delivery": window + 15},
    )


def _defective_warranty(world, rng, now, company, customer, window: int) -> None:
    product = _product_by_category(world, "laptops", final_sale=False)
    created = now - timedelta(days=window + 25)
    order = add_order_bundle(
        world,
        rng,
        now,
        company,
        customer,
        product,
        status="delivered",
        created_at=created,
        delivered_offset_days=5,
    )
    _add_return_and_optional_refund(
        world,
        rng,
        now,
        order_id=order.id,
        customer_id=customer.id,
        reason="defective_product",
        refund_status="requested",
        amount=order.total_amount,
        requires_human=order.total_amount > Decimal("1000"),
    )
    _scenario(
        world,
        scenario_id="SCN-DEMO-05",
        kind="defective_warranty",
        customer_id=customer.id,
        order_id=order.id,
        message="Meu notebook chegou com defeito. Quero reembolso.",
        expected_intent="billing",
        expected_resolution="warranty_exception",
        expected_tools=["get_order", "check_refund_eligibility"],
        expected_policy="warranty_policy",
        requires_human=order.total_amount > Decimal("1000"),
        payload={"product_category": "laptops"},
    )


def _high_value_refund(world, rng, now, company, customer, threshold: Decimal) -> None:
    product = next(
        item
        for item in world.products
        if item.unit_price > threshold and item.category == "laptops"
    )
    order = add_order_bundle(
        world,
        rng,
        now,
        company,
        customer,
        product,
        status="delivered",
        created_at=now - timedelta(days=10),
        delivered_offset_days=4,
    )
    _add_return_and_optional_refund(
        world,
        rng,
        now,
        order_id=order.id,
        customer_id=customer.id,
        reason="customer_preference",
        refund_status="pending_approval",
        amount=order.total_amount,
        requires_human=True,
    )
    _scenario(
        world,
        scenario_id="SCN-DEMO-06",
        kind="high_value_refund",
        customer_id=customer.id,
        order_id=order.id,
        message="Quero reembolso do meu notebook de alto valor.",
        expected_intent="billing",
        expected_resolution="escalate_high_value_refund",
        expected_tools=["get_order", "check_refund_eligibility"],
        expected_policy="refund_policy",
        requires_human=True,
        payload={"amount": str(order.total_amount)},
    )


def _cancel_after_ship(world, rng, now, company, customer) -> None:
    product = _product_by_category(world, "monitors")
    order = add_order_bundle(
        world,
        rng,
        now,
        company,
        customer,
        product,
        status="shipped",
        created_at=now - timedelta(days=3),
        shipment_status="in_transit",
        estimated_offset_days=7,
    )
    _scenario(
        world,
        scenario_id="SCN-DEMO-07",
        kind="cancel_after_ship",
        customer_id=customer.id,
        order_id=order.id,
        message="Quero cancelar meu pedido.",
        expected_intent="logistics",
        expected_resolution="deny_cancel_use_return",
        expected_tools=["get_order", "get_shipment"],
        expected_policy="shipping_policy",
    )


def _final_sale(world, rng, now, company, customer) -> None:
    product = _product_by_category(world, "accessories", final_sale=True)
    order = add_order_bundle(
        world,
        rng,
        now,
        company,
        customer,
        product,
        status="delivered",
        created_at=now - timedelta(days=8),
        delivered_offset_days=3,
    )
    _add_return_and_optional_refund(
        world,
        rng,
        now,
        order_id=order.id,
        customer_id=customer.id,
        reason="customer_preference",
        refund_status="denied",
        amount=order.total_amount,
        requires_human=False,
    )
    _scenario(
        world,
        scenario_id="SCN-DEMO-08",
        kind="final_sale",
        customer_id=customer.id,
        order_id=order.id,
        message="Quero devolver este item.",
        expected_intent="logistics",
        expected_resolution="deny_final_sale",
        expected_tools=["get_order", "check_refund_eligibility"],
        expected_policy="return_policy",
        payload={"final_sale": True},
    )


def _failed_payment(world, rng, now, company, customer) -> None:
    product = _product_by_category(world, "headphones", final_sale=False)
    order = add_order_bundle(
        world,
        rng,
        now,
        company,
        customer,
        product,
        status="pending",
        created_at=now - timedelta(days=2),
        failed_payments=2,
        payment_method="credit_card",
    )
    _scenario(
        world,
        scenario_id="SCN-DEMO-09",
        kind="failed_payment",
        customer_id=customer.id,
        order_id=order.id,
        message="Tentei pagar e o cartao foi recusado. O que aconteceu com o pedido?",
        expected_intent="billing",
        expected_resolution="explain_failed_payment",
        expected_tools=["get_order", "get_payments"],
        expected_policy="payment_policy",
        payload={"failed_payments": 2},
    )


def _happy_path(world, rng, now, company, customer) -> None:
    product = _product_by_category(world, "monitors", final_sale=False)
    order = add_order_bundle(
        world,
        rng,
        now,
        company,
        customer,
        product,
        status="shipped",
        created_at=now - timedelta(days=1),
        shipment_status="in_transit",
        estimated_offset_days=6,
    )
    _scenario(
        world,
        scenario_id="SCN-DEMO-10",
        kind="happy_path",
        customer_id=customer.id,
        order_id=order.id,
        message="Onde esta meu pedido?",
        expected_intent="logistics",
        expected_resolution="share_tracking",
        expected_tools=["get_order", "get_shipment"],
        expected_policy="shipping_policy",
    )
