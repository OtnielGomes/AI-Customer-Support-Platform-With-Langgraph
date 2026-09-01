"""Graph node implementations."""

import logging
import uuid
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from app.agents.account import run_account_agent
from app.agents.billing import run_billing_agent
from app.agents.escalation import CUSTOMER_ESCALATION_MESSAGE, run_escalation_agent
from app.agents.logistics import run_logistics_agent
from app.agents.supervisor import classify_intent
from app.graph.state import SupportState
from app.models.customer import Customer
from app.models.ticket import Ticket
from app.observability.metrics import record_node_latency
from app.policies.engine import escalation_from_facts
from app.security.guardrails import GuardrailViolation, sanitize_input, validate_output
from app.services.order_summary import build_orders_summary
from app.tools.context import get_tool_context
from app.tools.lookups import list_customer_orders

logger = logging.getLogger(__name__)


def _last_user_message(state: SupportState) -> str:
    """Extract last human message from state."""
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            return str(message.content)
        if hasattr(message, "type") and message.type == "human":
            return str(message.content)
    return ""


def _conversation_history(state: SupportState) -> list[Any]:
    """Return the graph message window for domain workers."""
    return list(state.get("messages") or [])


def _worker_kwargs(state: SupportState) -> dict[str, Any]:
    """Shared identity context passed to domain workers."""
    return {
        "customer_id": state.get("customer_id"),
        "customer_name": state.get("customer_name"),
        "customer_tier": state.get("customer_tier"),
        "account_status": state.get("account_status"),
        "orders_summary": state.get("orders_summary"),
        "history": _conversation_history(state),
    }


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


async def load_customer_context_node(state: SupportState) -> dict[str, Any]:
    """Load the authenticated customer's profile and orders into graph state."""
    with record_node_latency("load_customer_context"):
        customer_id = state.get("customer_id")
        context = get_tool_context()
        if context is None or not customer_id:
            return {}
        try:
            customer_uuid = uuid.UUID(str(customer_id))
        except ValueError:
            logger.warning("Invalid customer_id on graph state: %s", customer_id)
            return {}
        customer = await context.session.get(Customer, customer_uuid)
        if customer is None:
            return {}
        orders = await list_customer_orders(context.session, customer.id)
        bound_order_id = None
        ticket_id = state.get("ticket_id")
        if ticket_id:
            try:
                ticket = await context.session.get(Ticket, uuid.UUID(str(ticket_id)))
            except ValueError:
                ticket = None
            if ticket is not None and ticket.order_id is not None:
                bound_order_id = ticket.order_id
        if bound_order_id is None and len(orders) == 1:
            bound_order_id = orders[0].id
        summary = build_orders_summary(orders, bound_order_id=bound_order_id)
        selected: dict[str, Any] = {}
        bound = next((item for item in orders if item.id == bound_order_id), None)
        if bound is not None:
            selected = {
                "order_public_id": bound.public_id,
                "order_status": bound.status.value,
                "order_total": str(bound.total_amount),
            }
        payload: dict[str, Any] = {
            "customer_public_id": customer.public_id,
            "customer_name": customer.name,
            "customer_tier": customer.customer_tier.value,
            "account_status": customer.account_status.value,
            "orders_summary": summary,
            **selected,
        }
        identity = escalation_from_facts(
            {"account_status": customer.account_status.value}
        )
        if identity.escalate:
            payload["needs_human"] = True
            payload["policy_decision"] = {
                "requires_human": True,
                "escalation_trigger": "unusable_identity",
            }
        return payload


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
        return await run_billing_agent(text, scopes, **_worker_kwargs(state))


async def logistics_node(state: SupportState) -> dict[str, Any]:
    """Run logistics domain agent."""
    with record_node_latency("logistics"):
        text = _last_user_message(state)
        scopes = state.get("principal_scopes", ["read", "write"])
        return await run_logistics_agent(text, scopes, **_worker_kwargs(state))


async def account_node(state: SupportState) -> dict[str, Any]:
    """Run account domain agent."""
    with record_node_latency("account"):
        text = _last_user_message(state)
        scopes = state.get("principal_scopes", ["read", "write"])
        return await run_account_agent(text, scopes, **_worker_kwargs(state))


async def escalation_node(state: SupportState) -> dict[str, Any]:
    """Pause for a human agent, then apply their reply as the draft answer.

    ``interrupt()`` suspends the graph until ``Command(resume=...)`` is sent
    with the same ``thread_id``. On resume the node restarts from the top;
    ``interrupt()`` then returns the human payload.
    """
    from langgraph.types import interrupt

    with record_node_latency("escalation"):
        reason = _internal_escalation_reason(state)
        prepared = await run_escalation_agent(
            reason=reason,
            draft_answer=state.get("draft_answer"),
        )
        payload = {
            "ticket_id": state.get("ticket_id"),
            "intent": state.get("intent"),
            "confidence": state.get("confidence"),
            "reason": prepared.get("escalation_reason") or reason,
            "draft_answer": prepared.get("draft_answer"),
        }
        human = interrupt(payload)
        answer = _human_answer(human) or prepared.get("draft_answer") or CUSTOMER_ESCALATION_MESSAGE
        return {
            "needs_human": False,
            "draft_answer": answer,
            "messages": [AIMessage(content=answer)],
        }


def _internal_escalation_reason(state: SupportState) -> str:
    """Build a console-only handoff reason; never customer-facing."""
    decision = state.get("policy_decision") or {}
    if isinstance(decision, dict):
        for key in ("reason", "denial_reason", "message"):
            value = decision.get(key)
            if value:
                return str(value)
        if decision.get("requires_human"):
            return "Policy requires human review"
        trigger = decision.get("escalation_trigger")
        if trigger:
            return f"Escalation catalog: {trigger}"
    if state.get("needs_human"):
        return "Worker requested human handoff"
    return "Low confidence or unresolved issue"


def _human_answer(human: Any) -> str | None:
    """Extract the free-text answer from a resume payload."""
    if human is None:
        return None
    if isinstance(human, str):
        return human
    if isinstance(human, dict):
        answer = human.get("answer") or human.get("draft_answer")
        return str(answer) if answer else None
    return str(human)


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
                refund_executed=state.get("refund_executed", False),
            )
            return {"draft_answer": validated}
        except GuardrailViolation as exc:
            escalation = await run_escalation_agent(reason=exc.reason)
            return escalation

