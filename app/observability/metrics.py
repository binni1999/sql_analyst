
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock
from time import perf_counter
from typing import Iterator


@dataclass
class MetricsRegistry:
    """Small thread-safe in-process metrics registry."""

    _counters: dict[str, int] = field(default_factory=dict)
    _timings: dict[str, dict[str, float | int]] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def increment(self, name: str, value: int = 1) -> None:
        """Increment a counter."""
        if value < 0:
            raise ValueError("counter increment cannot be negative")

        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + value

    def observe(self, name: str, value_ms: float) -> None:
        """Record a timing observation in milliseconds."""
        if value_ms < 0:
            raise ValueError("timing value cannot be negative")

        with self._lock:
            timing = self._timings.get(name)

            if timing is None:
                self._timings[name] = {
                    "count": 1,
                    "total_ms": value_ms,
                    "min_ms": value_ms,
                    "max_ms": value_ms,
                }
                return

            timing["count"] = int(timing["count"]) + 1
            timing["total_ms"] = float(timing["total_ms"]) + value_ms
            timing["min_ms"] = min(float(timing["min_ms"]), value_ms)
            timing["max_ms"] = max(float(timing["max_ms"]), value_ms)

    def reset(self) -> None:
        """Clear all collected metrics."""
        with self._lock:
            self._counters.clear()
            self._timings.clear()

    @contextmanager
    def timer(self, name: str) -> Iterator[None]:
        """Measure execution time for a code block."""
        start = perf_counter()

        try:
            yield
        finally:
            elapsed_ms = (perf_counter() - start) * 1000
            self.observe(name, elapsed_ms)

    def snapshot(self) -> dict[str, object]:
        """Return a point-in-time snapshot of collected metrics."""
        with self._lock:
            counters = dict(self._counters)
            timings = {
                name: dict(values)
                for name, values in self._timings.items()
            }

        timing_summary: dict[str, dict[str, float | int]] = {}

        for name, timing in timings.items():
            count = int(timing["count"])
            total_ms = float(timing["total_ms"])

            timing_summary[name] = {
                "count": count,
                "total_ms": round(total_ms, 3),
                "avg_ms": round(total_ms / count, 3),
                "min_ms": round(float(timing["min_ms"]), 3),
                "max_ms": round(float(timing["max_ms"]), 3),
            }

        return {
            "counters": counters,
            "timings": timing_summary,
        }


metrics_registry = MetricsRegistry()
