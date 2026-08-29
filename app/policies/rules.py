"""Pure policy functions. Do not import LangChain or call an LLM here."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.policies.types import CancelDecision, EscalationDecision, RefundDecision

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

    if reason == "withdrawal":
        legal_days = int(company.get("withdrawal", {}).get("legal_days", 7))
        if days_since_delivery is None:
            return RefundDecision(
                eligible=False,
                requires_human=False,
                reasons=["NOT_DELIVERED"],
                policy_ids=policy_ids + ["withdrawal_policy"],
            )
        if days_since_delivery > legal_days:
            return RefundDecision(
                eligible=False,
                requires_human=False,
                reasons=["OUTSIDE_WITHDRAWAL_WINDOW"],
                policy_ids=policy_ids + ["withdrawal_policy"],
            )
        return RefundDecision(
            eligible=True,
            requires_human=amount > threshold,
            reasons=["WITHDRAWAL"],
            restocking_fee_rate=Decimal("0"),
            max_amount=amount,
            original_payment_method_only=True,
            policy_ids=policy_ids + ["withdrawal_policy"],
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


def can_cancel(
    *,
    shipment_status: str | None,
    order_status: str,
    company: dict[str, Any],
) -> CancelDecision:
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
    return CancelDecision(
        eligible=True,
        reasons=["CANCEL_BEFORE_SHIPMENT"],
        policy_ids=["shipping_policy"],
    )


ALWAYS_ESCALATE = frozenset(
    {
        "delivered_but_missing",
        "fraud",
        "privacy_beyond_own_profile",
        "product_technical_assistance",
        "unusable_identity",
        "policy_exception_demanded",
    }
)
AUTONOMOUS_TRIGGERS = frozenset({"order_tracking", "payment_status"})


def should_escalate(
    *,
    trigger: str,
    customer_insists_after_refusal: bool = False,
) -> EscalationDecision:
    """Evaluate the closed Escalation catalog.

    Lawful first refusals stay in-thread. The Customer demanding an exception
    after that refusal is Escalation. Tracking and payment-status lookups stay
    autonomous.
    """
    procedure = ["escalation_procedure"]
    if trigger in ALWAYS_ESCALATE:
        return EscalationDecision(
            escalate=True,
            reasons=[trigger.upper()],
            policy_ids=procedure,
        )
    if trigger == "lawful_refusal":
        if customer_insists_after_refusal:
            return EscalationDecision(
                escalate=True,
                reasons=["POLICY_EXCEPTION_DEMANDED"],
                policy_ids=procedure,
            )
        return EscalationDecision(
            escalate=False,
            reasons=["LAWFUL_REFUSAL"],
            policy_ids=["refund_policy"],
        )
    if trigger in AUTONOMOUS_TRIGGERS:
        return EscalationDecision(escalate=False, reasons=["AUTONOMOUS"], policy_ids=[])
    return EscalationDecision(escalate=False, reasons=["UNKNOWN_TRIGGER"], policy_ids=[])


def escalation_from_facts(facts: dict[str, Any]) -> EscalationDecision:
    """Map structured Facts onto the closed Escalation catalog."""
    account_status = facts.get("account_status")
    if account_status in {"suspended", "closed"}:
        return should_escalate(trigger="unusable_identity")
    if facts.get("identity_checked") and facts.get("identity_verified") is False:
        return should_escalate(trigger="unusable_identity")
    if facts.get("shipment_status") == "delivered" and facts.get("customer_received") is False:
        return should_escalate(trigger="delivered_but_missing")
    if facts.get("fraud_reported") or facts.get("chargeback"):
        return should_escalate(trigger="fraud")
    if facts.get("privacy_beyond_own_profile"):
        return should_escalate(trigger="privacy_beyond_own_profile")
    if facts.get("product_technical_assistance"):
        return should_escalate(trigger="product_technical_assistance")
    if facts.get("customer_insists_after_refusal"):
        return should_escalate(trigger="lawful_refusal", customer_insists_after_refusal=True)
    trigger = facts.get("escalation_trigger")
    if trigger:
        return should_escalate(
            trigger=str(trigger),
            customer_insists_after_refusal=bool(facts.get("customer_insists_after_refusal")),
        )
    return EscalationDecision(escalate=False, reasons=["NO_CATALOG_HIT"], policy_ids=[])
