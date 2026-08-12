"""Application metrics helpers."""

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricsCollector:
    """In-memory metrics collector for node latencies and counters."""

    node_latencies_ms: dict[str, list[float]] = field(default_factory=dict)
    counters: dict[str, int] = field(default_factory=dict)

    def record_latency(self, node: str, duration_ms: float) -> None:
        """Record node execution latency."""
        self.node_latencies_ms.setdefault(node, []).append(duration_ms)

    def increment(self, name: str, value: int = 1) -> None:
        """Increment a counter."""
        self.counters[name] = self.counters.get(name, 0) + value

    def snapshot(self) -> dict[str, Any]:
        """Return metrics snapshot."""
        avg_latencies = {
            node: sum(values) / len(values) if values else 0.0
            for node, values in self.node_latencies_ms.items()
        }
        return {"avg_latency_ms": avg_latencies, "counters": dict(self.counters)}


_metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    """Return global metrics collector."""
    return _metrics


@contextmanager
def record_node_latency(node: str):
    """Record latency for a graph node."""
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        _metrics.record_latency(node, duration_ms)
