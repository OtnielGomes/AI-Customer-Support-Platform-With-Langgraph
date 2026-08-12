"""Redis-backed tool result cache."""

import json
import logging
from typing import Any

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

DEFAULT_TTL = 300


class ToolResultCache:
    """Cache tool results in Redis with TTL."""

    def __init__(self, redis: Redis, ttl: int = DEFAULT_TTL) -> None:
        self._redis = redis
        self._ttl = ttl

    def _key(self, tool_name: str, args_hash: str) -> str:
        """Build cache key."""
        return f"tool:{tool_name}:{args_hash}"

    async def get(self, tool_name: str, args_hash: str) -> Any | None:
        """Get cached tool result."""
        try:
            raw = await self._redis.get(self._key(tool_name, args_hash))
            if raw:
                return json.loads(raw)
        except Exception as exc:
            logger.warning("Tool cache get failed: %s", exc)
        return None

    async def set(self, tool_name: str, args_hash: str, result: Any) -> None:
        """Store tool result in cache."""
        try:
            await self._redis.set(
                self._key(tool_name, args_hash),
                json.dumps(result, default=str),
                ex=self._ttl,
            )
        except Exception as exc:
            logger.warning("Tool cache set failed: %s", exc)
