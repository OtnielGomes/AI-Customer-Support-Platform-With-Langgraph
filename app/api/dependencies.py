"""FastAPI dependency injection."""

from collections.abc import AsyncGenerator
from typing import Annotated, Any

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence import get_db_session
from app.retrieval.embeddings import EmbeddingService
from app.retrieval.retriever import KnowledgeRetriever
from app.security.authentication import Principal, get_current_principal
from app.tools.knowledge_base.tools import set_kb_context


async def get_session(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AsyncSession:
    """Provide async database session."""
    return session


async def get_redis(request: Request) -> Redis:
    """Provide Redis client from app state."""
    redis: Redis = request.app.state.redis
    return redis


async def get_support_graph(request: Request) -> Any:
    """Provide compiled support graph from app state."""
    return request.app.state.support_graph


async def get_embedding_service(
    redis: Annotated[Redis, Depends(get_redis)],
) -> EmbeddingService:
    """Provide embedding service with Redis cache."""
    return EmbeddingService(redis=redis)


async def get_knowledge_retriever(
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
) -> KnowledgeRetriever:
    """Provide knowledge retriever."""
    return KnowledgeRetriever(embedding_service)


async def get_kb_context(
    session: Annotated[AsyncSession, Depends(get_session)],
    retriever: Annotated[KnowledgeRetriever, Depends(get_knowledge_retriever)],
) -> AsyncGenerator[None, None]:
    """Set KB tool context for the current request."""
    set_kb_context(session, retriever)
    yield


SessionDep = Annotated[AsyncSession, Depends(get_session)]
RedisDep = Annotated[Redis, Depends(get_redis)]
GraphDep = Annotated[Any, Depends(get_support_graph)]
PrincipalDep = Annotated[Principal, Depends(get_current_principal)]
KbContextDep = Annotated[None, Depends(get_kb_context)]
