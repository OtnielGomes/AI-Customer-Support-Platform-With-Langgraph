"""API request/response schemas."""

import uuid
from datetime import datetime
from typing import Any

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from app.models.ticket import TicketIntent, TicketStatus


class CreateTicketRequest(BaseModel):
    """Request to create a support ticket."""

    customer_email: str = Field(min_length=3, max_length=255)
    customer_name: str = Field(min_length=1, max_length=255)
    subject: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1, max_length=10000)


class MessageInput(BaseModel):
    """Single message in a resolve request."""

    role: str = Field(pattern="^(user|human)$")
    content: str = Field(min_length=1, max_length=10000)


class ResolveRequest(BaseModel):
    """Request to resolve a ticket via the support graph."""

    messages: list[MessageInput] = Field(min_length=1)

    def to_langchain_messages(self) -> list[HumanMessage]:
        """Convert to LangChain human messages."""
        return [
            HumanMessage(content=msg.content)
            for msg in self.messages
            if msg.role in ("user", "human")
        ]


class ResolutionResponse(BaseModel):
    """Graph resolution result."""

    ticket_id: uuid.UUID
    answer: str
    intent: str | None = None
    confidence: float | None = None
    escalated: bool = False
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    retrieved_context: list[dict[str, Any]] = Field(default_factory=list)


class TicketResponse(BaseModel):
    """Ticket details response."""

    id: uuid.UUID
    customer_id: uuid.UUID
    subject: str
    description: str
    status: TicketStatus
    intent: TicketIntent | None = None
    escalated_at: datetime | None = None
    resolution: str | None = None
    escalated: bool = False


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    database: str
    redis: str
    openai_configured: bool
