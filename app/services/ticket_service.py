"""Ticket listing, resolution persistence, and agent-run flush."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.escalation import CUSTOMER_ESCALATION_MESSAGE
from app.api.exceptions import (
    RunNotFoundError,
    TicketConflictError,
    TicketNotFoundError,
    TicketOwnershipError,
)
from app.api.schemas import (
    AgentEventResponse,
    AgentRunResponse,
    ChatMessageResponse,
    ResolutionResponse,
    TicketListResponse,
    TicketResponse,
    TicketSummary,
)
from app.models.agent_run import AgentEvent, AgentRun, AgentRunStatus
from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.models.resolution import Resolution
from app.models.ticket import Ticket, TicketIntent, TicketStatus
from app.models.ticket_message import TicketMessage, TicketMessageRole
from app.observability.metrics import get_metrics
from app.observability.trace_recorder import TraceRecorder, extract_interrupt_payload
from app.security.guardrails import sanitize_customer_answer
from app.services.order_summary import order_to_api_summary

logger = logging.getLogger(__name__)


async def get_ticket_or_404(session: AsyncSession, ticket_id: uuid.UUID) -> Ticket:
    """Load a ticket with customer and resolution, or raise 404."""
    result = await session.execute(
        select(Ticket)
        .options(
            selectinload(Ticket.resolution),
            selectinload(Ticket.customer),
            selectinload(Ticket.order).selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Ticket.order).selectinload(Order.payments),
        )
        .where(Ticket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    if ticket is None:
        raise TicketNotFoundError(str(ticket_id))
    return ticket


def ticket_to_response(ticket: Ticket) -> TicketResponse:
    """Map a ticket ORM instance to the public response DTO."""
    resolution_text = None
    escalated = ticket.status == TicketStatus.ESCALATED
    if ticket.resolution:
        resolution_text = ticket.resolution.answer
        escalated = ticket.resolution.escalated or escalated
    customer = ticket.customer
    return TicketResponse(
        id=ticket.id,
        customer_id=ticket.customer_id,
        customer_email=customer.email if customer else None,
        customer_name=customer.name if customer else None,
        subject=ticket.subject,
        description=ticket.description,
        status=ticket.status,
        intent=ticket.intent,
        escalated_at=ticket.escalated_at,
        resolution=resolution_text,
        escalated=escalated,
        order_id=ticket.order_id,
        order=order_to_api_summary(ticket.order) if ticket.order is not None else None,
        last_message_at=ticket.last_message_at,
        assigned_agent=ticket.assigned_agent,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


def ticket_to_summary(ticket: Ticket) -> TicketSummary:
    """Map a ticket to a list-row DTO."""
    customer = ticket.customer
    escalated = ticket.status == TicketStatus.ESCALATED
    if ticket.resolution:
        escalated = ticket.resolution.escalated or escalated
    return TicketSummary(
        id=ticket.id,
        customer_id=ticket.customer_id,
        customer_email=customer.email if customer else None,
        customer_name=customer.name if customer else None,
        subject=ticket.subject,
        status=ticket.status,
        intent=ticket.intent,
        escalated=escalated,
        escalated_at=ticket.escalated_at,
        last_message_at=ticket.last_message_at,
        assigned_agent=ticket.assigned_agent,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


async def list_tickets(
    session: AsyncSession,
    *,
    status: TicketStatus | None = None,
    intent: TicketIntent | None = None,
    escalated: bool | None = None,
    q: str | None = None,
    customer_email: str | None = None,
    owner_id: uuid.UUID | None = None,
    limit: int = 20,
    offset: int = 0,
    order: Literal["desc", "asc"] = "desc",
    sort: Literal["created_at", "last_message_at"] = "created_at",
) -> TicketListResponse:
    """Return a filtered, paginated ticket list."""
    filters = _ticket_filters(
        status=status,
        intent=intent,
        escalated=escalated,
        q=q,
        customer_email=customer_email,
        owner_id=owner_id,
    )
    count_stmt = select(func.count()).select_from(Ticket).join(Ticket.customer).where(*filters)
    total = int((await session.execute(count_stmt)).scalar_one())

    sort_col = Ticket.last_message_at if sort == "last_message_at" else Ticket.created_at
    order_col = sort_col.desc().nulls_last() if order == "desc" else sort_col.asc().nulls_last()
    stmt: Select[tuple[Ticket]] = (
        select(Ticket)
        .join(Ticket.customer)
        .options(selectinload(Ticket.customer), selectinload(Ticket.resolution))
        .where(*filters)
        .order_by(order_col)
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(stmt)).scalars().unique().all()
    return TicketListResponse(
        items=[ticket_to_summary(ticket) for ticket in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


async def list_escalations(
    session: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
) -> TicketListResponse:
    """Return escalated tickets oldest-first (support queue)."""
    filters = [Ticket.status == TicketStatus.ESCALATED]
    count_stmt = select(func.count()).select_from(Ticket).where(*filters)
    total = int((await session.execute(count_stmt)).scalar_one())
    stmt = (
        select(Ticket)
        .options(selectinload(Ticket.customer), selectinload(Ticket.resolution))
        .where(*filters)
        .order_by(Ticket.escalated_at.asc().nulls_last(), Ticket.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(stmt)).scalars().unique().all()
    return TicketListResponse(
        items=[ticket_to_summary(ticket) for ticket in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


async def persist_graph_result(
    session: AsyncSession,
    ticket: Ticket,
    result: dict[str, Any],
    recorder: TraceRecorder,
    *,
    started_at: float,
    error: str | None = None,
) -> ResolutionResponse:
    """Persist ticket resolution and flush buffered agent events."""
    interrupt_payload = extract_interrupt_payload(result)
    awaiting_human = interrupt_payload is not None
    escalated = awaiting_human or bool(result.get("needs_human"))

    intent_str = result.get("intent") or "unknown"
    try:
        ticket.intent = TicketIntent(intent_str)
    except ValueError:
        ticket.intent = TicketIntent.UNKNOWN
        intent_str = ticket.intent.value

    if awaiting_human or escalated:
        ticket.status = TicketStatus.ESCALATED
        ticket.escalated_at = ticket.escalated_at or datetime.now(UTC)
    elif error:
        ticket.status = TicketStatus.OPEN
    elif ticket.status != TicketStatus.CLOSED:
        # Keep the conversation open until the customer or an agent confirms.
        ticket.status = TicketStatus.IN_PROGRESS

    if interrupt_payload:
        raw_answer = str(interrupt_payload.get("draft_answer") or "").strip()
    else:
        raw_answer = result.get("draft_answer") or (
            "No answer generated." if not error else str(error)
        )
    answer = sanitize_customer_answer(str(raw_answer))
    if not answer:
        if awaiting_human or escalated:
            answer = CUSTOMER_ESCALATION_MESSAGE
        elif error:
            answer = str(error)
        else:
            answer = "No answer generated."

    confidence = result.get("confidence")
    await _upsert_resolution(session, ticket, answer, escalated, confidence)

    recorder.record_tool_results(result.get("tool_results"))
    run = await _flush_run(
        session,
        ticket,
        recorder,
        intent=intent_str,
        confidence=confidence,
        escalated=escalated,
        awaiting_human=awaiting_human,
        started_at=started_at,
        error=error,
    )
    history = await list_messages(session, ticket.id)
    last = history[-1] if history else None
    if should_persist_assistant_message(last, answer):
        await append_message(
            session,
            ticket,
            TicketMessageRole.ASSISTANT,
            answer,
            agent_run_id=run.id,
        )

    if escalated:
        get_metrics().increment("escalations")

    return ResolutionResponse(
        ticket_id=ticket.id,
        answer=answer,
        intent=intent_str,
        confidence=confidence,
        escalated=escalated,
        awaiting_human=awaiting_human,
        run_id=run.id,
        tool_results=result.get("tool_results") or [],
        retrieved_context=result.get("retrieved_context") or [],
        interrupt_payload=interrupt_payload,
    )


CLOSE_SYSTEM_MESSAGE = "Conversa encerrada pelo atendente."
CONFIRM_SYSTEM_MESSAGE = "Você marcou esta conversa como resolvida."


async def close_ticket(
    session: AsyncSession, ticket: Ticket, reason: str | None
) -> tuple[Ticket, TicketMessage]:
    """Mark a ticket closed without resuming the graph.

    Clears human assignment and appends a customer-visible system notice.
    """
    if ticket.status == TicketStatus.CLOSED:
        raise TicketConflictError(str(ticket.id), "Ticket is already closed")
    was_escalated = ticket.status == TicketStatus.ESCALATED
    ticket.status = TicketStatus.CLOSED
    ticket.assigned_agent = None
    if reason:
        note = f"Closed by agent. {reason}"
        if ticket.resolution is None:
            ticket.resolution = Resolution(
                ticket_id=ticket.id,
                answer=note,
                escalated=was_escalated,
                confidence=None,
            )
        else:
            ticket.resolution.answer = f"{ticket.resolution.answer}\n\n{note}"
    await session.flush()
    message = await append_message(session, ticket, TicketMessageRole.SYSTEM, CLOSE_SYSTEM_MESSAGE)
    # Re-load relationships: flush expires `updated_at` (onupdate) and lazy IO
    # in `ticket_to_response` raises MissingGreenlet under AsyncSession.
    reloaded = await get_ticket_or_404(session, ticket.id)
    return reloaded, message


async def confirm_resolution(
    session: AsyncSession, ticket: Ticket
) -> tuple[Ticket, TicketMessage | None]:
    """Mark a ticket resolved after the customer confirms the answer helped."""
    if ticket.status == TicketStatus.CLOSED:
        raise TicketConflictError(str(ticket.id), "Ticket is already closed")
    if ticket.status == TicketStatus.RESOLVED:
        return ticket, None
    ticket.status = TicketStatus.RESOLVED
    await session.flush()
    message = await append_message(
        session,
        ticket,
        TicketMessageRole.SYSTEM,
        CONFIRM_SYSTEM_MESSAGE,
    )
    reloaded = await get_ticket_or_404(session, ticket.id)
    return reloaded, message


async def list_runs(session: AsyncSession, ticket_id: uuid.UUID) -> list[AgentRun]:
    """Return agent runs for a ticket, newest first."""
    await get_ticket_or_404(session, ticket_id)
    result = await session.execute(
        select(AgentRun).where(AgentRun.ticket_id == ticket_id).order_by(AgentRun.created_at.desc())
    )
    return list(result.scalars().all())


async def list_run_events(
    session: AsyncSession, run_id: uuid.UUID
) -> tuple[AgentRun, list[AgentEvent]]:
    """Return events for a run, or raise 404."""
    result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
    run = result.scalar_one_or_none()
    if run is None:
        raise RunNotFoundError(str(run_id))
    events = await session.execute(
        select(AgentEvent).where(AgentEvent.run_id == run_id).order_by(AgentEvent.sequence.asc())
    )
    return run, list(events.scalars().all())


def run_to_response(run: AgentRun) -> AgentRunResponse:
    """Map an agent run to the public DTO."""
    return AgentRunResponse(
        id=run.id,
        ticket_id=run.ticket_id,
        thread_id=run.thread_id,
        status=run.status,
        intent=run.intent,
        confidence=run.confidence,
        escalated=run.escalated,
        total_latency_ms=run.total_latency_ms,
        error=run.error,
        created_at=run.created_at,
    )


def event_to_response(event: AgentEvent) -> AgentEventResponse:
    """Map an agent event to the public DTO."""
    return AgentEventResponse(
        id=event.id,
        run_id=event.run_id,
        sequence=event.sequence,
        event_type=event.event_type,
        name=event.name,
        input=event.input,
        output=event.output,
        latency_ms=event.latency_ms,
        error=event.error,
        created_at=event.created_at,
    )


def _ticket_filters(
    *,
    status: TicketStatus | None,
    intent: TicketIntent | None,
    escalated: bool | None,
    q: str | None,
    customer_email: str | None,
    owner_id: uuid.UUID | None = None,
) -> list[Any]:
    """Build SQLAlchemy filter clauses for ticket listing."""
    filters: list[Any] = []
    if owner_id is not None:
        filters.append(Ticket.customer_id == owner_id)
    if status is not None:
        filters.append(Ticket.status == status)
    if intent is not None:
        filters.append(Ticket.intent == intent)
    if escalated is True:
        filters.append(Ticket.status == TicketStatus.ESCALATED)
    elif escalated is False:
        filters.append(Ticket.status != TicketStatus.ESCALATED)
    if customer_email:
        filters.append(Customer.email.ilike(customer_email))
    if q:
        pattern = f"%{q}%"
        filters.append(
            or_(
                Ticket.subject.ilike(pattern),
                Ticket.description.ilike(pattern),
                Customer.email.ilike(pattern),
                Customer.name.ilike(pattern),
            )
        )
    return filters


async def _upsert_resolution(
    session: AsyncSession,
    ticket: Ticket,
    answer: str,
    escalated: bool,
    confidence: float | None,
) -> Resolution:
    """Create or update the ticket resolution row."""
    existing = await session.execute(select(Resolution).where(Resolution.ticket_id == ticket.id))
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
    return resolution


async def _flush_run(
    session: AsyncSession,
    ticket: Ticket,
    recorder: TraceRecorder,
    *,
    intent: str | None,
    confidence: float | None,
    escalated: bool,
    awaiting_human: bool,
    started_at: float,
    error: str | None,
) -> AgentRun:
    """Persist the buffered trace as an AgentRun plus AgentEvent rows."""
    if error:
        status = AgentRunStatus.FAILED
    elif awaiting_human:
        status = AgentRunStatus.AWAITING_HUMAN
    else:
        status = AgentRunStatus.COMPLETED

    run = AgentRun(
        ticket_id=ticket.id,
        thread_id=str(ticket.id),
        status=status,
        intent=intent,
        confidence=confidence,
        escalated=escalated,
        total_latency_ms=(time.perf_counter() - started_at) * 1000,
        error=error,
    )
    session.add(run)
    await session.flush()

    for buffered in recorder.events:
        session.add(
            AgentEvent(
                run_id=run.id,
                sequence=buffered.sequence,
                event_type=buffered.event_type,
                name=buffered.name,
                input=buffered.input,
                output=buffered.output,
                latency_ms=buffered.latency_ms,
                error=buffered.error,
            )
        )
    await session.flush()
    return run


def assert_ticket_owner(ticket: Ticket, customer: Customer | None) -> None:
    """Reject portal access to another customer's ticket."""
    if customer is None:
        return
    if ticket.customer_id != customer.id:
        raise TicketOwnershipError(str(ticket.id))


