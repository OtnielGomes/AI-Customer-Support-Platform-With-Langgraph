"""Redis pub/sub fan-out for live ticket chat events."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


def ticket_channel(ticket_id: str) -> str:
    """Return the Redis channel for a ticket conversation."""
    return f"ticket:{ticket_id}:events"


def encode_chat_event(event: str, data: Any) -> str:
    """Serialize a chat event for Redis and SSE."""
    return json.dumps({"event": event, "data": data}, default=str)


def decode_chat_event(payload: str) -> dict[str, Any]:
    """Parse a published chat event."""
    parsed = json.loads(payload)
    if not isinstance(parsed, dict):
        return {"event": "error", "data": {"error": "invalid event"}}
    return parsed


async def publish_ticket_event(redis: Redis, ticket_id: str, event: str, data: Any) -> None:
    """Publish one chat event to subscribers of the ticket channel."""
    await redis.publish(ticket_channel(ticket_id), encode_chat_event(event, data))


async def subscribe_ticket_events(
    redis: Redis,
    ticket_id: str,
    *,
    idle_timeout: float = 15.0,
) -> AsyncIterator[dict[str, Any]]:
    """Yield chat events from the ticket channel until the subscriber closes.

    Uses ``get_message`` with a timeout instead of cancelling ``listen()``.
    ``asyncio.wait_for`` on ``listen()`` kills the pub/sub iterator after one
    idle period, so the SSE stream closes and the UI misses assistant turns.
    """
    pubsub = redis.pubsub()
    await pubsub.subscribe(ticket_channel(ticket_id))
    try:
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=idle_timeout,
            )
            if message is None:
                yield {
                    "event": "heartbeat",
                    "data": {"ts": datetime.now(timezone.utc).isoformat()},
                }
                continue
            raw = message.get("data")
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            if not isinstance(raw, str):
                continue
            try:
                yield decode_chat_event(raw)
            except json.JSONDecodeError:
                logger.warning("Ignoring malformed chat bus payload")
    finally:
        await pubsub.unsubscribe(ticket_channel(ticket_id))
        await pubsub.aclose()
