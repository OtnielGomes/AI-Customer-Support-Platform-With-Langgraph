"""Escalation agent for human handoff."""

from datetime import UTC, datetime
from typing import Any

from langchain_core.messages import AIMessage

CUSTOMER_ESCALATION_MESSAGE = (
    "Vou encaminhar seu caso para um especialista humano. "
    "Alguém da equipe continua a partir daqui e retorna em breve."
)
ESCALATION_MESSAGE = CUSTOMER_ESCALATION_MESSAGE


async def run_escalation_agent(
    reason: str,
    draft_answer: str | None = None,
) -> dict[str, Any]:
    """Prepare escalation and flag human handoff.

    ``draft_answer`` is the customer-facing reply. ``reason`` stays on the
    interrupt payload for the console and must not be concatenated into chat.
    """
    message = (draft_answer or "").strip() or CUSTOMER_ESCALATION_MESSAGE
    return {
        "needs_human": True,
        "draft_answer": message,
        "escalation_reason": reason,
        "messages": [AIMessage(content=message)],
        "escalated_at": datetime.now(UTC).isoformat(),
    }
