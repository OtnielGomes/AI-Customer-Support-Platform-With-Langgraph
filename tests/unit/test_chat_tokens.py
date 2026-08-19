"""Unit tests for live-chat token filtering."""

from langchain_core.messages import AIMessage, AIMessageChunk

from types import SimpleNamespace

from app.services.chat_service import _token_text, customer_turn_runs_graph


def test_token_text_keeps_incremental_chunks() -> None:
    """Worker LLM deltas should stream to the portal."""
    chunk = AIMessageChunk(content="Seu pedido ORD-01001")
    text = _token_text((chunk, {"langgraph_node": "logistics"}))
    assert text == "Seu pedido ORD-01001"


def test_token_text_skips_complete_node_messages() -> None:
    """Node-returned AIMessages must not be appended as extra tokens."""
    message = AIMessage(
        content=(
            "Seu pedido ORD-01001 não está mais a caminho; ele foi entregue "
            "em 2026-08-07 pela Correios."
        )
    )
    assert _token_text((message, {"langgraph_node": "logistics"})) == ""


def test_token_text_skips_guardrail_nodes() -> None:
    """Supervisor and guardrail tokens should not appear in the bubble."""
    chunk = AIMessageChunk(content="internal")
    assert _token_text((chunk, {"langgraph_node": "supervisor"})) == ""
    assert _token_text((chunk, {"langgraph_node": "output_guardrails"})) == ""


def test_customer_turn_skips_graph_after_human_takeover() -> None:
    """A console takeover must silence the AI for later customer messages."""
    owned = SimpleNamespace(assigned_agent="console")
    idle = SimpleNamespace(assigned_agent=None)
    assert customer_turn_runs_graph(owned) is False
    assert customer_turn_runs_graph(idle) is True
