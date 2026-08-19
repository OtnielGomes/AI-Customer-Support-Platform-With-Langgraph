"""Unit tests for Redis chat-bus publish/subscribe."""

import asyncio
from typing import Any

from app.services.chat_bus import (
    publish_ticket_event,
    subscribe_ticket_events,
    ticket_channel,
)


class FakePubSub:
    """Minimal pub/sub double for ``subscribe_ticket_events``."""

    def __init__(self) -> None:
        self.queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        self.subscribed: list[str] = []

    async def subscribe(self, channel: str) -> None:
        self.subscribed.append(channel)

    async def unsubscribe(self, channel: str) -> None:
        if channel in self.subscribed:
            self.subscribed.remove(channel)

    async def aclose(self) -> None:
        return None

    async def get_message(self, ignore_subscribe_messages: bool = True, timeout: float = 15.0):
        del ignore_subscribe_messages
        try:
            return await asyncio.wait_for(self.queue.get(), timeout=timeout)
        except TimeoutError:
            return None


class FakeRedis:
    """In-memory Redis that delivers published payloads to one subscriber."""

    def __init__(self) -> None:
        self.pubsub_obj = FakePubSub()
        self.published: list[tuple[str, str]] = []

    def pubsub(self) -> FakePubSub:
        return self.pubsub_obj

    async def publish(self, channel: str, payload: str) -> None:
        self.published.append((channel, payload))
        await self.pubsub_obj.queue.put({"data": payload})


async def test_subscribe_emits_heartbeat_then_event() -> None:
    """Idle timeout yields a heartbeat; a publish yields the original event."""
    redis = FakeRedis()
    events: list[dict[str, Any]] = []

    async def consume() -> None:
        async for item in subscribe_ticket_events(redis, "t1", idle_timeout=0.05):
            events.append(item)
            if item["event"] == "token":
                break

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.08)
    await publish_ticket_event(redis, "t1", "token", {"text": "oi"})
    await asyncio.wait_for(task, timeout=1)
    assert events[0]["event"] == "heartbeat"
    assert events[-1] == {"event": "token", "data": {"text": "oi"}}
    assert redis.published[0][0] == ticket_channel("t1")
