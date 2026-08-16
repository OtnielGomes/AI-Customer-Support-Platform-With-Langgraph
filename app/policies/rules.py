"""Pure policy functions. Do not import LangChain or call an LLM here."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.policies.types import CancelDecision, RefundDecision

ELECTRONICS = {"smartphones", "laptops", "monitors", "headphones"}


def _dec(value: Any) -> Decimal:
    """Convert yaml numbers to Decimal without binary float noise."""
    return Decimal(str(value))


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
    company: dict[str, Any],
    shipment_status: str | None = None,
) -> RefundDecision:
    """Evaluate refund eligibility against canonical company rules."""
    refund_cfg = company["refund"]
    warranty_cfg = company["warranty"]
    window = int(refund_cfg["standard_window_days"])
    threshold = _dec(refund_cfg["approval_threshold_brl"])
    restocking = _dec(refund_cfg["restocking_fee_rate"])
    inspection_after = int(warranty_cfg["electronics_inspection_after_days"])
    policy_ids = ["refund_policy"]
    reasons: list[str] = []

    if not identity_verified:
        return RefundDecision(
            eligible=False,
            requires_human=True,
            reasons=["IDENTITY_REQUIRED"],
            policy_ids=policy_ids + ["account_policy"],
        )

    if duplicate_charge:
        return RefundDecision(
            eligible=True,
            requires_human=amount > threshold,
            reasons=["DUPLICATE_CHARGE"],
            restocking_fee_rate=Decimal("0"),
            max_amount=amount,
            original_payment_method_only=True,
            policy_ids=["payment_policy", "refund_policy"],
        )

    if days_since_delivery is None:
        return RefundDecision(
            eligible=False,
            requires_human=False,
            reasons=["NOT_DELIVERED"],
            policy_ids=policy_ids,
        )

    if final_sale and reason == "customer_preference":
        return RefundDecision(
            eligible=False,
            requires_human=False,
            reasons=["FINAL_SALE"],
            policy_ids=policy_ids + ["return_policy"],
        )

    defective = reason == "defective_product"
    if defective:
        policy_ids = ["refund_policy", "warranty_policy"]
        if days_since_delivery > warranty_days:
            return RefundDecision(
                eligible=False,
                requires_human=False,
                reasons=["OUTSIDE_WARRANTY"],
                policy_ids=policy_ids,
            )
        reasons.append("WARRANTY_EXCEPTION" if days_since_delivery > window else "DEFECTIVE")
        inspection = (
            product_category in ELECTRONICS and days_since_delivery > inspection_after
        )
        return RefundDecision(
            eligible=True,
            requires_human=amount > threshold or inspection,
            reasons=reasons + (["INSPECTION_REQUIRED"] if inspection else []),
            restocking_fee_rate=Decimal("0"),
            max_amount=amount,
            inspection_required=inspection,
            policy_ids=policy_ids,
        )

    if days_since_delivery > window:
        return RefundDecision(
            eligible=False,
            requires_human=False,
            reasons=["OUTSIDE_WINDOW"],
            policy_ids=policy_ids,
        )

    inspection = product_category in ELECTRONICS and days_since_delivery > inspection_after
    return RefundDecision(
        eligible=True,
        requires_human=amount > threshold or inspection,
        reasons=["WITHIN_WINDOW"] + (["INSPECTION_REQUIRED"] if inspection else []),
        restocking_fee_rate=restocking,
        max_amount=amount,
        inspection_required=inspection,
        policy_ids=policy_ids,
    )


def can_cancel(*, shipment_status: str | None, order_status: str, company: dict[str, Any]) -> CancelDecision:
    """Cancellation is allowed only before the order ships."""
    shipped_states = {"shipped", "in_transit", "out_for_delivery", "delivered", "delayed", "lost"}
    if order_status in {"shipped", "delivered", "returned"} or (shipment_status in shipped_states):
        return CancelDecision(
            eligible=False,
            reasons=["SHIPPED_USE_RETURN"],
            policy_ids=["shipping_policy"],
        )
    if order_status == "cancelled":
        return CancelDecision(
            eligible=False,
            reasons=["ALREADY_CANCELLED"],
            policy_ids=["shipping_policy"],
        )
    return CancelDecision(eligible=True, reasons=["CANCEL_BEFORE_SHIPMENT"], policy_ids=["shipping_policy"])
