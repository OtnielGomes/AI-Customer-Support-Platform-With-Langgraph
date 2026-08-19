"""Unit tests for portal customer identity resolution."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.exceptions import CustomerNotFoundError
from app.security.customer_identity import (
    get_optional_customer,
    get_required_customer,
    resolve_customer_by_email,
)


def _session_returning(customer: object | None) -> AsyncMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = customer
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    return session


async def test_resolve_customer_is_case_insensitive() -> None:
    """Login email is normalized before lookup."""
    customer = SimpleNamespace(email="demo@test.com.br")
    session = _session_returning(customer)
    found = await resolve_customer_by_email(session, "  Demo@test.com.br  ")
    assert found is customer


async def test_resolve_customer_unknown_email() -> None:
    """Unknown emails raise a 404 domain error with the normalized address."""
    session = _session_returning(None)
    with pytest.raises(CustomerNotFoundError) as caught:
        await resolve_customer_by_email(session, "Nobody@Test.COM")
    assert "nobody@test.com" in str(caught.value)


async def test_optional_customer_missing_header() -> None:
    """Blank or absent identity headers resolve to None."""
    session = AsyncMock()
    assert await get_optional_customer(session, None) is None
    assert await get_optional_customer(session, "  ") is None
    session.execute.assert_not_called()


async def test_required_customer_missing_identity() -> None:
    """Routes that require a portal customer reject a missing header."""
    with pytest.raises(CustomerNotFoundError):
        await get_required_customer(None)
