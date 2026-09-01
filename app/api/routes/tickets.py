"""Ticket API routes."""

import logging
import time
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Query
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from sse_starlette.sse import EventSourceResponse

from app.api.dependencies import GraphDep, KbContextDep, PrincipalDep, RedisDep, SessionDep
from app.api.exceptions import CustomerNotFoundError, TicketConflictError
from app.api.schemas import (
    AgentRunListResponse,
    ChatMessageListResponse,
    ChatMessageRequest,
    CloseTicketRequest,
    CreateTicketRequest,
    EscalationReplyRequest,
    ResolutionResponse,
    ResolveRequest,
    TakeoverRequest,
    TicketListResponse,
    TicketResponse,
)
from app.config import get_settings
from app.models.order import Order
from app.models.ticket import Ticket, TicketIntent, TicketStatus
from app.models.ticket_message import TicketMessageRole
from app.observability.langfuse import build_langfuse_handler
from app.observability.trace_recorder import TraceRecorder
from app.security.authorization import authorize_route
from app.security.customer_identity import OptionalCustomerDep, resolve_customer_by_email
from app.services import chat_service, ticket_service
from app.services.chat_bus import publish_ticket_event, subscribe_ticket_events
from app.services.graph_runner import (
    build_graph_config,
    invoke_graph,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketResponse, status_code=201)
async def create_ticket(
    body: CreateTicketRequest,
    session: SessionDep,
    principal: PrincipalDep,
    customer: OptionalCustomerDep,
) -> TicketResponse:
    """Create a new support ticket for an existing customer."""
    authorize_route(principal, ["write"])

    found = await resolve_customer_by_email(session, body.customer_email)
    if customer is not None and found.id != customer.id:
        raise CustomerNotFoundError(body.customer_email)

    order_id = body.order_id
    if order_id is not None:
        order = await session.get(Order, order_id)
        if order is None or order.customer_id != found.id:
            raise TicketConflictError("new", "Order does not belong to this customer")

    ticket = Ticket(
        customer_id=found.id,
        order_id=order_id,
        subject=body.subject,
        description=body.description,
        status=TicketStatus.OPEN,
    )
    session.add(ticket)
    await session.flush()
    await session.refresh(ticket, attribute_names=["created_at", "updated_at"])
    await ticket_service.append_message(
        session,
        ticket,
        TicketMessageRole.CUSTOMER,
        body.description,
    )
    await session.refresh(ticket, attribute_names=["created_at", "updated_at", "last_message_at"])
    loaded = await ticket_service.get_ticket_or_404(session, ticket.id)
    return ticket_service.ticket_to_response(loaded)


