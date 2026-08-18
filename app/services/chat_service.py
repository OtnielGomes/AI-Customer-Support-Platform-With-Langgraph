"""Live chat turns: persist messages, stream the graph, fan-out on Redis."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.types import Command
from redis.asyncio import Redis

from app.config import get_settings
from app.models.ticket import Ticket, TicketStatus
from app.models.ticket_message import TicketMessageRole
from app.observability.langfuse import build_langfuse_handler
from app.observability.trace_recorder import TraceRecorder
from app.security.authentication import Principal
from app.services import ticket_service
from app.services.chat_bus import publish_ticket_event
from app.services.graph_runner import (
    build_graph_config,
    invoke_graph,
    snapshot_to_result,
    stream_graph_events,
)

logger = logging.getLogger(__name__)

_TOKEN_SKIP_NODES = {
    "supervisor",
    "input_guardrails",
    "load_customer_context",
    "output_guardrails",
    "resolution",
}


def sse_event(event: str, data: Any) -> dict[str, str]:
    """Build an EventSourceResponse payload."""
    payload = data if isinstance(data, str) else json.dumps(data, default=str)
    return {"event": event, "data": payload}


def _is_llm_token_chunk(message_chunk: Any) -> bool:
    """Return True for incremental LLM chunks, not complete node messages."""
    name = type(message_chunk).__name__
    if not name.endswith("Chunk"):
        return False
    return not getattr(message_chunk, "tool_calls", None)


def _token_text(chunk: Any) -> str:
    """Extract visible LLM text from a messages-mode chunk."""
    message_chunk = chunk
    metadata: dict[str, Any] = {}
    if isinstance(chunk, tuple) and len(chunk) == 2:
        message_chunk, meta = chunk
        if isinstance(meta, dict):
            metadata = meta
    node = str(metadata.get("langgraph_node") or "")
    if node in _TOKEN_SKIP_NODES:
        return ""
    if not _is_llm_token_chunk(message_chunk):
        return ""
    content = getattr(message_chunk, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text") or ""))
        return "".join(parts)
    return ""


def _tool_names(update: dict[str, Any]) -> list[str]:
    """Collect tool names from a graph update dict."""
    names: list[str] = []
    for payload in update.values():
        if not isinstance(payload, dict):
            continue
        for result in payload.get("tool_results") or []:
            if isinstance(result, dict) and result.get("tool"):
                names.append(str(result["tool"]))
    return names


async def _heartbeat_seconds() -> float:
    settings = get_settings()
    return float(max(5, settings.chat_stream_heartbeat_seconds))


async def _with_heartbeats(
    source: AsyncIterator[dict[str, str]],
) -> AsyncIterator[dict[str, str]]:
    """Insert heartbeat SSE events when the upstream is idle."""
    timeout = await _heartbeat_seconds()
    iterator = source.__aiter__()
    while True:
        try:
            item = await asyncio.wait_for(iterator.__anext__(), timeout=timeout)
            yield item
        except TimeoutError:
            yield sse_event("heartbeat", {"ts": datetime.now(timezone.utc).isoformat()})
        except StopAsyncIteration:
            break


async def publish_and_sse(
    redis: Redis,
    ticket_id: str,
    event: str,
    data: Any,
) -> dict[str, str]:
    """Publish to Redis and return the matching SSE packet."""
    await publish_ticket_event(redis, ticket_id, event, data)
    return sse_event(event, data)


async def stream_customer_turn(
    *,
    session,
    redis: Redis,
    graph: Any,
    ticket: Ticket,
    principal: Principal,
    content: str,
) -> AsyncIterator[dict[str, str]]:
    """Persist a customer message, run the graph, and yield SSE events."""
    async def _inner() -> AsyncIterator[dict[str, str]]:
        ticket.status = TicketStatus.IN_PROGRESS
        message = await ticket_service.append_message(
            session,
            ticket,
            TicketMessageRole.CUSTOMER,
            content,
        )
        payload = ticket_service.message_to_response(message).model_dump(mode="json")
        yield await publish_and_sse(redis, str(ticket.id), "message", payload)

        recorder = TraceRecorder()
        started_at = time.perf_counter()
        config = build_graph_config(
            str(ticket.id),
            recorder,
            extra_callbacks=[build_langfuse_handler(str(ticket.id))],
        )
        graph_payload = {
            "ticket_id": str(ticket.id),
            "customer_id": str(ticket.customer_id),
            "messages": [HumanMessage(content=content)],
            "principal_scopes": principal.scopes,
        }
        error: str | None = None
        try:
            async for event in stream_graph_events(graph, graph_payload, config, recorder):
                mode = event.get("mode")
                data = event.get("data")
                if mode == "updates" and isinstance(data, dict):
                    yield await publish_and_sse(
                        redis,
                        str(ticket.id),
                        "status",
                        {"nodes": list(data.keys())},
                    )
                    for name in _tool_names(data):
                        yield await publish_and_sse(
                            redis,
                            str(ticket.id),
                            "tool",
                            {"name": name, "status": "done"},
                        )
                elif mode == "messages":
                    token = _token_text(data)
                    if token:
                        yield await publish_and_sse(
                            redis,
                            str(ticket.id),
                            "token",
                            {"text": token},
                        )
        except Exception as exc:
            logger.exception("Graph stream failed for ticket %s", ticket.id)
            error = str(exc)
            yield await publish_and_sse(
                redis,
                str(ticket.id),
                "error",
                {"error": error},
            )

        result = await _snapshot_or_error(graph, config, error)
        response = await ticket_service.persist_graph_result(
            session,
            ticket,
            result,
            recorder,
            started_at=started_at,
            error=error,
        )
        async for packet in _publish_assistant_and_done(session, redis, ticket, response):
            yield packet

    async for packet in _with_heartbeats(_inner()):
        yield packet


async def stream_human_turn(
    *,
    session,
    redis: Redis,
    graph: Any,
    ticket: Ticket,
    principal: Principal,
    content: str,
    agent: str,
) -> AsyncIterator[dict[str, str]]:
    """Persist a human reply; resume the graph when it is interrupted."""
    async def _inner() -> AsyncIterator[dict[str, str]]:
        message = await ticket_service.append_message(
            session,
            ticket,
            TicketMessageRole.HUMAN_AGENT,
            content,
            extra={"agent": agent},
        )
        payload = ticket_service.message_to_response(message).model_dump(mode="json")
        yield await publish_and_sse(redis, str(ticket.id), "message", payload)

        recorder = TraceRecorder()
        started_at = time.perf_counter()
        config = build_graph_config(
            str(ticket.id),
            recorder,
            extra_callbacks=[build_langfuse_handler(str(ticket.id))],
        )
        interrupted = await _graph_is_interrupted(graph, config)
        if not interrupted:
            yield await publish_and_sse(
                redis,
                str(ticket.id),
                "done",
                {
                    "ticket_id": str(ticket.id),
                    "answer": content,
                    "awaiting_human": False,
                    "escalated": False,
                },
            )
            return

        ticket.status = TicketStatus.IN_PROGRESS
        await session.flush()
        error: str | None = None
        try:
            result = await invoke_graph(
                graph,
                Command(resume={"answer": content, "agent": agent}),
                config,
                recorder,
            )
        except Exception as exc:
            logger.exception("Human resume failed for ticket %s", ticket.id)
            error = str(exc)
            result = {"draft_answer": error, "needs_human": False}
        response = await ticket_service.persist_graph_result(
            session,
            ticket,
            result,
            recorder,
            started_at=started_at,
            error=error,
        )
        async for packet in _publish_assistant_and_done(session, redis, ticket, response):
            yield packet

    async for packet in _with_heartbeats(_inner()):
        yield packet


async def _graph_is_interrupted(graph: Any, config: dict[str, Any]) -> bool:
    """Return True when the checkpoint currently has an interrupt."""
    try:
        snapshot = await graph.aget_state(config)
    except Exception as exc:
        logger.warning("Failed to read graph snapshot: %s", exc)
        return False
    result = snapshot_to_result(snapshot)
    return bool(result.get("__interrupt__"))


async def _snapshot_or_error(graph: Any, config: dict[str, Any], error: str | None) -> dict:
    """Read checkpoint state after a stream, including interrupts."""
    if error:
        return {"draft_answer": error, "needs_human": False}
    try:
        snapshot = await graph.aget_state(config)
    except Exception as exc:
        logger.warning("Failed to read graph snapshot: %s", exc)
        return {"draft_answer": "Stream completed without snapshot.", "needs_human": False}
    return snapshot_to_result(snapshot)


async def _publish_assistant_and_done(
    session,
    redis: Redis,
    ticket: Ticket,
    response: Any,
) -> AsyncIterator[dict[str, str]]:
    """Fan-out the persisted assistant turn plus the done payload."""
    history = await ticket_service.list_messages(session, ticket.id)
    if history and history[-1].role == TicketMessageRole.ASSISTANT:
        yield await publish_and_sse(
            redis,
            str(ticket.id),
            "message",
            ticket_service.message_to_response(history[-1]).model_dump(mode="json"),
        )
    yield await publish_and_sse(
        redis,
        str(ticket.id),
        "done",
        response.model_dump(mode="json"),
    )
