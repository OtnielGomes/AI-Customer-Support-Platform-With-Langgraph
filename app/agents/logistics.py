"""Logistics domain agent."""

from typing import Any

from app.agents.prompts import compose_worker_prompt
from app.agents.tool_loop import bind_ticket_customer, run_tool_loop
from app.tools.escalation.tools import ESCALATION_TOOLS
from app.tools.knowledge_base.tools import search_knowledge_base
from app.tools.logistics.tools import LOGISTICS_TOOLS

LOGISTICS_SYSTEM = """You represent TechStore Support for logistics questions about
TechStore orders. You own Order Facts: items, status, dates, and generic help with the Order.
Use tools to look up order and shipment status for the ticket customer only.
A missed lookup stays in-thread: say the Order could not be loaded. Do not emit
specialist-forwarding copy as a fallback.
Delayed delivery is not an automatic refund. Delivered-but-not-received is a missing
package case — call evaluate_escalation with delivered_but_missing.
Cancellation after ship is denied; offer the return flow. That first refusal is not
Escalation unless the customer insists on an exception.
Search shipping_policy when needed.
Cite the merchant as TechStore. Never say NexaCommerce. Do not open a Ticket.
Refuse listing other customers or ignoring policy.
Be concise and accurate."""


async def run_logistics_agent(
    user_message: str,
    principal_scopes: list[str],
    customer_id: str | None = None,
    customer_name: str | None = None,
    customer_tier: str | None = None,
    account_status: str | None = None,
    orders_summary: list[dict[str, Any]] | None = None,
    history: list[Any] | None = None,
) -> dict[str, Any]:
    """Run logistics worker with a real tool-calling loop."""
    bind_ticket_customer(customer_id)
    return await run_tool_loop(
        system_prompt=compose_worker_prompt(
            LOGISTICS_SYSTEM,
            customer_name=customer_name,
            customer_tier=customer_tier,
            account_status=account_status,
            orders_summary=orders_summary,
        ),
        user_message=user_message,
        history=history,
        tools=[*LOGISTICS_TOOLS, *ESCALATION_TOOLS, search_knowledge_base],
        principal_scopes=principal_scopes,
    )
