from __future__ import annotations

from dataclasses import dataclass
from time import time
from typing import Any, Callable, Protocol
import threading


class RateLimitClient(Protocol):
    def incr(self, key: str) -> int: ...

    def expire(self, key: str, seconds: int) -> Any: ...


@dataclass(frozen=True, slots=True)
class RateLimitConfig:
    limit: int
    window_seconds: int
    namespace: str = "rate-limit"


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    reset_at: float
    retry_after_seconds: int
    key: str
    current_count: int


def build_rate_limit_key(namespace: str, identifier: str) -> str:
    return f"{namespace}:{identifier}"


class InMemoryRateLimiter:
    def __init__(self, config: RateLimitConfig, *, clock: Callable[[], float] = time) -> None:
        if config.limit <= 0:
            raise ValueError("limit must be positive")
        if config.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self.config = config
        self._clock = clock
        self._lock = threading.Lock()
        self._windows: dict[str, tuple[float, int]] = {}

    def allow(self, identifier: str, *, cost: int = 1) -> RateLimitDecision:
        if cost <= 0:
            raise ValueError("cost must be positive")
        now = self._clock()
        window_start = now - (now % self.config.window_seconds)
        reset_at = window_start + self.config.window_seconds
        key = build_rate_limit_key(self.config.namespace, identifier)

        with self._lock:
            stored_window, stored_count = self._windows.get(key, (window_start, 0))
            if stored_window != window_start:
                stored_window, stored_count = window_start, 0
            current_count = stored_count + cost
            self._windows[key] = (stored_window, current_count)

        allowed = current_count <= self.config.limit
        remaining = max(self.config.limit - current_count, 0)
        retry_after_seconds = 0 if allowed else max(int(reset_at - now), 1)
        return RateLimitDecision(
            allowed=allowed,
            limit=self.config.limit,
            remaining=remaining,
            reset_at=reset_at,
            retry_after_seconds=retry_after_seconds,
            key=key,
            current_count=current_count,
        )

    def reset(self, identifier: str) -> bool:
        key = build_rate_limit_key(self.config.namespace, identifier)
        with self._lock:
            return self._windows.pop(key, None) is not None


class RedisRateLimiter:
    def __init__(self, client: RateLimitClient, config: RateLimitConfig, *, clock: Callable[[], float] = time) -> None:
        if config.limit <= 0:
            raise ValueError("limit must be positive")
        if config.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self._client = client
        self.config = config
        self._clock = clock

    def allow(self, identifier: str, *, cost: int = 1) -> RateLimitDecision:
        if cost <= 0:
            raise ValueError("cost must be positive")
        now = self._clock()
        window_start = now - (now % self.config.window_seconds)
        reset_at = window_start + self.config.window_seconds
        bucket = int(window_start)
        key = build_rate_limit_key(self.config.namespace, f"{identifier}:{bucket}")
        current_count = 0
        for _ in range(cost):
            current_count = int(self._client.incr(key))
        if current_count == cost:
            self._client.expire(key, self.config.window_seconds)
        allowed = current_count <= self.config.limit
        remaining = max(self.config.limit - current_count, 0)
        retry_after_seconds = 0 if allowed else max(int(reset_at - now), 1)
        return RateLimitDecision(
            allowed=allowed,
            limit=self.config.limit,
            remaining=remaining,
            reset_at=reset_at,
            retry_after_seconds=retry_after_seconds,
            key=key,
            current_count=current_count,
        )


__all__ = [
    "InMemoryRateLimiter",
    "RateLimitConfig",
    "RateLimitDecision",
    "RedisRateLimiter",
    "build_rate_limit_key",
]
