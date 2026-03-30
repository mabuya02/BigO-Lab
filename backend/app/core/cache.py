from __future__ import annotations

from dataclasses import dataclass
from time import time
from typing import Any, Callable, Protocol
import json
import threading

from app.core.performance import build_cache_key, normalize_result


class CacheClient(Protocol):
    def get(self, key: str) -> Any: ...

    def set(self, key: str, value: Any, ex: int | None = None) -> Any: ...

    def delete(self, key: str) -> Any: ...


@dataclass(frozen=True, slots=True)
class CacheEntry:
    value: Any
    expires_at: float | None

    def is_expired(self, now: float | None = None) -> bool:
        if self.expires_at is None:
            return False
        current_time = time() if now is None else now
        return current_time >= self.expires_at


class InMemoryCache:
    def __init__(self, *, clock: Callable[[], float] = time) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._entries: dict[str, CacheEntry] = {}

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return default
            if entry.is_expired(self._clock()):
                self._entries.pop(key, None)
                return default
            return entry.value

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> Any:
        expires_at = None
        if ttl_seconds is not None:
            expires_at = self._clock() + max(ttl_seconds, 0)
        with self._lock:
            self._entries[key] = CacheEntry(value=value, expires_at=expires_at)
        return value

    def delete(self, key: str) -> bool:
        with self._lock:
            return self._entries.pop(key, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def remember(self, key: str, factory: Callable[[], Any], ttl_seconds: int | None = None) -> Any:
        cached = self.get(key, default=None)
        if cached is not None:
            return cached
        value = factory()
        self.set(key, value, ttl_seconds=ttl_seconds)
        return value


class RedisCache:
    def __init__(self, client: CacheClient, *, namespace: str = "big-o-cache") -> None:
        self._client = client
        self._namespace = namespace

    def key(self, payload: Any, *, prefix: str = "payload") -> str:
        return build_cache_key(f"{self._namespace}:{prefix}", payload)

    def get(self, key: str, default: Any = None) -> Any:
        raw_value = self._client.get(key)
        if raw_value is None:
            return default
        if isinstance(raw_value, bytes):
            raw_value = raw_value.decode("utf-8")
        try:
            return json.loads(raw_value)
        except (TypeError, json.JSONDecodeError):
            return raw_value

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> Any:
        payload = json.dumps(normalize_result(value), sort_keys=True, separators=(",", ":"))
        if ttl_seconds is None:
            self._client.set(key, payload)
        else:
            self._client.set(key, payload, ex=ttl_seconds)
        return value

    def delete(self, key: str) -> Any:
        return self._client.delete(key)

    def remember(self, key: str, factory: Callable[[], Any], ttl_seconds: int | None = None) -> Any:
        cached = self.get(key, default=None)
        if cached is not None:
            return cached
        value = factory()
        self.set(key, value, ttl_seconds=ttl_seconds)
        return value


def build_transient_cache_key(namespace: str, payload: Any) -> str:
    return build_cache_key(namespace, payload, prefix="transient")


__all__ = [
    "CacheEntry",
    "CacheClient",
    "InMemoryCache",
    "RedisCache",
    "build_transient_cache_key",
]
