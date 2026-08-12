"""Ticket API routes."""

import json
import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter
from langchain_core.messages import HumanMessage
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse

from app.api.dependencies import GraphDep, KbContextDep, PrincipalDep, SessionDep
from app.api.exceptions import TicketNotFoundError
from app.api.schemas import (
    CreateTicketRequest,
    ResolutionResponse,
    ResolveRequest,
    TicketResponse,
)
from app.models.customer import Customer
from app.models.resolution import Resolution
from app.models.ticket import Ticket, TicketIntent, TicketStatus
from app.observability.langfuse import build_langfuse_handler
from app.observability.metrics import get_metrics
from app.security.authorization import authorize_route

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketResponse, status_code=201)
async def create_ticket(
    body: CreateTicketRequest,
    session: SessionDep,
    principal: PrincipalDep,
) -> TicketResponse:
    """Create a new support ticket."""
    authorize_route(principal, ["write"])

    result = await session.execute(
        select(Customer).where(Customer.email == body.customer_email)
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        customer = Customer(email=body.customer_email, name=body.customer_name)
        session.add(customer)
        await session.flush()

    ticket = Ticket(
        customer_id=customer.id,
        subject=body.subject,
        description=body.description,
        status=TicketStatus.OPEN,
    )
    session.add(ticket)
    await session.flush()

    return TicketResponse(
        id=ticket.id,
        customer_id=ticket.customer_id,
        subject=ticket.subject,
        description=ticket.description,
        status=ticket.status,
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: uuid.UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> TicketResponse:
    """Get ticket by ID."""
    authorize_route(principal, ["read"])
    ticket = await _get_ticket_or_404(session, ticket_id)
    resolution_text = None
    escalated = False
    if ticket.resolution:
        resolution_text = ticket.resolution.answer
        escalated = ticket.resolution.escalated

    return TicketResponse(
        id=ticket.id,
        customer_id=ticket.customer_id,
        subject=ticket.subject,
        description=ticket.description,
        status=ticket.status,
        intent=ticket.intent,
        escalated_at=ticket.escalated_at,
        resolution=resolution_text,
        escalated=escalated,
    )


@router.post("/{ticket_id}/resolve", response_model=ResolutionResponse)
async def resolve_ticket(
    ticket_id: uuid.UUID,
    body: ResolveRequest,
    session: SessionDep,
    graph: GraphDep,
    principal: PrincipalDep,
    _kb: KbContextDep,
) -> ResolutionResponse:
    """Resolve a ticket using the support graph."""
    authorize_route(principal, ["write"])
    ticket = await _get_ticket_or_404(session, ticket_id)

    messages = body.to_langchain_messages()
    if not messages:
        messages = [HumanMessage(content=ticket.description)]

    config: dict = {
        "configurable": {"thread_id": str(ticket_id)},
        "callbacks": [],
    }
    handler = build_langfuse_handler(str(ticket_id))
    if handler:
        config["callbacks"].append(handler)

    result = await graph.ainvoke(
        {
            "ticket_id": str(ticket_id),
            "customer_id": str(ticket.customer_id),
            "messages": messages,
            "principal_scopes": principal.scopes,
        },
        config=config,
    )

    response = await _persist_resolution(session, ticket, result)
    if result.get("needs_human"):
        get_metrics().increment("escalations")
    return response


@router.post("/{ticket_id}/stream")
async def stream_ticket_resolution(
    ticket_id: uuid.UUID,
    body: ResolveRequest,
    session: SessionDep,
    graph: GraphDep,
    principal: PrincipalDep,
    _kb: KbContextDep,
) -> EventSourceResponse:
    """Stream graph execution via Server-Sent Events."""
    authorize_route(principal, ["write"])
    ticket = await _get_ticket_or_404(session, ticket_id)
    messages = body.to_langchain_messages() or [HumanMessage(content=ticket.description)]

    async def event_generator():
        config = {"configurable": {"thread_id": str(ticket_id)}}
        async for event in graph.astream(
            {
                "ticket_id": str(ticket_id),
                "customer_id": str(ticket.customer_id),
                "messages": messages,
                "principal_scopes": principal.scopes,
            },
            config=config,
            stream_mode="updates",
        ):
            yield {
                "event": "update",
                "data": json.dumps(event, default=str),
            }
        yield {"event": "done", "data": json.dumps({"status": "complete"})}

    return EventSourceResponse(event_generator())


async def _get_ticket_or_404(session, ticket_id: uuid.UUID) -> Ticket:
    """Load ticket or raise."""
    result = await session.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if ticket is None:
        raise TicketNotFoundError(str(ticket_id))
    return ticket


async def _persist_resolution(
    session,
    ticket: Ticket,
    result: dict,
) -> ResolutionResponse:
    """Persist graph result to database."""
    intent_str = result.get("intent", "unknown")
    try:
        ticket.intent = TicketIntent(intent_str)
    except ValueError:
        ticket.intent = TicketIntent.UNKNOWN

    escalated = bool(result.get("needs_human"))
    if escalated:
        ticket.status = TicketStatus.ESCALATED
        ticket.escalated_at = datetime.now(UTC)
    else:
        ticket.status = TicketStatus.RESOLVED

    answer = result.get("draft_answer", "No answer generated.")
    confidence = result.get("confidence")

    existing = await session.execute(
        select(Resolution).where(Resolution.ticket_id == ticket.id)
    )
    resolution = existing.scalar_one_or_none()
    if resolution is None:
        resolution = Resolution(
            ticket_id=ticket.id,
            answer=answer,
            escalated=escalated,
            confidence=confidence,
        )
        session.add(resolution)
    else:
        resolution.answer = answer
        resolution.escalated = escalated
        resolution.confidence = confidence

    await session.flush()

    return ResolutionResponse(
        ticket_id=ticket.id,
        answer=answer,
        intent=intent_str,
        confidence=confidence,
        escalated=escalated,
        tool_results=result.get("tool_results", []),
        retrieved_context=result.get("retrieved_context", []),
    )
