"""Unit tests for reranker."""

from app.retrieval.reranker import rerank_chunks
from app.retrieval.types import RetrievedChunk


def test_rerank_boosts_domain_match() -> None:
    """Domain-matching chunks should rank higher."""
    chunks = [
        RetrievedChunk(content="a", source_path="x", domain="billing", score=0.5),
        RetrievedChunk(content="b", source_path="y", domain="logistics", score=0.55),
    ]
    result = rerank_chunks(chunks, domain="billing", top_k=1)
    assert result[0].domain == "billing"
