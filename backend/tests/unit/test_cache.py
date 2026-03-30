from __future__ import annotations

import unittest

from app.core.cache import InMemoryCache, RedisCache, build_transient_cache_key


class FakeRedisClient:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.expirations: dict[str, int] = {}

    def get(self, key: str):
        return self.values.get(key)

    def set(self, key: str, value, ex: int | None = None):
        self.values[key] = value
        if ex is not None:
            self.expirations[key] = ex
        return True

    def delete(self, key: str):
        return self.values.pop(key, None) is not None


class CacheTests(unittest.TestCase):
    def test_build_transient_cache_key_is_stable(self) -> None:
        left = build_transient_cache_key("runs", {"b": 2, "a": 1})
        right = build_transient_cache_key("runs", {"a": 1, "b": 2})
        self.assertEqual(left, right)

    def test_in_memory_cache_expiry_and_remember(self) -> None:
        now = [100.0]

        def clock() -> float:
            return now[0]

        cache = InMemoryCache(clock=clock)
        cache.set("alpha", {"value": 1}, ttl_seconds=5)
        self.assertEqual(cache.get("alpha"), {"value": 1})

        now[0] += 6
        self.assertIsNone(cache.get("alpha"))

        calls = {"count": 0}

        def factory():
            calls["count"] += 1
            return "computed"

        self.assertEqual(cache.remember("beta", factory, ttl_seconds=10), "computed")
        self.assertEqual(cache.remember("beta", factory, ttl_seconds=10), "computed")
        self.assertEqual(calls["count"], 1)

    def test_redis_cache_serializes_payloads(self) -> None:
        client = FakeRedisClient()
        cache = RedisCache(client, namespace="playground")
        key = cache.key({"x": 1}, prefix="result")

        cache.set(key, {"answer": 42}, ttl_seconds=15)

        self.assertEqual(client.expirations[key], 15)
        self.assertEqual(cache.get(key), {"answer": 42})

