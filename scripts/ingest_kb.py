"""Knowledge base ingestion script."""

import asyncio
import hashlib
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.kb_chunk import KBChunk
from app.persistence import get_session_factory
from app.retrieval.embeddings import EmbeddingService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHUNK_SIZE = 500


def chunk_text(text: str, size: int = CHUNK_SIZE) -> list[str]:
    """Split text into fixed-size chunks."""
    words = text.split()
    chunks: list[str] = []
    current: list[str] = []
    for word in words:
        current.append(word)
        if len(" ".join(current)) >= size:
            chunks.append(" ".join(current))
            current = []
    if current:
        chunks.append(" ".join(current))
    return chunks


def content_hash(content: str) -> str:
    """Hash content for idempotent upsert."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def infer_domain(path: Path) -> str:
    """Infer domain from directory structure."""
    parts = path.parts
    for domain in ("billing", "logistics", "account"):
        if domain in parts:
            return domain
    return "general"


async def ingest_file(session: AsyncSession, path: Path, embedding_service: EmbeddingService) -> int:
    """Ingest a single markdown file."""
    text = path.read_text(encoding="utf-8")
    domain = infer_domain(path)
    chunks = chunk_text(text)
    count = 0

    for chunk_content in chunks:
        digest = content_hash(chunk_content)
        existing = await session.execute(
            select(KBChunk).where(KBChunk.content_hash == digest)
        )
        if existing.scalar_one_or_none():
            continue

        vector = await embedding_service.embed_text(chunk_content)
        session.add(
            KBChunk(
                content_hash=digest,
                source_path=str(path),
                domain=domain,
                content=chunk_content,
                embedding=vector,
            )
        )
        count += 1

    return count


async def main() -> None:
    """Ingest all knowledge base markdown files."""
    settings = get_settings()
    kb_root = Path("data/knowledge_base")
    if not kb_root.exists():
        logger.error("Knowledge base directory not found: %s", kb_root)
        return

    embedding_service = EmbeddingService()
    factory = get_session_factory()
    total = 0

    async with factory() as session:
        for path in kb_root.rglob("*.md"):
            ingested = await ingest_file(session, path, embedding_service)
            logger.info("Ingested %d chunks from %s", ingested, path)
            total += ingested
        await session.commit()

    logger.info("Ingestion complete: %d new chunks", total)


if __name__ == "__main__":
    asyncio.run(main())
