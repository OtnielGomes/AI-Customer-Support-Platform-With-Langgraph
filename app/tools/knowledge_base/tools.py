"""Knowledge base search tool."""

from contextvars import ContextVar
from typing import Any

from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession

from app.retrieval.retriever import KnowledgeRetriever

_session_ctx: ContextVar[AsyncSession | None] = ContextVar("kb_session", default=None)
_retriever_ctx: ContextVar[KnowledgeRetriever | None] = ContextVar("kb_retriever", default=None)


def set_kb_context(session: AsyncSession, retriever: KnowledgeRetriever) -> None:
    """Set async context for KB tool execution."""
    _session_ctx.set(session)
    _retriever_ctx.set(retriever)


@tool
async def search_knowledge_base(query: str, domain: str = "billing") -> list[dict[str, Any]]:
    """Search the knowledge base for relevant policy and FAQ content."""
    session = _session_ctx.get()
    retriever = _retriever_ctx.get()
    if session is None or retriever is None:
        return [{"error": "Knowledge base context not configured"}]

    chunks = await retriever.search(session, query=query, domain=domain, top_k=3)
    return [
        {
            "content": chunk.content,
            "source_path": chunk.source_path,
            "domain": chunk.domain,
            "score": chunk.score,
        }
        for chunk in chunks
    ]


KB_TOOLS = [search_knowledge_base]
