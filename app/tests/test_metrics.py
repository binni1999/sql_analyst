
from concurrent.futures import ThreadPoolExecutor

import pytest

from observability.metrics import MetricsRegistry


def test_increment_counter():
    registry = MetricsRegistry()

    registry.increment("sql.executions")
    registry.increment("sql.executions", 2)

    snapshot = registry.snapshot()

    assert snapshot["counters"]["sql.executions"] == 3


def test_observe_timing():
    registry = MetricsRegistry()

    registry.observe("sql.execution_ms", 10.0)
    registry.observe("sql.execution_ms", 20.0)

    snapshot = registry.snapshot()
    timing = snapshot["timings"]["sql.execution_ms"]

    assert timing["count"] == 2
    assert timing["total_ms"] == 30.0
    assert timing["avg_ms"] == 15.0
    assert timing["min_ms"] == 10.0
    assert timing["max_ms"] == 20.0


def test_timer_records_duration():
    registry = MetricsRegistry()

    with registry.timer("agent.execution_ms"):
        pass

    snapshot = registry.snapshot()

    assert snapshot["timings"]["agent.execution_ms"]["count"] == 1
    assert snapshot["timings"]["agent.execution_ms"]["min_ms"] >= 0


def test_negative_counter_rejected():
    registry = MetricsRegistry()

    with pytest.raises(ValueError):
        registry.increment("invalid", -1)


def test_negative_timing_rejected():
    registry = MetricsRegistry()

    with pytest.raises(ValueError):
        registry.observe("sql.execution_ms", -1.0)


def test_empty_snapshot():
    registry = MetricsRegistry()

    assert registry.snapshot() == {
        "counters": {},
        "timings": {},
    }


def test_reset_clears_metrics():
    registry = MetricsRegistry()
    registry.increment("sql.executions")
    registry.observe("sql.execution_ms", 10.0)

    registry.reset()

    assert registry.snapshot() == {
        "counters": {},
        "timings": {},
    }


def test_registry_instances_are_isolated():
    registry_a = MetricsRegistry()
    registry_b = MetricsRegistry()

    registry_a.increment("requests")
    registry_a.observe("request_ms", 10.0)

    assert registry_a.snapshot()["counters"]["requests"] == 1
    assert registry_b.snapshot() == {
        "counters": {},
        "timings": {},
    }


def test_concurrent_metrics_updates_are_thread_safe():
    registry = MetricsRegistry()
    workers = 10
    iterations = 1_000

    def record_metrics(_):
        for _ in range(iterations):
            registry.increment("requests")
            registry.observe("request_ms", 5.0)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        list(executor.map(record_metrics, range(workers)))

    snapshot = registry.snapshot()

    assert snapshot["counters"]["requests"] == workers * iterations

    timing = snapshot["timings"]["request_ms"]
    assert timing["count"] == workers * iterations
    assert timing["total_ms"] == workers * iterations * 5.0
    assert timing["avg_ms"] == 5.0
    assert timing["min_ms"] == 5.0
    assert timing["max_ms"] == 5.0
