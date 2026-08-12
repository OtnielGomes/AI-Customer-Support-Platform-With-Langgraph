"""Knowledge base chunk ORM model for pgvector RAG."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config import get_settings
from app.persistence import Base


class KBChunk(Base):
    """Embedded chunk from knowledge base documents."""

    __tablename__ = "kb_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source_path: Mapped[str] = mapped_column(String(500))
    domain: Mapped[str] = mapped_column(String(50), index=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(get_settings().embedding_dimensions),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
