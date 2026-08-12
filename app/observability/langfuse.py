"""Langfuse callback handler factory."""

import logging
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


def build_langfuse_handler(
    ticket_id: str | None = None,
    intent: str | None = None,
) -> Any | None:
    """Build Langfuse callback handler when credentials are configured."""
    settings = get_settings()
    if not settings.langfuse_enabled():
        return None

    try:
        from langfuse.callback import CallbackHandler

        tags = []
        if intent:
            tags.append(f"intent:{intent}")
        metadata: dict[str, str] = {}
        if ticket_id:
            metadata["ticket_id"] = ticket_id

        return CallbackHandler(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
            tags=tags,
            metadata=metadata,
        )
    except Exception as exc:
        logger.warning("Failed to initialize Langfuse handler: %s", exc)
        return None
