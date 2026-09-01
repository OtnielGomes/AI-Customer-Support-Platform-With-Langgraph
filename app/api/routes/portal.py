"""Customer portal identity and conversation bootstrap."""

import uuid

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.dependencies import PrincipalDep, SessionDep
from app.api.exceptions import TicketConflictError
from app.api.schemas import (
    CreateConversationRequest,
    CustomerProfileResponse,
    PortalSessionRequest,
    TicketResponse,
)
from app.models.order import Order, OrderItem
from app.models.ticket import Ticket, TicketStatus
from app.security.authorization import authorize_route
from app.security.customer_identity import CustomerDep, resolve_customer_by_email
from app.services import ticket_service
from app.services.order_summary import order_to_api_summary

router = APIRouter(prefix="/portal", tags=["portal"])


@router.post("/session", response_model=CustomerProfileResponse)
async def portal_session(
    body: PortalSessionRequest,
    session: SessionDep,
    principal: PrincipalDep,
) -> CustomerProfileResponse:
    """Validate a login email against existing customers."""
    authorize_route(principal, ["read"])
    customer = await resolve_customer_by_email(session, body.email)
    return await _profile(session, customer)


@router.get("/me", response_model=CustomerProfileResponse)
async def portal_me(
    session: SessionDep,
    principal: PrincipalDep,
    customer: CustomerDep,
) -> CustomerProfileResponse:
    """Return the authenticated portal customer, orders, and open chats."""
    authorize_route(principal, ["read"])
    return await _profile(session, customer)


@router.post("/conversations", response_model=TicketResponse, status_code=201)
async def create_conversation(
    body: CreateConversationRequest,
    session: SessionDep,
    principal: PrincipalDep,
    customer: CustomerDep,
) -> TicketResponse:
    """Open a chat thread for the logged-in customer."""
    authorize_route(principal, ["write"])
    order_id: uuid.UUID | None = body.order_id
    if order_id is not None:
        order = await session.get(Order, order_id)
        if order is None or order.customer_id != customer.id:
            raise TicketConflictError("new", "Order does not belong to this customer")
    ticket = Ticket(
        customer_id=customer.id,
        order_id=order_id,
        subject="Support chat",
        description="",
        status=TicketStatus.OPEN,
    )
    session.add(ticket)
    await session.flush()
    # Reload relationships: lazy IO on ticket.customer / ticket.resolution
    # raises MissingGreenlet under AsyncSession (same pattern as close_ticket).
    loaded = await ticket_service.get_ticket_or_404(session, ticket.id)
    return ticket_service.ticket_to_response(loaded)


async def _profile(session, customer) -> CustomerProfileResponse:
    """Build the portal profile DTO."""
    orders_result = await session.execute(
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.payments),
        )
        .where(Order.customer_id == customer.id)
        .order_by(Order.created_at.desc())
    )
    orders = list(orders_result.scalars().unique().all())
    tickets_result = await session.execute(
        select(Ticket)
        .options(selectinload(Ticket.customer), selectinload(Ticket.resolution))
        .where(Ticket.customer_id == customer.id)
        .order_by(Ticket.last_message_at.desc().nulls_last(), Ticket.created_at.desc())
        .limit(20)
    )
    tickets = list(tickets_result.scalars().unique().all())
    return CustomerProfileResponse(
        id=customer.id,
        public_id=customer.public_id,
        email=customer.email,
        name=customer.name,
        customer_tier=customer.customer_tier.value,
        account_status=customer.account_status.value,
        orders=[order_to_api_summary(order) for order in orders],
        conversations=[ticket_service.ticket_to_summary(ticket) for ticket in tickets],
    )
