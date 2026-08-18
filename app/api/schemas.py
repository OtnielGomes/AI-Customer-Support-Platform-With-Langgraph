"""API request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from app.models.agent_run import AgentEventType, AgentRunStatus
from app.models.ticket import TicketIntent, TicketStatus


class CreateTicketRequest(BaseModel):
    """Request to create a support ticket for an existing customer."""

    customer_email: str = Field(min_length=3, max_length=255)
    customer_name: str = Field(min_length=1, max_length=255)
    subject: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1, max_length=10000)
    order_id: uuid.UUID | None = None


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


class EscalationReplyRequest(BaseModel):
    """Human agent reply that resumes an interrupted graph."""

    answer: str = Field(min_length=1, max_length=10000)
    agent: str = Field(default="human", max_length=255)


class CloseTicketRequest(BaseModel):
    """Request to close a ticket without resuming the graph."""

    reason: str | None = Field(default=None, max_length=2000)


class PortalSessionRequest(BaseModel):
    """Validate a customer login email."""

    email: str = Field(min_length=3, max_length=255)


class CreateConversationRequest(BaseModel):
    """Open a portal chat thread, optionally pinned to an order."""

    order_id: uuid.UUID | None = None


class ChatMessageRequest(BaseModel):
    """A new chat turn from the customer or a human agent."""

    content: str = Field(min_length=1, max_length=10000)
    role: str = Field(default="customer", pattern="^(customer|human_agent|user|human)$")


class TakeoverRequest(BaseModel):
    """Assign a human agent to a live conversation."""

    agent: str = Field(default="console", max_length=255)


class OrderSummary(BaseModel):
    """Compact order row for the portal and graph context."""

    id: uuid.UUID
    public_id: str
    status: str
    total_amount: str
    currency: str
    created_at: datetime | None = None


class ChatMessageResponse(BaseModel):
    """One persisted conversation message."""

    id: uuid.UUID
    ticket_id: uuid.UUID
    role: str
    content: str
    agent_run_id: uuid.UUID | None = None
    created_at: datetime | None = None


class ChatMessageListResponse(BaseModel):
    """Conversation history."""

    items: list[ChatMessageResponse]


class CustomerProfileResponse(BaseModel):
    """Authenticated portal customer."""

    id: uuid.UUID
    public_id: str
    email: str
    name: str
    customer_tier: str
    account_status: str
    orders: list[OrderSummary] = Field(default_factory=list)
    conversations: list["TicketSummary"] = Field(default_factory=list)


class ResolutionResponse(BaseModel):
    """Graph resolution result."""

    ticket_id: uuid.UUID
    answer: str
    intent: str | None = None
    confidence: float | None = None
    escalated: bool = False
    awaiting_human: bool = False
    run_id: uuid.UUID | None = None
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    retrieved_context: list[dict[str, Any]] = Field(default_factory=list)
    interrupt_payload: dict[str, Any] | None = None


class TicketResponse(BaseModel):
    """Ticket details response."""

    id: uuid.UUID
    customer_id: uuid.UUID
    customer_email: str | None = None
    customer_name: str | None = None
    subject: str
    description: str
    status: TicketStatus
    intent: TicketIntent | None = None
    escalated_at: datetime | None = None
    resolution: str | None = None
    escalated: bool = False
    order_id: uuid.UUID | None = None
    last_message_at: datetime | None = None
    assigned_agent: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TicketSummary(BaseModel):
    """Ticket row for list views."""

    id: uuid.UUID
    customer_id: uuid.UUID
    customer_email: str | None = None
    customer_name: str | None = None
    subject: str
    status: TicketStatus
    intent: TicketIntent | None = None
    escalated: bool = False
    escalated_at: datetime | None = None
    last_message_at: datetime | None = None
    assigned_agent: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TicketListResponse(BaseModel):
    """Paginated ticket list."""

    items: list[TicketSummary]
    total: int
    limit: int
    offset: int


class AgentRunResponse(BaseModel):
    """Persisted graph invocation."""

    id: uuid.UUID
    ticket_id: uuid.UUID
    thread_id: str
    status: AgentRunStatus
    intent: str | None = None
    confidence: float | None = None
    escalated: bool = False
    total_latency_ms: float | None = None
    error: str | None = None
    created_at: datetime


class AgentRunListResponse(BaseModel):
    """List of agent runs for a ticket."""

    items: list[AgentRunResponse]


class AgentEventResponse(BaseModel):
    """Persisted execution event."""

    id: uuid.UUID
    run_id: uuid.UUID
    sequence: int
    event_type: AgentEventType
    name: str
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    latency_ms: float | None = None
    error: str | None = None
    created_at: datetime


class AgentEventListResponse(BaseModel):
    """Events belonging to one agent run."""

    items: list[AgentEventResponse]


class VolumePoint(BaseModel):
    """Daily ticket volume."""

    date: str
    count: int


class AnalyticsOverviewResponse(BaseModel):
    """Aggregate ticket metrics for the console."""

    total_tickets: int
    by_status: dict[str, int]
    by_intent: dict[str, int]
    escalation_rate: float
    avg_confidence: float | None = None
    avg_resolution_ms: float | None = None
    volume_by_day: list[VolumePoint] = Field(default_factory=list)


class ToolAnalyticsItem(BaseModel):
    """Per-tool usage and latency."""

    name: str
    calls: int
    errors: int
    error_rate: float
    avg_latency_ms: float | None = None
    p95_latency_ms: float | None = None


class AnalyticsToolsResponse(BaseModel):
    """Tool analytics payload."""

    items: list[ToolAnalyticsItem]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    database: str
    redis: str
    openai_configured: bool
