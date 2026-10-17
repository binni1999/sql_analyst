from fastapi.testclient import TestClient

from main import app
from observability.metrics import metrics_registry


def setup_function():
    metrics_registry.reset()


def teardown_function():
    metrics_registry.reset()


def test_metrics_endpoint_returns_empty_metrics():
    client = TestClient(app)

    response = client.get("/metrics")

    assert response.status_code == 200

    data = response.json()

    assert data == {
        "counters": {},
        "timings": {},
    }


def test_metrics_endpoint_returns_recorded_metrics():
    metrics_registry.increment("sql.executions", 5)
    metrics_registry.increment("sql.successes", 4)
    metrics_registry.increment("sql.failures", 1)
    metrics_registry.increment("redis.cache_hits", 10)

    metrics_registry.observe(
        "sql.execution_ms",
        12.5,
    )

    client = TestClient(app)

    response = client.get("/metrics")

    assert response.status_code == 200

    data = response.json()

    assert data["counters"]["sql.executions"] == 5
    assert data["counters"]["sql.successes"] == 4
    assert data["counters"]["sql.failures"] == 1
    assert data["counters"]["redis.cache_hits"] == 10

    assert data["timings"]["sql.execution_ms"]["count"] == 1
    assert data["timings"]["sql.execution_ms"]["avg_ms"] == 12.5