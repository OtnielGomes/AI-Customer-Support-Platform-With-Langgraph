"""Seeded random helpers for deterministic synthetic data."""

from __future__ import annotations

import random
import uuid
from typing import Sequence, TypeVar

T = TypeVar("T")


class SeededRNG:
    """``random.Random`` wrapper that also yields deterministic UUIDs."""

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)

    def uuid4(self) -> uuid.UUID:
        """Return a UUID4 derived from the seeded bit stream."""
        return uuid.UUID(int=self._rng.getrandbits(128), version=4)

    def choice(self, seq: Sequence[T]) -> T:
        """Pick one element."""
        return self._rng.choice(seq)

    def choices(self, seq: Sequence[T], weights: Sequence[float], k: int = 1) -> list[T]:
        """Pick ``k`` elements with replacement."""
        return self._rng.choices(seq, weights=weights, k=k)

    def randint(self, a: int, b: int) -> int:
        """Inclusive integer range."""
        return self._rng.randint(a, b)

    def random(self) -> float:
        """Uniform float in [0, 1)."""
        return self._rng.random()

    def sample(self, seq: Sequence[T], k: int) -> list[T]:
        """Sample without replacement."""
        return self._rng.sample(list(seq), k)
