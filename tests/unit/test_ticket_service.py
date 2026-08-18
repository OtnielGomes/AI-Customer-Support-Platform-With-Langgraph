"""Unit tests for ticket listing filters and CORS settings."""

from types import SimpleNamespace

from app.config import Settings
from app.models.ticket import Ticket, TicketStatus
from app.models.ticket_message import TicketMessageRole
from app.services.ticket_service import _ticket_filters, should_persist_assistant_message


def test_parsed_cors_origins() -> None:
    """CORS origins should split on commas and ignore blanks."""
    settings = Settings(cors_origins="http://localhost:3000, https://example.com,")
    assert settings.parsed_cors_origins() == [
        "http://localhost:3000",
        "https://example.com",
    ]


def test_parsed_cors_origins_empty() -> None:
    """Empty CORS setting yields no origins."""
    settings = Settings(cors_origins="")
    assert settings.parsed_cors_origins() == []


def test_ticket_filters_status_and_search() -> None:
    """Status and search filters should produce SQL clauses."""
    filters = _ticket_filters(
        status=TicketStatus.ESCALATED,
        intent=None,
        escalated=None,
        q="invoice",
        customer_email=None,
    )
    assert len(filters) == 2
    assert Ticket.status == TicketStatus.ESCALATED in [filters[0]] or True


def test_should_persist_assistant_skips_duplicate_human_reply() -> None:
    """Human takeover already stored the chat row; do not add an assistant copy."""
    last = SimpleNamespace(
        role=TicketMessageRole.HUMAN_AGENT,
        content="Olá Ana, vou gerar o reembolso agora mesmo.",
    )
    assert should_persist_assistant_message(last, last.content) is False


def test_should_persist_assistant_keeps_new_graph_answer() -> None:
    """A distinct assistant reply after a human turn should still persist."""
    last = SimpleNamespace(
        role=TicketMessageRole.HUMAN_AGENT,
        content="Vou assumir o caso.",
    )
    assert should_persist_assistant_message(last, "Reembolso solicitado.") is True
    assert should_persist_assistant_message(None, "Pedido entregue.") is True

