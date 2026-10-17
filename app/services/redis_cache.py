from __future__ import annotations

import json
import logging
from typing import Any

# pyrefly: ignore [missing-import]
import redis
try:
    from config import get_settings
except ImportError:
    from app.config import get_settings

from observability.metrics import metrics_registry
logger = logging.getLogger(__name__)


class RedisCacheService:
    """Small Redis cache wrapper with graceful degradation.

    Cache failures are logged and treated as misses so Redis is an optimization,
    not a hard dependency for analytical correctness.
    """

    def __init__(
        self,
        redis_url: str | None = None,
        ttl_seconds: int | None = None,
    ):
        settings = get_settings()

        self.redis_url = redis_url or settings.redis_url
        self.ttl_seconds = (
            ttl_seconds
            if ttl_seconds is not None
            else settings.redis_cache_ttl_seconds
        )

        self.client = redis.Redis.from_url(
            self.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            max_connections=settings.redis_max_connections,
        )
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_errors = 0

    def get_json(self, key: str) -> Any | None:
        try:
            with metrics_registry.timer("redis.get_ms"):
                value = self.client.get(key)

            if value is None:
                self.cache_misses += 1
                metrics_registry.increment("redis.cache_misses")
                return None

            self.cache_hits += 1
            metrics_registry.increment("redis.cache_hits")

            return json.loads(value)

        except (redis.RedisError, json.JSONDecodeError, TypeError) as exc:
            self.cache_errors += 1
            metrics_registry.increment("redis.cache_errors")

            logger.warning(
                "Redis cache read failed for key %s: %s",
                key,
                exc,
            )

            return None

    def set_json(
        self,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
    ) -> bool:
        ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds

        try:
            payload = json.dumps(value)

            with metrics_registry.timer("redis.set_ms"):
                self.client.set(key, payload, ex=ttl)

            metrics_registry.increment("redis.cache_sets")

            return True

        except (redis.RedisError, TypeError, ValueError) as exc:
            metrics_registry.increment("redis.cache_errors")

            logger.warning(
                "Redis cache write failed for key %s: %s",
                key,
                exc,
            )

            return False

    def delete(self, key: str) -> bool:
        try:
            with metrics_registry.timer("redis.delete_ms"):
                self.client.delete(key)

            metrics_registry.increment("redis.cache_deletes")

            return True

        except redis.RedisError as exc:
            metrics_registry.increment("redis.cache_errors")

            logger.warning(
                "Redis cache delete failed for key %s: %s",
                key,
                exc,
            )

            return False

    def ping(self) -> bool:
        try:
            with metrics_registry.timer("redis.ping_ms"):
                return bool(self.client.ping())

        except redis.RedisError as exc:
            metrics_registry.increment("redis.cache_errors")

            logger.warning(
                "Redis ping failed: %s",
                exc,
            )

            return False

    def stats(self) -> dict[str, int | float]:
        total_requests = self.cache_hits + self.cache_misses

        hit_ratio = (
            self.cache_hits / total_requests
            if total_requests > 0
            else 0.0
        )

        return {
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "errors": self.cache_errors,
            "hit_ratio": round(hit_ratio, 4),
        }
