"""Orchestrate policy decisions from company.yaml."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.policies.loader import load_cached_company_config
from app.policies.rules import can_cancel as cancel_rule
from app.policies.rules import can_refund as refund_rule
from app.policies.types import CancelDecision, RefundDecision


def can_refund(
    *,
    days_since_delivery: int | None,
    amount: Decimal,
    product_category: str,
    final_sale: bool,
    reason: str,
    identity_verified: bool,
    warranty_days: int,
    duplicate_charge: bool = False,
    company: dict[str, Any] | None = None,
    shipment_status: str | None = None,
) -> RefundDecision:
    """Evaluate refund eligibility using cached company configuration."""
    return refund_rule(
        days_since_delivery=days_since_delivery,
        amount=amount,
        product_category=product_category,
        final_sale=final_sale,
        reason=reason,
        identity_verified=identity_verified,
        warranty_days=warranty_days,
        duplicate_charge=duplicate_charge,
        company=company or load_cached_company_config(),
        shipment_status=shipment_status,
    )


def can_cancel(
    *,
    shipment_status: str | None,
    order_status: str,
    company: dict[str, Any] | None = None,
) -> CancelDecision:
    """Evaluate cancellation eligibility using cached company configuration."""
    return cancel_rule(
        shipment_status=shipment_status,
        order_status=order_status,
        company=company or load_cached_company_config(),
    )


def evaluate_refund_from_facts(facts: dict[str, Any]) -> RefundDecision:
    """Evaluate a refund from a tool-assembled facts dict."""
    amount = facts["amount"]
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    return can_refund(
        days_since_delivery=facts.get("days_since_delivery"),
        amount=amount,
        product_category=str(facts.get("product_category") or "accessories"),
        final_sale=bool(facts.get("final_sale")),
        reason=str(facts.get("reason") or "customer_preference"),
        identity_verified=bool(facts.get("identity_verified")),
        warranty_days=int(facts.get("warranty_days") or 90),
        duplicate_charge=bool(facts.get("duplicate_charge")),
        shipment_status=facts.get("shipment_status"),
    )
