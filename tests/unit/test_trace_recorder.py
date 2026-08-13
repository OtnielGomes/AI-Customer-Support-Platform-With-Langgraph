"""Unit tests for the in-memory trace recorder."""

from types import SimpleNamespace

from app.models.agent_run import AgentEventType
from app.observability.trace_recorder import TraceRecorder, extract_interrupt_payload, to_jsonable


def test_to_jsonable_nested_and_messages() -> None:
    """Convert nested values and message-like objects."""
    message = SimpleNamespace(type="human", content="hello")
    result = to_jsonable({"items": [1, message], "ok": True})
    assert result["ok"] is True
    assert result["items"][0] == 1
    assert result["items"][1]["content"] == "hello"


def test_record_graph_update_creates_node_and_interrupt_events() -> None:
    """Stream updates should become node and guardrail events."""
    recorder = TraceRecorder()
    recorder.record_graph_update(
        {
            "supervisor": {"intent": "billing", "confidence": 0.9},
            "__interrupt__": [{"reason": "low confidence"}],
        }
    )
    names = [event.name for event in recorder.events]
    assert "supervisor" in names
    assert "interrupt" in names
    interrupt = next(event for event in recorder.events if event.name == "interrupt")
    assert interrupt.event_type == AgentEventType.GUARDRAIL


def test_record_tool_results_backfills_missing_tools() -> None:
    """Tool results from graph state should be recorded when callbacks miss them."""
    recorder = TraceRecorder()
    recorder.record_tool_results(
        [
            {"tool": "get_invoice", "result": {"id": "INV-1"}},
            {"tool": "get_invoice", "result": {"id": "INV-2"}},
            {"tool": "request_refund", "error": "denied"},
        ]
    )
    tool_events = [event for event in recorder.events if event.event_type == AgentEventType.TOOL]
    assert len(tool_events) == 2
    refund = next(event for event in tool_events if event.name == "request_refund")
    assert refund.error == "denied"


def test_extract_interrupt_payload_from_object() -> None:
    """Interrupt objects expose a ``value`` attribute."""
    payload = extract_interrupt_payload(
        {"__interrupt__": [SimpleNamespace(value={"reason": "needs human"})]}
    )
    assert payload == {"reason": "needs human"}


def test_extract_interrupt_payload_absent() -> None:
    """Missing interrupt key should return None."""
    assert extract_interrupt_payload({"draft_answer": "ok"}) is None
