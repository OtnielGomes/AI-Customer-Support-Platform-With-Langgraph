"""Embedding service with optional Redis cache."""

import hashlib
import json
import logging

from langchain_openai import OpenAIEmbeddings
from redis.asyncio import Redis

from app.config import build_embeddings, get_settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Wrap OpenAI embeddings with optional Redis caching."""

    def __init__(
        self,
        embeddings: OpenAIEmbeddings | None = None,
        redis: Redis | None = None,
    ) -> None:
        self._embeddings = embeddings or build_embeddings()
        self._redis = redis
        self._settings = get_settings()

    def _cache_key(self, text: str) -> str:
        """Build Redis cache key for text embedding."""
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"emb:{self._settings.embedding_model}:{digest}"

    async def embed_text(self, text: str) -> list[float]:
        """Embed a single text, using cache when available."""
        if self._redis is not None:
            cached = await self._redis.get(self._cache_key(text))
            if cached:
                return json.loads(cached)

        vector = await self._embeddings.aembed_query(text)

        if self._redis is not None:
            await self._redis.set(
                self._cache_key(text),
                json.dumps(vector),
                ex=86400,
            )
        return vector

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in batch."""
        return await self._embeddings.aembed_documents(texts)
