"""Run the support graph and collect stream updates for persistence."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Any

from app.observability.trace_recorder import TraceRecorder, extract_interrupt_payload

OnUpdate = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


async def invoke_graph(
    graph: Any,
    payload: Any,
    config: dict[str, Any],
    recorder: TraceRecorder,
    *,
    on_update: OnUpdate | None = None,
) -> dict[str, Any]:
    """Drive the graph via ``astream`` and return a persistable result dict.

    Collects node updates into ``recorder``, then reads the checkpoint snapshot
    so interrupt payloads are available even when ``ainvoke`` is not used.
    """
    async for event in graph.astream(payload, config=config, stream_mode="updates"):
        if isinstance(event, dict):
            recorder.record_graph_update(event)
            if on_update is not None:
                await on_update(event)

    snapshot = await graph.aget_state(config)
    return snapshot_to_result(snapshot)


def snapshot_to_result(snapshot: Any) -> dict[str, Any]:
    """Convert a LangGraph StateSnapshot into a persistable result dict."""
    values = dict(getattr(snapshot, "values", None) or {})
    interrupts = _snapshot_interrupts(snapshot)
    if interrupts:
        values["__interrupt__"] = interrupts
        if not values.get("needs_human"):
            values["needs_human"] = True
        payload_value = extract_interrupt_payload(values)
        if payload_value and not values.get("draft_answer"):
            values["draft_answer"] = payload_value.get("draft_answer") or ""
    return values


async def stream_graph_updates(
    graph: Any,
    payload: Any,
    config: dict[str, Any],
    recorder: TraceRecorder,
) -> AsyncIterator[dict[str, Any]]:
    """Yield graph update events while buffering them on the recorder."""
    async for event in stream_graph_events(graph, payload, config, recorder):
        if event.get("mode") == "updates":
            yield event["data"]


async def stream_graph_events(
    graph: Any,
    payload: Any,
    config: dict[str, Any],
    recorder: TraceRecorder,
) -> AsyncIterator[dict[str, Any]]:
    """Yield ``updates`` and ``messages`` chunks from the compiled graph."""
    async for item in graph.astream(
        payload,
        config=config,
        stream_mode=["updates", "messages"],
    ):
        mode, chunk = _unpack_stream_item(item)
        if mode == "updates" and isinstance(chunk, dict):
            recorder.record_graph_update(chunk)
            yield {"mode": "updates", "data": chunk}
        elif mode == "messages":
            yield {"mode": "messages", "data": chunk}


def _unpack_stream_item(item: Any) -> tuple[str, Any]:
    """Normalize LangGraph stream items across v1 tuples and v2 StreamPart dicts."""
    if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str):
        return item[0], item[1]
    if isinstance(item, dict) and "type" in item and "data" in item:
        return str(item["type"]), item["data"]
    return "updates", item


def build_graph_config(
    ticket_id: str,
    recorder: TraceRecorder,
    extra_callbacks: list[Any] | None = None,
) -> dict[str, Any]:
    """Build LangGraph runnable config with trace callbacks."""
    callbacks: list[Any] = [recorder]
    if extra_callbacks:
        callbacks.extend(callback for callback in extra_callbacks if callback is not None)
    return {
        "configurable": {"thread_id": ticket_id},
        "callbacks": callbacks,
    }


def _snapshot_interrupts(snapshot: Any) -> list[Any]:
    """Extract interrupt objects from a StateSnapshot."""
    interrupts = getattr(snapshot, "interrupts", None)
    if interrupts:
        return list(interrupts)
    tasks = getattr(snapshot, "tasks", None) or ()
    collected: list[Any] = []
    for task in tasks:
        collected.extend(getattr(task, "interrupts", ()) or ())
    return collected
