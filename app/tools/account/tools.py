"""Account domain tools backed by PostgreSQL."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from app.tools.context import ToolContext, require_context
from app.tools.lookups import customer_to_dict, load_customer, scoped_to_customer


def _ctx() -> ToolContext | dict[str, Any]:
    return require_context()


@tool
async def get_customer(customer_id: str = "") -> dict[str, Any]:
    """Get the ticket customer profile. Does not list other customers."""
    context = _ctx()
    if isinstance(context, dict):
        return context
    identifier = customer_id or (str(context.customer_id) if context.customer_id else "")
    if not identifier:
        return {"error": "customer_id is required"}
    customer = await load_customer(context.session, identifier)
    if customer is None or not scoped_to_customer(context, customer.id):
        return {"error": "Customer not found"}
    return customer_to_dict(customer)


@tool
async def verify_identity(customer_id: str = "") -> dict[str, Any]:
    """Verify the ticket customer. Never verifies a different customer."""
    context = _ctx()
    if isinstance(context, dict):
        return context
    profile = await get_customer.ainvoke({"customer_id": customer_id})
    if "error" in profile:
        context.identity_verified = False
        return {"verified": False, **profile}
    active = profile.get("account_status") == "active"
    context.identity_verified = active
    return {
        "verified": active,
        "customer_public_id": profile.get("public_id"),
        "account_status": profile.get("account_status"),
    }


ACCOUNT_TOOLS = [get_customer, verify_identity]
