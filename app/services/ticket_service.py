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

from app.api.exceptions import RunNotFoundError, TicketConflictError, TicketNotFoundError
from app.api.schemas import (
    AgentEventResponse,
    AgentRunResponse,
    ResolutionResponse,
    TicketListResponse,
    TicketResponse,
    TicketSummary,
)
from app.models.agent_run import AgentEvent, AgentRun, AgentRunStatus
from app.models.customer import Customer
from app.models.resolution import Resolution
from app.models.ticket import Ticket, TicketIntent, TicketStatus
from app.observability.metrics import get_metrics
from app.observability.trace_recorder import TraceRecorder, extract_interrupt_payload

logger = logging.getLogger(__name__)


async def get_ticket_or_404(session: AsyncSession, ticket_id: uuid.UUID) -> Ticket:
    """Load a ticket with customer and resolution, or raise 404."""
    result = await session.execute(
        select(Ticket)
        .options(selectinload(Ticket.resolution), selectinload(Ticket.customer))
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
    limit: int = 20,
    offset: int = 0,
    order: Literal["desc", "asc"] = "desc",
) -> TicketListResponse:
    """Return a filtered, paginated ticket list."""
    filters = _ticket_filters(
        status=status,
        intent=intent,
        escalated=escalated,
        q=q,
        customer_email=customer_email,
    )
    count_stmt = select(func.count()).select_from(Ticket).join(Ticket.customer).where(*filters)
    total = int((await session.execute(count_stmt)).scalar_one())

    order_col = Ticket.created_at.desc() if order == "desc" else Ticket.created_at.asc()
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
        answer = (
            str(interrupt_payload.get("draft_answer") or interrupt_payload.get("reason") or "")
            or "Your request has been escalated to a human support specialist."
        )
    else:
        answer = result.get("draft_answer") or ("No answer generated." if not error else str(error))

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


async def close_ticket(session: AsyncSession, ticket: Ticket, reason: str | None) -> Ticket:
    """Mark a ticket closed without resuming the graph."""
    if ticket.status == TicketStatus.CLOSED:
        raise TicketConflictError(str(ticket.id), "Ticket is already closed")
    was_escalated = ticket.status == TicketStatus.ESCALATED
    ticket.status = TicketStatus.CLOSED
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
    # Re-load relationships: flush expires `updated_at` (onupdate) and lazy IO
    # in `ticket_to_response` raises MissingGreenlet under AsyncSession.
    return await get_ticket_or_404(session, ticket.id)


async def confirm_resolution(session: AsyncSession, ticket: Ticket) -> Ticket:
    """Mark a ticket resolved after the customer confirms the answer helped."""
    if ticket.status == TicketStatus.CLOSED:
        raise TicketConflictError(str(ticket.id), "Ticket is already closed")
    if ticket.status == TicketStatus.RESOLVED:
        return ticket
    ticket.status = TicketStatus.RESOLVED
    await session.flush()
    return await get_ticket_or_404(session, ticket.id)


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
) -> list[Any]:
    """Build SQLAlchemy filter clauses for ticket listing."""
    filters: list[Any] = []
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