@router.get("", response_model=TicketListResponse)
async def list_tickets(
    session: SessionDep,
    principal: PrincipalDep,
    customer: OptionalCustomerDep,
    status: Annotated[TicketStatus | None, Query()] = None,
    intent: Annotated[TicketIntent | None, Query()] = None,
    escalated: Annotated[bool | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    customer_email: Annotated[str | None, Query(max_length=255)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    order: Annotated[Literal["desc", "asc"], Query()] = "desc",
    sort: Annotated[Literal["created_at", "last_message_at"], Query()] = "created_at",
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
        owner_id=customer.id if customer is not None else None,
        limit=limit,
        offset=offset,
        order=order,
        sort=sort,
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: uuid.UUID,
    session: SessionDep,
    principal: PrincipalDep,
    customer: OptionalCustomerDep,
) -> TicketResponse:
    """Get ticket by ID."""
    authorize_route(principal, ["read"])
    ticket = await ticket_service.get_ticket_or_404(session, ticket_id)
    ticket_service.assert_ticket_owner(ticket, customer)
    return ticket_service.ticket_to_response(ticket)


@router.post("/{ticket_id}/resolve", response_model=ResolutionResponse)
async def resolve_ticket(
    ticket_id: uuid.UUID,
    body: ResolveRequest,
    session: SessionDep,
    graph: GraphDep,
    principal: PrincipalDep,
    _kb: KbContextDep,
    customer: OptionalCustomerDep,
) -> ResolutionResponse:
    """Resolve a ticket using the support graph."""
    authorize_route(principal, ["write"])
    ticket = await ticket_service.get_ticket_or_404(session, ticket_id)
    ticket_service.assert_ticket_owner(ticket, customer)
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
    redis: RedisDep,
    _kb: KbContextDep,
    customer: OptionalCustomerDep,
) -> EventSourceResponse:
    """Deprecated alias of POST /tickets/{id}/messages."""
    authorize_route(principal, ["write"])
    ticket = await ticket_service.get_ticket_or_404(session, ticket_id)
    ticket_service.assert_ticket_owner(ticket, customer)
    _reject_closed_ticket(ticket)
    content = body.messages[-1].content if body.messages else ticket.description
    return EventSourceResponse(
        chat_service.stream_customer_turn(
            session=session,
            redis=redis,
            graph=graph,
            ticket=ticket,
            principal=principal,
            content=content,
        )
    )


@router.get("/{ticket_id}/messages", response_model=ChatMessageListResponse)
async def get_ticket_messages(
    ticket_id: uuid.UUID,
    session: SessionDep,
    principal: PrincipalDep,
    customer: OptionalCustomerDep,
) -> ChatMessageListResponse:
    """Return persisted conversation history."""
    authorize_route(principal, ["read"])
    ticket = await ticket_service.get_ticket_or_404(session, ticket_id)
    ticket_service.assert_ticket_owner(ticket, customer)
    messages = await ticket_service.list_messages(session, ticket.id)
    return ChatMessageListResponse(
        items=[ticket_service.message_to_response(item) for item in messages]
    )


@router.post("/{ticket_id}/messages")
async def post_ticket_message(
    ticket_id: uuid.UUID,
    body: ChatMessageRequest,
    session: SessionDep,
    graph: GraphDep,
    principal: PrincipalDep,
    redis: RedisDep,
    _kb: KbContextDep,
    customer: OptionalCustomerDep,
) -> EventSourceResponse:
    """Append a chat turn and stream the assistant or human follow-up."""
    authorize_route(principal, ["write"])
    ticket = await ticket_service.get_ticket_or_404(session, ticket_id)
    ticket_service.assert_ticket_owner(ticket, customer)
    _reject_closed_ticket(ticket)
    role = body.role
    if customer is not None and role not in {"human_agent"}:
        role = "customer"
    if role in {"customer", "user", "human"}:
        return EventSourceResponse(
            chat_service.stream_customer_turn(
                session=session,
                redis=redis,
                graph=graph,
                ticket=ticket,
                principal=principal,
                content=body.content,
            )
        )
    return EventSourceResponse(
        chat_service.stream_human_turn(
            session=session,
            redis=redis,
            graph=graph,
            ticket=ticket,
            principal=principal,
            content=body.content,
            agent="console",
        )
    )


@router.get("/{ticket_id}/events")
async def ticket_events(
    ticket_id: uuid.UUID,
    session: SessionDep,
    principal: PrincipalDep,
    redis: RedisDep,
    customer: OptionalCustomerDep,
) -> EventSourceResponse:
    """Subscribe to live chat events for a ticket."""
    authorize_route(principal, ["read"])
    ticket = await ticket_service.get_ticket_or_404(session, ticket_id)
    ticket_service.assert_ticket_owner(ticket, customer)

    async def event_generator():
        timeout = max(5, get_settings().chat_stream_heartbeat_seconds)
        async for item in subscribe_ticket_events(
            redis, str(ticket.id), idle_timeout=float(timeout)
        ):
            yield chat_service.sse_event(str(item.get("event") or "message"), item.get("data"))

    return EventSourceResponse(event_generator())


@router.post("/{ticket_id}/takeover", response_model=TicketResponse)
async def takeover_ticket(
    ticket_id: uuid.UUID,
    body: TakeoverRequest,
    session: SessionDep,
    principal: PrincipalDep,
    redis: RedisDep,
) -> TicketResponse:
    """Assign a human agent to the live conversation."""
    authorize_route(principal, ["write"])
    ticket = await ticket_service.get_ticket_or_404(session, ticket_id)
    ticket = await ticket_service.assign_agent(session, ticket, body.agent)
    await _publish_ticket_status(redis, ticket)
    return ticket_service.ticket_to_response(ticket)


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
    customer: OptionalCustomerDep,
    redis: RedisDep,
) -> TicketResponse:
    """Close a ticket without resuming the graph."""
    authorize_route(principal, ["write"])
    ticket = await ticket_service.get_ticket_or_404(session, ticket_id)
    ticket_service.assert_ticket_owner(ticket, customer)
    ticket, message = await ticket_service.close_ticket(session, ticket, body.reason)
    await _publish_lifecycle(redis, ticket, message)
    return ticket_service.ticket_to_response(ticket)


@router.post("/{ticket_id}/confirm", response_model=TicketResponse)
async def confirm_ticket(
    ticket_id: uuid.UUID,
    session: SessionDep,
    principal: PrincipalDep,
    customer: OptionalCustomerDep,
    redis: RedisDep,
) -> TicketResponse:
    """Customer confirms the assistant's answer resolved the issue."""
    authorize_route(principal, ["write"])
    ticket = await ticket_service.get_ticket_or_404(session, ticket_id)
    ticket_service.assert_ticket_owner(ticket, customer)
    ticket, message = await ticket_service.confirm_resolution(session, ticket)
    await _publish_lifecycle(redis, ticket, message)
    return ticket_service.ticket_to_response(ticket)


@router.get("/{ticket_id}/runs", response_model=AgentRunListResponse)
async def list_ticket_runs(
    ticket_id: uuid.UUID,
    session: SessionDep,
    principal: PrincipalDep,
    customer: OptionalCustomerDep,
) -> AgentRunListResponse:
    """List persisted graph runs for a ticket."""
    authorize_route(principal, ["read"])
    ticket = await ticket_service.get_ticket_or_404(session, ticket_id)
    ticket_service.assert_ticket_owner(ticket, customer)
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


async def _publish_lifecycle(redis, ticket: Ticket, message) -> None:
    """Fan-out a system notice and the new ticket status to live subscribers."""
    if message is not None:
        await publish_ticket_event(
            redis,
            str(ticket.id),
            "message",
            ticket_service.message_to_response(message).model_dump(mode="json"),
        )
    await _publish_ticket_status(redis, ticket)


async def _publish_ticket_status(redis, ticket: Ticket) -> None:
    """Notify subscribers that ticket status or assignment changed."""
    await publish_ticket_event(
        redis,
        str(ticket.id),
        "ticket_status",
        {
            "status": ticket.status.value,
            "assigned_agent": ticket.assigned_agent,
        },
    )
