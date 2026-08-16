"""Ticket API routes."""

import json
import logging
import time
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Query
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse

from app.api.dependencies import GraphDep, KbContextDep, PrincipalDep, SessionDep
from app.api.exceptions import TicketConflictError
from app.api.schemas import (
    AgentRunListResponse,
    CloseTicketRequest,
    CreateTicketRequest,
    EscalationReplyRequest,
    ResolutionResponse,
    ResolveRequest,
    TicketListResponse,
    TicketResponse,
)
from app.models.customer import Customer
from app.models.ticket import Ticket, TicketIntent, TicketStatus
from app.observability.langfuse import build_langfuse_handler
from app.observability.trace_recorder import TraceRecorder
from app.security.authorization import authorize_route
from app.services import ticket_service
from app.services.graph_runner import (
    build_graph_config,
    invoke_graph,
    snapshot_to_result,
    stream_graph_updates,
)

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

    result = await session.execute(select(Customer).where(Customer.email == body.customer_email))
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
    await session.refresh(ticket, attribute_names=["created_at", "updated_at"])

    return TicketResponse(
        id=ticket.id,
        customer_id=ticket.customer_id,
        customer_email=customer.email,
        customer_name=customer.name,
        subject=ticket.subject,
        description=ticket.description,
        status=ticket.status,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


@router.get("", response_model=TicketListResponse)
async def list_tickets(
    session: SessionDep,
    principal: PrincipalDep,
    status: Annotated[TicketStatus | None, Query()] = None,
    intent: Annotated[TicketIntent | None, Query()] = None,
    escalated: Annotated[bool | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    customer_email: Annotated[str | None, Query(max_length=255)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    order: Annotated[Literal["desc", "asc"], Query()] = "desc",
) -> TicketListResponse:
    """List tickets with filters, search, and pagination."""
    authorize_route(principal, ["read"])
    return await ticket_service.list_tickets(
        session,
        status=status,
        intent=intent,
        escalated=escalated,
        q=q,
        customer_email=customer_email,
        limit=limit,
        offset=offset,
        order=order,
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: uuid.UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> TicketResponse:
    """Get ticket by ID."""
    authorize_route(principal, ["read"])
    ticket = await ticket_service.get_ticket_or_404(session, ticket_id)
    return ticket_service.ticket_to_response(ticket)


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
    ticket = await ticket_service.get_ticket_or_404(session, ticket_id)
    _reject_closed_ticket(ticket)
    ticket.status = TicketStatus.IN_PROGRESS
    await session.flush()

    recorder = TraceRecorder()
    started_at = time.perf_counter()
    config = build_graph_config(
        str(ticket_id),
        recorder,
        extra_callbacks=[build_langfuse_handler(str(ticket_id))],
    )
    payload = _graph_payload(ticket, body, principal.scopes)
    try:
        result = await invoke_graph(graph, payload, config, recorder)
    except Exception as exc:
        logger.exception("Graph resolve failed for ticket %s", ticket_id)
        return await ticket_service.persist_graph_result(
            session,
            ticket,
            {"draft_answer": str(exc), "needs_human": False},
            recorder,
            started_at=started_at,
            error=str(exc),
        )
    return await ticket_service.persist_graph_result(
        session,
        ticket,
        result,
        recorder,
        started_at=started_at,
    )


@router.post("/{ticket_id}/stream")
async def stream_ticket_resolution(
    ticket_id: uuid.UUID,
    body: ResolveRequest,
    session: SessionDep,
    graph: GraphDep,
    principal: PrincipalDep,
    _kb: KbContextDep,
) -> EventSourceResponse:
    """Stream graph execution via Server-Sent Events and persist the result."""
    authorize_route(principal, ["write"])
    ticket = await ticket_service.get_ticket_or_404(session, ticket_id)
    _reject_closed_ticket(ticket)
    ticket.status = TicketStatus.IN_PROGRESS
    await session.flush()

    recorder = TraceRecorder()
    started_at = time.perf_counter()
    config = build_graph_config(
        str(ticket_id),
        recorder,
        extra_callbacks=[build_langfuse_handler(str(ticket_id))],
    )
    payload = _graph_payload(ticket, body, principal.scopes)

    async def event_generator():
        error: str | None = None
        try:
            async for event in stream_graph_updates(graph, payload, config, recorder):
                yield {
                    "event": "update",
                    "data": json.dumps(event, default=str),
                }
        except Exception as exc:
            logger.exception("Graph stream failed for ticket %s", ticket_id)
            error = str(exc)
            yield {"event": "error", "data": json.dumps({"error": error})}

        result = await _snapshot_result(graph, config, error)
        response = await ticket_service.persist_graph_result(
            session,
            ticket,
            result,
            recorder,
            started_at=started_at,
            error=error,
        )
        yield {
            "event": "done",
            "data": json.dumps(response.model_dump(mode="json"), default=str),
        }

    return EventSourceResponse(event_generator())


@router.post("/{ticket_id}/escalation/reply", response_model=ResolutionResponse)
async def reply_to_escalation(
    ticket_id: uuid.UUID,
    body: EscalationReplyRequest,
    session: SessionDep,
    graph: GraphDep,
    principal: PrincipalDep,
    _kb: KbContextDep,
) -> ResolutionResponse:
    """Resume an interrupted graph with a human agent's answer."""
    authorize_route(principal, ["write"])
    ticket = await ticket_service.get_ticket_or_404(session, ticket_id)
    if ticket.status != TicketStatus.ESCALATED:
        raise TicketConflictError(str(ticket_id), "Ticket is not awaiting human reply")

    recorder = TraceRecorder()
    started_at = time.perf_counter()
    config = build_graph_config(
        str(ticket_id),
        recorder,
        extra_callbacks=[build_langfuse_handler(str(ticket_id))],
    )
    ticket.status = TicketStatus.IN_PROGRESS
    await session.flush()

    result = await invoke_graph(
        graph,
        Command(resume={"answer": body.answer, "agent": body.agent}),
        config,
        recorder,
    )
    return await ticket_service.persist_graph_result(
        session,
        ticket,
        result,
        recorder,
        started_at=started_at,
    )


@router.post("/{ticket_id}/close", response_model=TicketResponse)
async def close_ticket(
    ticket_id: uuid.UUID,
    body: CloseTicketRequest,
    session: SessionDep,
    principal: PrincipalDep,
) -> TicketResponse:
    """Close a ticket without resuming the graph."""
    authorize_route(principal, ["write"])
    ticket = await ticket_service.get_ticket_or_404(session, ticket_id)
    ticket = await ticket_service.close_ticket(session, ticket, body.reason)
    return ticket_service.ticket_to_response(ticket)


@router.post("/{ticket_id}/confirm", response_model=TicketResponse)
async def confirm_ticket(
    ticket_id: uuid.UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> TicketResponse:
    """Customer confirms the assistant's answer resolved the issue."""
    authorize_route(principal, ["write"])
    ticket = await ticket_service.get_ticket_or_404(session, ticket_id)
    ticket = await ticket_service.confirm_resolution(session, ticket)
    return ticket_service.ticket_to_response(ticket)


@router.get("/{ticket_id}/runs", response_model=AgentRunListResponse)
async def list_ticket_runs(
    ticket_id: uuid.UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> AgentRunListResponse:
    """List persisted graph runs for a ticket."""
    authorize_route(principal, ["read"])
    runs = await ticket_service.list_runs(session, ticket_id)
    return AgentRunListResponse(items=[ticket_service.run_to_response(run) for run in runs])


def _graph_payload(ticket: Ticket, body: ResolveRequest, scopes: list[str]) -> dict:
    """Build the initial graph input from a ticket and request body."""
    messages = body.to_langchain_messages()
    if not messages:
        messages = [HumanMessage(content=ticket.description)]
    return {
        "ticket_id": str(ticket.id),
        "customer_id": str(ticket.customer_id),
        "messages": messages,
        "principal_scopes": scopes,
    }


def _reject_closed_ticket(ticket: Ticket) -> None:
    """Prevent graph runs on archived tickets."""
    if ticket.status == TicketStatus.CLOSED:
        raise TicketConflictError(str(ticket.id), "Ticket is closed")


async def _snapshot_result(graph, config: dict, error: str | None) -> dict:
    """Read checkpoint state after a stream, including interrupts."""
    if error:
        return {"draft_answer": error, "needs_human": False}
    try:
        snapshot = await graph.aget_state(config)
    except Exception as exc:
        logger.warning("Failed to read graph snapshot: %s", exc)
        return {"draft_answer": "Stream completed without snapshot.", "needs_human": False}
    return snapshot_to_result(snapshot)
