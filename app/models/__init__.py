"""ORM model package."""

from app.models.customer import Customer
from app.models.kb_chunk import KBChunk
from app.models.resolution import Resolution
from app.models.ticket import Ticket, TicketIntent, TicketStatus

__all__ = [
    "Customer",
    "KBChunk",
    "Resolution",
    "Ticket",
    "TicketIntent",
    "TicketStatus",
]
