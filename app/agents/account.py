"""Account domain agent."""

from typing import Any

from app.agents.prompts import compose_worker_prompt
from app.agents.tool_loop import bind_ticket_customer, run_tool_loop
from app.tools.account.tools import ACCOUNT_TOOLS
from app.tools.escalation.tools import ESCALATION_TOOLS
from app.tools.knowledge_base.tools import search_knowledge_base

ACCOUNT_SYSTEM = """You represent TechStore Support for account questions.
Use get_customer and verify_identity for the ticket customer only.
Never list all gold customers or other accounts.
Do not claim administrator powers for the user.
Call evaluate_escalation for privacy beyond the customer's own profile.
Search account_policy when needed. Do not open a Ticket.
Cite the merchant as TechStore. Never say NexaCommerce."""


async def run_account_agent(
    user_message: str,
    principal_scopes: list[str],
    customer_id: str | None = None,
    customer_name: str | None = None,
    customer_tier: str | None = None,
    account_status: str | None = None,
    orders_summary: list[dict[str, Any]] | None = None,
    history: list[Any] | None = None,
) -> dict[str, Any]:
    """Run account worker with a real tool-calling loop."""
    bind_ticket_customer(customer_id)
    return await run_tool_loop(
        system_prompt=compose_worker_prompt(
            ACCOUNT_SYSTEM,
            customer_name=customer_name,
            customer_tier=customer_tier,
            account_status=account_status,
            orders_summary=orders_summary,
        ),
        user_message=user_message,
        history=history,
        tools=[*ACCOUNT_TOOLS, *ESCALATION_TOOLS, search_knowledge_base],
        principal_scopes=principal_scopes,
    )
