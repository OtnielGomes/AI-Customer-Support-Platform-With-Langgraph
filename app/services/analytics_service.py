"""SQL aggregations for the support console analytics views."""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Date

from app.api.schemas import (
    AnalyticsOverviewResponse,
    AnalyticsToolsResponse,
    ToolAnalyticsItem,
    VolumePoint,
)
from app.models.agent_run import AgentEvent, AgentEventType, AgentRun
from app.models.ticket import Ticket, TicketIntent, TicketStatus

logger = logging.getLogger(__name__)

OVERVIEW_CACHE_KEY = "analytics:overview"
TOOLS_CACHE_KEY = "analytics:tools"
CACHE_TTL_SECONDS = 30


async def get_overview(
    session: AsyncSession,
    redis: Redis | None = None,
) -> AnalyticsOverviewResponse:
    """Return ticket volume, status mix, escalation rate, and daily counts."""
    cached = await _cache_get(redis, OVERVIEW_CACHE_KEY)
    if cached is not None:
        return AnalyticsOverviewResponse.model_validate(cached)

    total = int((await session.execute(select(func.count()).select_from(Ticket))).scalar_one())

    status_rows = (
        await session.execute(select(Ticket.status, func.count()).group_by(Ticket.status))
    ).all()
    by_status = {status.value: 0 for status in TicketStatus}
    for status, count in status_rows:
        by_status[status.value if hasattr(status, "value") else str(status)] = int(count)

    intent_rows = (
        await session.execute(select(Ticket.intent, func.count()).group_by(Ticket.intent))
    ).all()
    by_intent = {intent.value: 0 for intent in TicketIntent}
    by_intent["none"] = 0
    for intent, count in intent_rows:
        if intent is None:
            by_intent["none"] = int(count)
        else:
            key = intent.value if hasattr(intent, "value") else str(intent)
            by_intent[key] = int(count)

    escalated_count = by_status.get(TicketStatus.ESCALATED.value, 0)
    escalation_rate = (escalated_count / total) if total else 0.0

    avg_confidence = (
        await session.execute(
            select(func.avg(AgentRun.confidence)).where(AgentRun.confidence.is_not(None))
        )
    ).scalar_one()

    avg_resolution_ms = (
        await session.execute(
            select(func.avg(AgentRun.total_latency_ms)).where(
                AgentRun.total_latency_ms.is_not(None)
            )
        )
    ).scalar_one()

    day_expr = cast(func.timezone("UTC", Ticket.created_at), Date)
    volume_rows = (
        await session.execute(
            select(day_expr.label("day"), func.count())
            .group_by(day_expr)
            .order_by(day_expr.asc())
        )
    ).all()
    volume_by_day = [
        VolumePoint(date=_as_iso_date(day), count=int(count)) for day, count in volume_rows
    ]

    response = AnalyticsOverviewResponse(
        total_tickets=total,
        by_status=by_status,
        by_intent=by_intent,
        escalation_rate=round(escalation_rate, 4),
        avg_confidence=float(avg_confidence) if avg_confidence is not None else None,
        avg_resolution_ms=float(avg_resolution_ms) if avg_resolution_ms is not None else None,
        volume_by_day=volume_by_day,
    )
    await _cache_set(redis, OVERVIEW_CACHE_KEY, response.model_dump(mode="json"))
    return response


async def get_tool_analytics(
    session: AsyncSession,
    redis: Redis | None = None,
) -> AnalyticsToolsResponse:
    """Return per-tool call counts, error rate, and latency percentiles."""
    cached = await _cache_get(redis, TOOLS_CACHE_KEY)
    if cached is not None:
        return AnalyticsToolsResponse.model_validate(cached)

    error_case = case((AgentEvent.error.is_not(None), 1), else_=0)
    p95 = func.percentile_cont(0.95).within_group(AgentEvent.latency_ms)
    stmt = (
        select(
            AgentEvent.name,
            func.count().label("calls"),
            func.sum(error_case).label("errors"),
            func.avg(AgentEvent.latency_ms).label("avg_latency_ms"),
            p95.label("p95_latency_ms"),
        )
        .where(AgentEvent.event_type == AgentEventType.TOOL)
        .group_by(AgentEvent.name)
        .order_by(func.count().desc())
    )
    rows = (await session.execute(stmt)).all()
    items: list[ToolAnalyticsItem] = []
    for name, calls, errors, avg_latency, p95_latency in rows:
        call_count = int(calls)
        error_count = int(errors or 0)
        items.append(
            ToolAnalyticsItem(
                name=name,
                calls=call_count,
                errors=error_count,
                error_rate=round((error_count / call_count) if call_count else 0.0, 4),
                avg_latency_ms=float(avg_latency) if avg_latency is not None else None,
                p95_latency_ms=float(p95_latency) if p95_latency is not None else None,
            )
        )
    response = AnalyticsToolsResponse(items=items)
    await _cache_set(redis, TOOLS_CACHE_KEY, response.model_dump(mode="json"))
    return response


def _as_iso_date(value: Any) -> str:
    """Normalize a SQL date/datetime to ISO date string."""
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]


async def _cache_get(redis: Redis | None, key: str) -> dict[str, Any] | None:
    """Read a JSON cache entry from Redis."""
    if redis is None:
        return None
    try:
        raw = await redis.get(key)
    except Exception as exc:
        logger.warning("Analytics cache read failed for %s: %s", key, exc)
        return None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def _cache_set(redis: Redis | None, key: str, payload: dict[str, Any]) -> None:
    """Write a JSON cache entry with a short TTL."""
    if redis is None:
        return
    try:
        await redis.set(key, json.dumps(payload), ex=CACHE_TTL_SECONDS)
    except Exception as exc:
        logger.warning("Analytics cache write failed for %s: %s", key, exc)
