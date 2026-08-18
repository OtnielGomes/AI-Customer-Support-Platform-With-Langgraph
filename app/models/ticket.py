"""Ticket ORM model."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.persistence import Base

if TYPE_CHECKING:
    from app.models.agent_run import AgentRun
    from app.models.customer import Customer
    from app.models.order import Order
    from app.models.resolution import Resolution
    from app.models.ticket_message import TicketMessage


class TicketStatus(enum.StrEnum):
    """Lifecycle status of a support ticket."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    CLOSED = "closed"


class TicketIntent(enum.StrEnum):
    """Classified intent for routing."""

    BILLING = "billing"
    LOGISTICS = "logistics"
    ACCOUNT = "account"
    UNKNOWN = "unknown"


class Ticket(Base):
    """Support ticket submitted by a customer."""

    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id"),
        index=True,
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id"),
        nullable=True,
        index=True,
    )
    subject: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status", values_callable=lambda x: [e.value for e in x]),
        default=TicketStatus.OPEN,
    )
    intent: Mapped[TicketIntent | None] = mapped_column(
        Enum(TicketIntent, name="ticket_intent", values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    assigned_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    customer: Mapped["Customer"] = relationship(back_populates="tickets")
    order: Mapped["Order | None"] = relationship(back_populates="tickets")
    resolution: Mapped["Resolution | None"] = relationship(back_populates="ticket", uselist=False)
    agent_runs: Mapped[list["AgentRun"]] = relationship(back_populates="ticket")
    messages: Mapped[list["TicketMessage"]] = relationship(
        back_populates="ticket",
        order_by="TicketMessage.created_at",
    )
