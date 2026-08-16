"""Runtime context shared by operational tools."""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.retrieval.retriever import KnowledgeRetriever
from app.security.authentication import Principal


@dataclass
class ToolContext:
    """Per-request tool runtime: DB session, retriever, caller, ticket customer."""

    session: AsyncSession
    retriever: KnowledgeRetriever | None = None
    principal: Principal | None = None
    customer_id: uuid.UUID | None = None
    identity_verified: bool = False


_context: ContextVar[ToolContext | None] = ContextVar("tool_context", default=None)


def set_tool_context(context: ToolContext) -> None:
    """Bind tool context for the current task."""
    _context.set(context)


def get_tool_context() -> ToolContext | None:
    """Return the current tool context if configured."""
    return _context.get()


def require_context() -> ToolContext | dict:
    """Return context or an error payload for tool callers."""
    context = get_tool_context()
    if context is None:
        return {"error": "Tool context not configured"}
    return context
