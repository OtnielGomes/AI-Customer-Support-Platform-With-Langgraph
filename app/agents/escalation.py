"""Escalation agent for human handoff."""

from datetime import UTC, datetime
from typing import Any

from langchain_core.messages import AIMessage

CUSTOMER_ESCALATION_MESSAGE = (
    "Vou encaminhar seu atendimento para um especialista avaliar o seu problema. "
    "Alguém da equipe continua a partir daqui."
)
ESCALATION_MESSAGE = CUSTOMER_ESCALATION_MESSAGE
_HANDOFF_MARKERS = ("especialista", "encaminh")


def customer_escalation_reply(draft_answer: str | None = None) -> str:
    """Build the customer-facing handoff text.

    Keeps a useful worker draft when present and always includes an explicit
    notice that a specialist will review the case. Internal ``reason`` stays
    off this string.
    """
    notice = CUSTOMER_ESCALATION_MESSAGE
    text = (draft_answer or "").strip()
    if not text:
        return notice
    lowered = text.lower()
    if any(marker in lowered for marker in _HANDOFF_MARKERS):
        return text
    return f"{text}\n\n{notice}"


async def run_escalation_agent(
    reason: str,
    draft_answer: str | None = None,
) -> dict[str, Any]:
    """Prepare escalation and flag human handoff.

    ``draft_answer`` is the customer-facing reply. ``reason`` stays on the
    interrupt payload for the console and must not be concatenated into chat.
    """
    message = customer_escalation_reply(draft_answer)
    return {
        "needs_human": True,
        "draft_answer": message,
        "escalation_reason": reason,
        "messages": [AIMessage(content=message)],
        "escalated_at": datetime.now(UTC).isoformat(),
    }
