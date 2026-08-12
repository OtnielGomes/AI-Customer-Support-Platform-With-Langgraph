"""Structured logging configuration."""

import logging
import sys
from typing import Any

from app.config import get_settings


def setup_logging() -> None:
    """Configure root logger with structured JSON-like output."""
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


class StructuredFormatter(logging.Formatter):
    """Simple structured log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as a readable structured line."""
        base: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            base["exception"] = self.formatException(record.exc_info)
        extras = {
            k: v
            for k, v in record.__dict__.items()
            if k not in logging.LogRecord.__dict__ and k not in base
        }
        if extras:
            base["extra"] = extras
        parts = [f"{k}={base[k]}" for k in ("level", "logger", "message")]
        if "exception" in base:
            parts.append(f"exception={base['exception']}")
        if "extra" in base:
            parts.append(f"extra={base['extra']}")
        return " | ".join(parts)


def get_logger(name: str) -> logging.Logger:
    """Return a module logger."""
    return logging.getLogger(name)
