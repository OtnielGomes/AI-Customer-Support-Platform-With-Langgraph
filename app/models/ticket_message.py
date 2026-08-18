"""Persisted chat messages for a support ticket."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.persistence import Base

if TYPE_CHECKING:
    from app.models.agent_run import AgentRun
    from app.models.ticket import Ticket


class TicketMessageRole(enum.StrEnum):
    """Who authored a chat message."""

    CUSTOMER = "customer"
    ASSISTANT = "assistant"
    HUMAN_AGENT = "human_agent"
    SYSTEM = "system"


class TicketMessage(Base):
    """One turn in a ticket conversation."""

    __tablename__ = "ticket_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id"),
        index=True,
    )
    role: Mapped[TicketMessageRole] = mapped_column(
        Enum(
            TicketMessageRole,
            name="ticket_message_role",
            values_callable=lambda x: [e.value for e in x],
        ),
    )
    content: Mapped[str] = mapped_column(Text)
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id"),
        nullable=True,
        index=True,
    )
    extra: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    ticket: Mapped["Ticket"] = relationship(back_populates="messages")
    agent_run: Mapped["AgentRun | None"] = relationship()
