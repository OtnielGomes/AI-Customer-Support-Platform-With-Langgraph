"""Conditional routing for support graph."""

from typing import Literal

from app.agents.supervisor import should_route_to_worker
from app.graph.state import SupportState


def route_after_supervisor(state: SupportState) -> Literal[
    "billing", "logistics", "account", "escalation"
]:
    """Route to domain worker or escalation based on intent."""
    if state.get("needs_human"):
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
    if state.get("needs_human"):
        return "escalation"
    return "resolution"


async def resolution_node(state: SupportState) -> dict:
    """Finalize resolution without escalation."""
    return {
        "needs_human": False,
        "draft_answer": state.get("draft_answer", "Request processed."),
    }
