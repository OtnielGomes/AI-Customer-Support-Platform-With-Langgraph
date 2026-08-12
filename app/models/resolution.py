"""Resolution ORM model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.persistence import Base

if TYPE_CHECKING:
    from app.models.ticket import Ticket


class Resolution(Base):
    """Final or interim resolution for a ticket."""

    __tablename__ = "resolutions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id"),
        unique=True,
        index=True,
    )
    answer: Mapped[str] = mapped_column(Text)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    ticket: Mapped["Ticket"] = relationship(back_populates="resolution")
