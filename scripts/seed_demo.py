"""Seed demo customer and ticket data."""

import asyncio
import logging
import sys
import uuid

from sqlalchemy import select

from app.models.customer import Customer
from app.models.ticket import Ticket, TicketStatus
from app.persistence import get_session_factory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Create demo customer and ticket if not exists."""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(Customer).where(Customer.email == "demo@example.com")
        )
        customer = result.scalar_one_or_none()
        if customer is None:
            customer = Customer(email="demo@example.com", name="Demo Customer")
            session.add(customer)
            await session.flush()
            logger.info("Created demo customer: %s", customer.id)

        ticket_result = await session.execute(
            select(Ticket).where(Ticket.customer_id == customer.id)
        )
        ticket = ticket_result.scalar_one_or_none()
        if ticket is None:
            ticket = Ticket(
                id=uuid.UUID("00000000-0000-4000-8000-000000000001"),
                customer_id=customer.id,
                subject="Refund request for INV-1001",
                description="I was charged twice for invoice INV-1001. Please refund the duplicate charge.",
                status=TicketStatus.OPEN,
            )
            session.add(ticket)
            logger.info("Created demo ticket: %s", ticket.id)

        await session.commit()
    logger.info("Seed complete")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)
    else:
        asyncio.run(main())
