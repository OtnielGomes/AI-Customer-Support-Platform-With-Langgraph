"""Escalation catalog tool wrapping the Policy engine."""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.tools import tool

from app.policies.engine import should_escalate

EscalationTrigger = Literal[
    "delivered_but_missing",
    "fraud",
    "privacy_beyond_own_profile",
    "product_technical_assistance",
    "unusable_identity",
    "policy_exception_demanded",
    "lawful_refusal",
    "order_tracking",
    "payment_status",
]


@tool
def evaluate_escalation(
    trigger: EscalationTrigger,
    customer_insists_after_refusal: bool = False,
) -> dict[str, Any]:
    """Decide whether this Ticket must pause for a Human Agent.

    Use the closed catalog only. Lawful refusals (outside window, final sale,
    already shipped) are not Escalation unless the Customer insists on an
    exception. Order tracking and payment-status lookups stay autonomous.
    """
    decision = should_escalate(
        trigger=trigger,
        customer_insists_after_refusal=customer_insists_after_refusal,
    )
    return {
        "escalate": decision.escalate,
        "requires_human": decision.escalate,
        "reasons": decision.reasons,
        "policy_ids": decision.policy_ids,
        "escalation_trigger": trigger,
        "customer_insists_after_refusal": customer_insists_after_refusal,
    }


ESCALATION_TOOLS = [evaluate_escalation]