def message_to_response(message: TicketMessage) -> ChatMessageResponse:
    """Map a chat message to the public DTO."""
    return ChatMessageResponse(
        id=message.id,
        ticket_id=message.ticket_id,
        role=message.role.value,
        content=message.content,
        agent_run_id=message.agent_run_id,
        created_at=message.created_at,
    )


async def append_message(
    session: AsyncSession,
    ticket: Ticket,
    role: TicketMessageRole,
    content: str,
    *,
    agent_run_id: uuid.UUID | None = None,
    extra: dict[str, Any] | None = None,
) -> TicketMessage:
    """Persist one conversation turn and bump inbox ordering."""
    message = TicketMessage(
        ticket_id=ticket.id,
        role=role,
        content=content,
        agent_run_id=agent_run_id,
        extra=extra,
    )
    session.add(message)
    ticket.last_message_at = datetime.now(UTC)
    if role != TicketMessageRole.SYSTEM:
        if not ticket.description:
            ticket.description = content
        if ticket.subject in {"", "Support chat", "Nova conversa"}:
            ticket.subject = content.strip().splitlines()[0][:80]
    await session.flush()
    await session.refresh(message, attribute_names=["created_at"])
    return message


async def list_messages(session: AsyncSession, ticket_id: uuid.UUID) -> list[TicketMessage]:
    """Return conversation history oldest-first."""
    result = await session.execute(
        select(TicketMessage)
        .where(TicketMessage.ticket_id == ticket_id)
        .order_by(TicketMessage.created_at.asc())
    )
    return list(result.scalars().all())


def should_persist_assistant_message(last: TicketMessage | None, answer: str) -> bool:
    """Skip a second bubble when the human turn already stored this text."""
    text = answer.strip()
    if not text or last is None:
        return bool(text)
    if last.role not in {TicketMessageRole.ASSISTANT, TicketMessageRole.HUMAN_AGENT}:
        return True
    return last.content.strip() != text


async def assign_agent(session: AsyncSession, ticket: Ticket, agent: str) -> Ticket:
    """Record human takeover on the ticket."""
    ticket.assigned_agent = agent
    await session.flush()
    return await get_ticket_or_404(session, ticket.id)
