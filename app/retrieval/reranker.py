"""Heuristic reranker for retrieved chunks."""

from app.retrieval.types import RetrievedChunk


def rerank_chunks(
    chunks: list[RetrievedChunk],
    domain: str | None = None,
    top_k: int = 5,
) -> list[RetrievedChunk]:
    """Rerank chunks with simple domain boost heuristic."""
    if not chunks:
        return []

    def score(chunk: RetrievedChunk) -> float:
        boost = 0.1 if domain and chunk.domain == domain else 0.0
        return chunk.score + boost

    sorted_chunks = sorted(chunks, key=score, reverse=True)
    return sorted_chunks[:top_k]
