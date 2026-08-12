"""Typed retrieval result."""

from dataclasses import dataclass


@dataclass
class RetrievedChunk:
    """A knowledge base chunk returned by retrieval."""

    content: str
    source_path: str
    domain: str
    score: float
