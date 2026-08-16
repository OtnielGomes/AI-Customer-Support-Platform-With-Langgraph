"""Tests for customer scoping helpers."""

import uuid

from app.tools.context import ToolContext
from app.tools.lookups import scoped_to_customer


def test_scoped_to_customer_allows_matching_id() -> None:
    """Ticket customer can read their own rows."""
    customer_id = uuid.uuid4()
    context = ToolContext(session=None, customer_id=customer_id)  # type: ignore[arg-type]
    assert scoped_to_customer(context, customer_id) is True


def test_scoped_to_customer_blocks_other_customer() -> None:
    """Tools must not return another customer's order."""
    context = ToolContext(session=None, customer_id=uuid.uuid4())  # type: ignore[arg-type]
    assert scoped_to_customer(context, uuid.uuid4()) is False
