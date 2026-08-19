"""Unit tests for portal identity, chat bus, and identity-first prompts."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.agents.prompts import IDENTITY_BLOCK, compose_worker_prompt, format_orders_summary
from app.api.exceptions import TicketOwnershipError
from app.services.chat_bus import decode_chat_event, encode_chat_event, ticket_channel
from app.services.ticket_service import assert_ticket_owner


def test_ticket_channel_name() -> None:
    """Redis fan-out uses ticket:{id}:events."""
    assert ticket_channel("abc") == "ticket:abc:events"


def test_chat_event_roundtrip() -> None:
    """Published payloads decode back to the same event envelope."""
    raw = encode_chat_event("token", {"text": "Olá"})
    parsed = decode_chat_event(raw)
    assert parsed["event"] == "token"
    assert parsed["data"]["text"] == "Olá"


def test_assert_ticket_owner_rejects_cross_customer() -> None:
    """Portal customers cannot open another customer's ticket."""
    ticket = SimpleNamespace(id=uuid4(), customer_id=uuid4())
    other = SimpleNamespace(id=uuid4())
    with pytest.raises(TicketOwnershipError):
        assert_ticket_owner(ticket, other)
    assert_ticket_owner(ticket, None)
    assert_ticket_owner(ticket, SimpleNamespace(id=ticket.customer_id))


def test_single_order_summary_tells_agent_not_to_ask() -> None:
    """One known order must be used without asking for ORD-xxxxx."""
    text = format_orders_summary(
        [
            {
                "public_id": "ORD-01001",
                "status": "delivered",
                "total_amount": "199.90",
                "currency": "BRL",
                "created_at": "2026-01-10T00:00:00+00:00",
            }
        ]
    )
    assert "ORD-01001" in text
    assert "single order" in text.lower()


def test_compose_worker_prompt_includes_identity_block() -> None:
    """Domain prompts must inherit identity-first instructions."""
    prompt = compose_worker_prompt(
        "You are billing.",
        customer_name="Ana Costa",
        customer_tier="gold",
        account_status="active",
        orders_summary=[
            {
                "public_id": "ORD-01002",
                "status": "shipped",
                "total_amount": "10.00",
                "currency": "BRL",
                "created_at": "2026-02-01",
            }
        ],
    )
    assert IDENTITY_BLOCK in prompt
    assert "Ana Costa" in prompt
    assert "Never ask for their email" in prompt
    assert "specialist who will review their problem" in prompt
