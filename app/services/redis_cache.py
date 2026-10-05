from __future__ import annotations

import json
import logging
from typing import Any

# pyrefly: ignore [missing-import]
import redis

from config import get_settings


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
        )

    def get_json(self, key: str) -> Any | None:
        try:
            value = self.client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except (redis.RedisError, json.JSONDecodeError, TypeError) as exc:
            logger.warning("Redis cache read failed for key %s: %s", key, exc)
            return None

    def set_json(self, key: str, value: Any, ttl_seconds: int | None = None) -> bool:
        ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds
        try:
            payload = json.dumps(value)
            self.client.setex(key, ttl, payload)
            return True
        except (redis.RedisError, TypeError, ValueError) as exc:
            logger.warning("Redis cache write failed for key %s: %s", key, exc)
            return False

    def delete(self, key: str) -> bool:
        try:
            self.client.delete(key)
            return True
        except redis.RedisError as exc:
            logger.warning("Redis cache delete failed for key %s: %s", key, exc)
            return False

    def ping(self) -> bool:
        try:
            return bool(self.client.ping())
        except redis.RedisError as exc:
            logger.warning("Redis ping failed: %s", exc)
            return False
