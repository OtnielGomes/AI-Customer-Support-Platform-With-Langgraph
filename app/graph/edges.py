"""Conditional routing for support graph."""

from typing import Literal

from app.graph.state import SupportState
from app.policies.engine import should_escalate


def _catalog_requires_escalation(state: SupportState) -> bool:
    """Return True when Policy or the closed catalog requires a Human Agent."""
    if state.get("needs_human"):
        return True
    decision = state.get("policy_decision") or {}
    if not isinstance(decision, dict):
        return False
    if decision.get("requires_human"):
        return True
    trigger = decision.get("escalation_trigger")
    if not trigger:
        return False
    gate = should_escalate(
        trigger=str(trigger),
        customer_insists_after_refusal=bool(decision.get("customer_insists_after_refusal")),
    )
    return gate.escalate


def route_after_supervisor(state: SupportState) -> Literal[
    "billing", "logistics", "account", "escalation"
]:
    """Route to a domain worker or Escalation from post-supervisor state.

    Known domains go to that worker regardless of classifier confidence.
    Unknown intent defaults to logistics (Order Facts). Escalation is only
    the closed catalog, engine ``requires_human``, or ``needs_human`` already set.
    """
    if _catalog_requires_escalation(state):
        return "escalation"

    intent = state.get("intent", "unknown")
    if intent == "billing":
        return "billing"
    if intent == "logistics":
        return "logistics"
    if intent == "account":
        return "account"
    return "logistics"


def route_after_worker(state: SupportState) -> Literal["resolution", "escalation"]:
    """Route to resolution or escalation after domain worker."""
    if _catalog_requires_escalation(state):
        return "escalation"
    return "resolution"


async def resolution_node(state: SupportState) -> dict:
    """Finalize resolution without escalation."""
    return {
        "needs_human": False,
        "draft_answer": state.get("draft_answer", "Request processed."),
    }
