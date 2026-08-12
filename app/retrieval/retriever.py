"""pgvector-backed knowledge retriever."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kb_chunk import KBChunk
from app.retrieval.embeddings import EmbeddingService
from app.retrieval.reranker import rerank_chunks
from app.retrieval.types import RetrievedChunk

logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    """Retrieve knowledge base chunks by vector similarity."""

    def __init__(self, embedding_service: EmbeddingService) -> None:
        self._embedding_service = embedding_service

    async def search(
        self,
        session: AsyncSession,
        query: str,
        domain: str | None = None,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """Search KB chunks by cosine similarity."""
        query_vector = await self._embedding_service.embed_text(query)

        distance = KBChunk.embedding.cosine_distance(query_vector)
        stmt = select(KBChunk, distance.label("distance")).order_by(distance).limit(top_k * 2)

        if domain:
            stmt = stmt.where(KBChunk.domain == domain)

        result = await session.execute(stmt)
        rows = result.all()

        chunks = [
            RetrievedChunk(
                content=row.KBChunk.content,
                source_path=row.KBChunk.source_path,
                domain=row.KBChunk.domain,
                score=max(0.0, 1.0 - float(row.distance)),
            )
            for row in rows
        ]

        reranked = rerank_chunks(chunks, domain=domain, top_k=top_k)
        logger.info(
            "Retrieved %d KB chunks for query domain=%s",
            len(reranked),
            domain,
        )
        return reranked
