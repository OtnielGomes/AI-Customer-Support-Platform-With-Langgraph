"""Conditional routing for support graph."""

from typing import Literal

from app.agents.supervisor import should_route_to_worker
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
    """Route to domain worker or escalation based on intent."""
    if _catalog_requires_escalation(state):
        return "escalation"

    intent = state.get("intent", "unknown")
    confidence = state.get("confidence", 0.0)

    if not should_route_to_worker(intent, confidence):
        return "escalation"

    if intent == "billing":
        return "billing"
    if intent == "logistics":
        return "logistics"
    if intent == "account":
        return "account"
    return "escalation"


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
