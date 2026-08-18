"""Resolve the portal customer from the X-Customer-Email header."""

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import SessionDep
from app.api.exceptions import CustomerNotFoundError
from app.models.customer import Customer

CUSTOMER_EMAIL_HEADER = "X-Customer-Email"


async def resolve_customer_by_email(session: AsyncSession, email: str) -> Customer:
    """Load a customer by case-insensitive email.

    Args:
        session: Database session.
        email: Login email from the portal.

    Returns:
        Matching customer row.

    Raises:
        CustomerNotFoundError: When no customer uses that email.
    """
    normalized = email.strip().lower()
    result = await session.execute(
        select(Customer).where(func.lower(Customer.email) == normalized)
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        raise CustomerNotFoundError(normalized)
    return customer


async def get_optional_customer(
    session: SessionDep,
    x_customer_email: Annotated[str | None, Header()] = None,
) -> Customer | None:
    """Return the portal customer when the identity header is present."""
    if not x_customer_email or not x_customer_email.strip():
        return None
    return await resolve_customer_by_email(session, x_customer_email)


async def get_required_customer(
    customer: Annotated[Customer | None, Depends(get_optional_customer)],
) -> Customer:
    """Require a valid portal customer header."""
    if customer is None:
        raise CustomerNotFoundError("missing")
    return customer


OptionalCustomerDep = Annotated[Customer | None, Depends(get_optional_customer)]
CustomerDep = Annotated[Customer, Depends(get_required_customer)]
