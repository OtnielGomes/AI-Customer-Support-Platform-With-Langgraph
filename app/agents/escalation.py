"""Escalation agent for human handoff."""

from datetime import UTC, datetime
from typing import Any

from langchain_core.messages import AIMessage

ESCALATION_MESSAGE = (
    "Your request has been escalated to a human support specialist. "
    "A team member will follow up shortly with an update."
)


async def run_escalation_agent(
    reason: str,
    draft_answer: str | None = None,
) -> dict[str, Any]:
    """Prepare escalation response and flag human handoff."""
    message = draft_answer or ESCALATION_MESSAGE
    if reason:
        message = f"{message}\n\nEscalation reason: {reason}"

    return {
        "needs_human": True,
        "draft_answer": message,
        "messages": [AIMessage(content=message)],
        "escalated_at": datetime.now(UTC).isoformat(),
    }
