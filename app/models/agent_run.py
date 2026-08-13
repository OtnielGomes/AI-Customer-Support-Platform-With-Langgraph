"""Agent run and event ORM models for persisted graph traces."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.persistence import Base

if TYPE_CHECKING:
    from app.models.ticket import Ticket


class AgentRunStatus(enum.StrEnum):
    """Lifecycle of a single graph invocation."""

    RUNNING = "running"
    COMPLETED = "completed"
    AWAITING_HUMAN = "awaiting_human"
    FAILED = "failed"


class AgentEventType(enum.StrEnum):
    """Kind of recorded execution event."""

    NODE = "node"
    TOOL = "tool"
    LLM = "llm"
    RETRIEVAL = "retrieval"
    GUARDRAIL = "guardrail"


class AgentRun(Base):
    """One invocation of the support graph for a ticket."""

    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id"),
        index=True,
    )
    thread_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[AgentRunStatus] = mapped_column(
        Enum(
            AgentRunStatus,
            name="agent_run_status",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=AgentRunStatus.RUNNING,
    )
    intent: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    total_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    ticket: Mapped["Ticket"] = relationship(back_populates="agent_runs")
    events: Mapped[list["AgentEvent"]] = relationship(
        back_populates="run",
        order_by="AgentEvent.sequence",
    )


class AgentEvent(Base):
    """Buffered execution event persisted after a graph run."""

    __tablename__ = "agent_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id"),
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[AgentEventType] = mapped_column(
        Enum(
            AgentEventType,
            name="agent_event_type",
            values_callable=lambda x: [e.value for e in x],
        ),
    )
    name: Mapped[str] = mapped_column(String(255))
    input: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    run: Mapped["AgentRun"] = relationship(back_populates="events")
