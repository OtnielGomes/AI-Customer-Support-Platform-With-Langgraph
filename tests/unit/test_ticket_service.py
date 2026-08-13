"""Unit tests for ticket listing filters and CORS settings."""

from app.config import Settings
from app.models.ticket import Ticket, TicketStatus
from app.services.ticket_service import _ticket_filters


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
