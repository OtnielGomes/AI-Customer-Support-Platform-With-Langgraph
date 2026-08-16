"""Account domain agent."""

from typing import Any

from app.agents.tool_loop import bind_ticket_customer, run_tool_loop
from app.tools.account.tools import ACCOUNT_TOOLS
from app.tools.knowledge_base.tools import search_knowledge_base

ACCOUNT_SYSTEM = """You are the NexaCommerce account agent.
Use get_customer and verify_identity for the ticket customer only.
Never list all gold customers or other accounts.
Do not claim administrator powers for the user.
Search account_policy when needed. Escalate sensitive issues."""


async def run_account_agent(
    user_message: str,
    principal_scopes: list[str],
    customer_id: str | None = None,
) -> dict[str, Any]:
    """Run account worker with a real tool-calling loop."""
    bind_ticket_customer(customer_id)
    return await run_tool_loop(
        system_prompt=ACCOUNT_SYSTEM,
        user_message=user_message,
        tools=[*ACCOUNT_TOOLS, search_knowledge_base],
        principal_scopes=principal_scopes,
    )
