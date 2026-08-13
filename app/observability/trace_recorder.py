"""In-memory callback handler that buffers graph execution events."""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from app.models.agent_run import AgentEventType


def to_jsonable(value: Any) -> Any:
    """Convert arbitrary values into JSON-serializable structures."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item) for item in value]
    if hasattr(value, "model_dump"):
        return to_jsonable(value.model_dump())
    if hasattr(value, "content"):
        return {
            "type": getattr(value, "type", "message"),
            "content": str(value.content),
        }
    return str(value)


class BufferedEvent:
    """Single buffered execution event awaiting persistence."""

    def __init__(
        self,
        sequence: int,
        event_type: AgentEventType,
        name: str,
        input_data: dict[str, Any] | None = None,
        output_data: dict[str, Any] | None = None,
        latency_ms: float | None = None,
        error: str | None = None,
    ) -> None:
        self.sequence = sequence
        self.event_type = event_type
        self.name = name
        self.input = input_data
        self.output = output_data
        self.latency_ms = latency_ms
        self.error = error


class TraceRecorder(BaseCallbackHandler):
    """Buffer LangChain/LangGraph callbacks; persist after the run.

    Nodes must not write to the database. This handler only accumulates
    events in memory. The ticket service flushes them after ``ainvoke``
    or ``astream`` returns.
    """

    def __init__(self) -> None:
        super().__init__()
        self.events: list[BufferedEvent] = []
        self._sequence = 0
        self._starts: dict[str, float] = {}

    def add_event(
        self,
        event_type: AgentEventType,
        name: str,
        *,
        input_data: Any = None,
        output_data: Any = None,
        latency_ms: float | None = None,
        error: str | None = None,
    ) -> BufferedEvent:
        """Append a buffered event and return it."""
        self._sequence += 1
        wrapped_input = _wrap(to_jsonable(input_data)) if input_data is not None else None
        wrapped_output = _wrap(to_jsonable(output_data)) if output_data is not None else None
        event = BufferedEvent(
            sequence=self._sequence,
            event_type=event_type,
            name=name,
            input_data=wrapped_input,
            output_data=wrapped_output,
            latency_ms=latency_ms,
            error=error,
        )
        self.events.append(event)
        return event

    def record_graph_update(self, update: dict[str, Any]) -> None:
        """Record a LangGraph ``stream_mode='updates'`` delta as node events."""
        for node_name, payload in update.items():
            if node_name == "__interrupt__":
                self.add_event(
                    AgentEventType.GUARDRAIL,
                    "interrupt",
                    output_data=payload,
                )
                continue
            self.add_event(AgentEventType.NODE, str(node_name), output_data=payload)

    def record_tool_results(self, tool_results: list[dict[str, Any]] | None) -> None:
        """Backfill tool events from graph state when callbacks missed them."""
        existing = {
            event.name for event in self.events if event.event_type == AgentEventType.TOOL
        }
        for item in tool_results or []:
            name = str(item.get("tool") or "unknown")
            if name in existing:
                continue
            error = item.get("error")
            self.add_event(
                AgentEventType.TOOL,
                name,
                output_data=item.get("result"),
                error=str(error) if error else None,
            )
            existing.add(name)

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Record LLM start time."""
        self._starts[str(run_id)] = time.perf_counter()
        name = (serialized or {}).get("name") or "llm"
        self.add_event(AgentEventType.LLM, str(name), input_data={"prompts": prompts[:3]})

    def on_llm_end(self, response: LLMResult, *, run_id: UUID, **kwargs: Any) -> None:
        """Attach LLM output and latency to the last matching event."""
        latency = _elapsed(self._starts.pop(str(run_id), None))
        generations = []
        for block in response.generations:
            for gen in block:
                generations.append(getattr(gen, "text", str(gen)))
        self._patch_last(
            AgentEventType.LLM,
            output_data={"generations": generations},
            latency_ms=latency,
        )

    def on_llm_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        """Mark LLM event as failed."""
        latency = _elapsed(self._starts.pop(str(run_id), None))
        self._patch_last(AgentEventType.LLM, error=str(error), latency_ms=latency)

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Record tool invocation start."""
        self._starts[str(run_id)] = time.perf_counter()
        name = (serialized or {}).get("name") or kwargs.get("name") or "tool"
        self.add_event(AgentEventType.TOOL, str(name), input_data={"input": input_str})

    def on_tool_end(self, output: Any, *, run_id: UUID, **kwargs: Any) -> None:
        """Attach tool output."""
        latency = _elapsed(self._starts.pop(str(run_id), None))
        self._patch_last(AgentEventType.TOOL, output_data=output, latency_ms=latency)

    def on_tool_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        """Mark tool event as failed."""
        latency = _elapsed(self._starts.pop(str(run_id), None))
        self._patch_last(AgentEventType.TOOL, error=str(error), latency_ms=latency)

    def on_retriever_start(
        self,
        serialized: dict[str, Any],
        query: str,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Record retriever start."""
        self._starts[str(run_id)] = time.perf_counter()
        name = (serialized or {}).get("name") or "retriever"
        self.add_event(AgentEventType.RETRIEVAL, str(name), input_data={"query": query})

    def on_retriever_end(self, documents: SequenceLike, *, run_id: UUID, **kwargs: Any) -> None:
        """Attach retriever documents."""
        latency = _elapsed(self._starts.pop(str(run_id), None))
        count = len(documents) if documents is not None else 0
        self._patch_last(
            AgentEventType.RETRIEVAL,
            output_data={"document_count": count},
            latency_ms=latency,
        )

    def on_chain_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        """Record a chain/node failure."""
        self.add_event(AgentEventType.NODE, "chain_error", error=str(error))

    def _patch_last(
        self,
        event_type: AgentEventType,
        *,
        output_data: Any = None,
        error: str | None = None,
        latency_ms: float | None = None,
    ) -> None:
        """Update the most recent event of the given type."""
        for event in reversed(self.events):
            if event.event_type == event_type:
                if output_data is not None:
                    event.output = _wrap(to_jsonable(output_data))
                if error is not None:
                    event.error = error
                if latency_ms is not None:
                    event.latency_ms = latency_ms
                return


def _wrap(value: Any) -> dict[str, Any]:
    """Ensure JSONB payload is an object."""
    if isinstance(value, dict):
        return value
    return {"value": value}


def _elapsed(started: float | None) -> float | None:
    """Return elapsed milliseconds from a perf_counter start."""
    if started is None:
        return None
    return (time.perf_counter() - started) * 1000


SequenceLike = Any


def extract_interrupt_payload(result: dict[str, Any]) -> dict[str, Any] | None:
    """Return the first interrupt payload from a graph result, if any."""
    interrupts = result.get("__interrupt__")
    if not interrupts:
        return None
    first = interrupts[0]
    value = getattr(first, "value", first)
    if isinstance(value, dict):
        return value
    if value is None:
        return None
    return {"value": value}
