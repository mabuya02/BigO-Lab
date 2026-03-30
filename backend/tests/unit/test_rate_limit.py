from __future__ import annotations

import unittest

from app.core.rate_limit import InMemoryRateLimiter, RateLimitConfig, RedisRateLimiter, build_rate_limit_key


class FakeClock:
    def __init__(self, start: float = 100.0) -> None:
        self.value = start

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class FakeRedisClient:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    def expire(self, key: str, seconds: int) -> bool:
        self.expirations[key] = seconds
        return True


class RateLimitTests(unittest.TestCase):
    def test_build_rate_limit_key(self) -> None:
        self.assertEqual(build_rate_limit_key("scope", "user-1"), "scope:user-1")

    def test_in_memory_rate_limiter_tracks_fixed_window(self) -> None:
        clock = FakeClock()
        limiter = InMemoryRateLimiter(RateLimitConfig(limit=2, window_seconds=10), clock=clock)

        first = limiter.allow("client-a")
        second = limiter.allow("client-a")
        third = limiter.allow("client-a")

        self.assertTrue(first.allowed)
        self.assertTrue(second.allowed)
        self.assertFalse(third.allowed)
        self.assertEqual(third.remaining, 0)
        self.assertEqual(third.retry_after_seconds, 10)

        clock.advance(10)
        reset = limiter.allow("client-a")
        self.assertTrue(reset.allowed)
        self.assertEqual(reset.current_count, 1)

    def test_redis_rate_limiter_uses_increment_and_expire(self) -> None:
        clock = FakeClock()
        client = FakeRedisClient()
        limiter = RedisRateLimiter(client, RateLimitConfig(limit=1, window_seconds=30), clock=clock)

        decision = limiter.allow("session-1")

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.current_count, 1)
        self.assertEqual(client.expirations[decision.key], 30)

        next_decision = limiter.allow("session-1")
        self.assertFalse(next_decision.allowed)
        self.assertEqual(next_decision.remaining, 0)

