"""Account domain tools backed by PostgreSQL."""

from __future__ import annotations

import uuid
from typing import Any

from langchain_core.tools import tool

from app.models.ticket import Ticket, TicketStatus
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


@tool
async def create_support_ticket(subject: str, description: str, order_id: str = "") -> dict[str, Any]:
    """Create an additional support ticket for the current customer."""
    context = _ctx()
    if isinstance(context, dict):
        return context
    if context.customer_id is None:
        return {"error": "No customer bound to this session"}
    order_uuid = None
    if order_id:
        from app.tools.lookups import load_order

        order = await load_order(context.session, order_id)
        if order is None or not scoped_to_customer(context, order.customer_id):
            return {"error": "Order not found", "order_id": order_id}
        order_uuid = order.id
    ticket = Ticket(
        id=uuid.uuid4(),
        customer_id=context.customer_id,
        order_id=order_uuid,
        subject=subject[:500],
        description=description,
        status=TicketStatus.OPEN,
    )
    context.session.add(ticket)
    await context.session.flush()
    return {"ticket_id": str(ticket.id), "status": ticket.status.value}


ACCOUNT_TOOLS = [get_customer, verify_identity, create_support_ticket]
