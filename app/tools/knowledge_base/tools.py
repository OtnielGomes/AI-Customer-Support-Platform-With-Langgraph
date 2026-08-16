"""Knowledge base search tool."""

from typing import Any

from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession

from app.retrieval.retriever import KnowledgeRetriever
from app.tools.context import ToolContext, get_tool_context, set_tool_context


def set_kb_context(session: AsyncSession, retriever: KnowledgeRetriever) -> None:
    """Set KB/session context, preserving an existing customer binding."""
    current = get_tool_context()
    if current is None:
        set_tool_context(ToolContext(session=session, retriever=retriever))
        return
    current.session = session
    current.retriever = retriever
    set_tool_context(current)


@tool
async def search_knowledge_base(query: str, domain: str = "billing") -> list[dict[str, Any]]:
    """Search the knowledge base for relevant policy and FAQ content."""
    context = get_tool_context()
    if context is None or context.retriever is None:
        return [{"error": "Knowledge base context not configured"}]

    chunks = await context.retriever.search(context.session, query=query, domain=domain, top_k=3)
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
