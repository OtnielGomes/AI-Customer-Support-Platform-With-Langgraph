"""Unit tests for supervisor routing."""

from app.agents.supervisor import should_route_to_worker


def test_route_billing_high_confidence() -> None:
    """High confidence billing intent should route to worker."""
    assert should_route_to_worker("billing", 0.9) is True


def test_route_low_confidence_escalates() -> None:
    """Low confidence should not route to worker."""
    assert should_route_to_worker("billing", 0.3) is False


def test_route_unknown_intent() -> None:
    """Unknown intent should not route to worker."""
    assert should_route_to_worker("unknown", 0.9) is False
