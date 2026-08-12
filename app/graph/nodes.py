"""Graph node implementations."""

import logging
from typing import Any

from langchain_core.messages import HumanMessage

from app.agents.account import run_account_agent
from app.agents.billing import run_billing_agent
from app.agents.escalation import run_escalation_agent
from app.agents.logistics import run_logistics_agent
from app.agents.supervisor import classify_intent
from app.graph.state import SupportState
from app.observability.metrics import record_node_latency
from app.security.guardrails import GuardrailViolation, sanitize_input, validate_output

logger = logging.getLogger(__name__)


def _last_user_message(state: SupportState) -> str:
    """Extract last human message from state."""
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            return str(message.content)
        if hasattr(message, "type") and message.type == "human":
            return str(message.content)
    return ""


async def input_guardrails_node(state: SupportState) -> dict[str, Any]:
    """Sanitize user input before graph processing."""
    with record_node_latency("input_guardrails"):
        text = _last_user_message(state)
        try:
            sanitize_input(text)
        except GuardrailViolation as exc:
            return {
                "needs_human": True,
                "draft_answer": f"Input blocked: {exc.reason}",
            }
        return {}


async def supervisor_node(state: SupportState) -> dict[str, Any]:
    """Classify intent and confidence."""
    with record_node_latency("supervisor"):
        text = _last_user_message(state)
        classification = await classify_intent(text)
        return {
            "intent": classification.intent,
            "confidence": classification.confidence,
        }


async def billing_node(state: SupportState) -> dict[str, Any]:
    """Run billing domain agent."""
    with record_node_latency("billing"):
        text = _last_user_message(state)
        scopes = state.get("principal_scopes", ["read", "write"])
        return await run_billing_agent(text, scopes)


async def logistics_node(state: SupportState) -> dict[str, Any]:
    """Run logistics domain agent."""
    with record_node_latency("logistics"):
        text = _last_user_message(state)
        scopes = state.get("principal_scopes", ["read", "write"])
        return await run_logistics_agent(text, scopes)


async def account_node(state: SupportState) -> dict[str, Any]:
    """Run account domain agent."""
    with record_node_latency("account"):
        text = _last_user_message(state)
        scopes = state.get("principal_scopes", ["read", "write"])
        return await run_account_agent(text, scopes)


async def escalation_node(state: SupportState) -> dict[str, Any]:
    """Escalate to human support."""
    with record_node_latency("escalation"):
        reason = state.get("draft_answer") or "Low confidence or unresolved issue"
        return await run_escalation_agent(reason=reason, draft_answer=state.get("draft_answer"))


async def output_guardrails_node(state: SupportState) -> dict[str, Any]:
    """Validate output before returning."""
    with record_node_latency("output_guardrails"):
        answer = state.get("draft_answer", "")
        if not answer:
            return {}
        try:
            validated = validate_output(
                answer,
                refund_tool_success=state.get("refund_tool_success", False),
            )
            return {"draft_answer": validated}
        except GuardrailViolation as exc:
            escalation = await run_escalation_agent(reason=exc.reason)
            return escalation

