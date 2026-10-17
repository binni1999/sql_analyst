import pytest

from observability.metrics import metrics_registry
from services.redis_cache import RedisCacheService


@pytest.fixture(autouse=True)
def reset_metrics():
    metrics_registry.reset()
    yield
    metrics_registry.reset()


class FakeRedisClient:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ex=None):
        self.data[key] = value
        return True

    def delete(self, key):
        self.data.pop(key, None)

    def ping(self):
        return True


def create_cache():
    cache = RedisCacheService(
        redis_url="redis://localhost:6379/0",
        ttl_seconds=300,
    )

    cache.client = FakeRedisClient()

    return cache


def test_cache_miss_records_metric():
    cache = create_cache()

    result = cache.get_json("missing")

    assert result is None

    snapshot = metrics_registry.snapshot()

    assert snapshot["counters"]["redis.cache_misses"] == 1
    assert snapshot["counters"].get("redis.cache_hits", 0) == 0

    assert snapshot["timings"]["redis.get_ms"]["count"] == 1


def test_cache_hit_records_metric():
    cache = create_cache()

    cache.set_json(
        "test",
        {"value": 123},
    )

    result = cache.get_json("test")

    assert result == {"value": 123}

    snapshot = metrics_registry.snapshot()

    assert snapshot["counters"]["redis.cache_hits"] == 1
    assert snapshot["counters"].get("redis.cache_misses", 0) == 0

    assert snapshot["timings"]["redis.get_ms"]["count"] == 1


def test_cache_set_records_metric():
    cache = create_cache()

    assert cache.set_json(
        "test",
        {"value": 123},
    )

    snapshot = metrics_registry.snapshot()

    assert snapshot["counters"]["redis.cache_sets"] == 1
    assert snapshot["timings"]["redis.set_ms"]["count"] == 1


def test_cache_delete_records_metric():
    cache = create_cache()

    cache.set_json(
        "test",
        {"value": 123},
    )

    assert cache.delete("test")

    snapshot = metrics_registry.snapshot()

    assert snapshot["counters"]["redis.cache_deletes"] == 1
    assert snapshot["timings"]["redis.delete_ms"]["count"] == 1


def test_cache_ping_records_timing():
    cache = create_cache()

    assert cache.ping()

    snapshot = metrics_registry.snapshot()

    assert snapshot["timings"]["redis.ping_ms"]["count"] == 1


def test_cache_stats_remain_correct():
    cache = create_cache()

    cache.set_json("test", {"value": 123})

    cache.get_json("test")
    cache.get_json("missing")

    stats = cache.stats()

    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["errors"] == 0
    assert stats["hit_ratio"] == 0.5