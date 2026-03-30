from __future__ import annotations

from functools import lru_cache
from typing import Any, Callable, Literal, TypeVar

from app.core.cache import CacheClient, InMemoryCache, RedisCache, build_transient_cache_key
from app.core.rate_limit import InMemoryRateLimiter, RateLimitConfig, RedisRateLimiter
from app.core.settings import get_settings

RuntimeScope = Literal["read", "compute", "heavy"]
T = TypeVar("T")


def _build_redis_client() -> CacheClient | None:
    settings = get_settings()
    try:
        import redis

        return redis.Redis.from_url(settings.redis_url, decode_responses=False, socket_connect_timeout=1, socket_timeout=1)
    except Exception:
        return None


@lru_cache(maxsize=1)
def get_cache() -> InMemoryCache | RedisCache:
    settings = get_settings()
    if settings.cache_enabled and settings.cache_backend == "redis":
        client = _build_redis_client()
        if client is not None:
            return RedisCache(client, namespace="big-o")
    return InMemoryCache()


@lru_cache(maxsize=3)
def get_rate_limiter(scope: RuntimeScope):
    settings = get_settings()
    limit_by_scope = {
        "read": settings.rate_limit_read_limit,
        "compute": settings.rate_limit_compute_limit,
        "heavy": settings.rate_limit_heavy_limit,
    }
    config = RateLimitConfig(
        limit=limit_by_scope[scope],
        window_seconds=settings.rate_limit_window_seconds,
        namespace=f"big-o:{scope}",
    )
    if settings.rate_limit_backend == "redis":
        client = _build_redis_client()
        if client is not None:
            return RedisRateLimiter(client, config)
    return InMemoryRateLimiter(config)


def cached_call(namespace: str, payload: Any, *, ttl_seconds: int, factory: Callable[[], T]) -> tuple[T, bool]:
    settings = get_settings()
    if not settings.cache_enabled:
        return factory(), False

    cache = get_cache()
    cache_key = build_transient_cache_key(namespace, payload)
    sentinel = object()
    if isinstance(cache, InMemoryCache):
        cached_value = cache.get(cache_key, sentinel)
        if cached_value is not sentinel:
            return cached_value, True
        value = factory()
        cache.set(cache_key, value, ttl_seconds=ttl_seconds)
        return value, False

    cached_value = cache.get(cache_key, sentinel)
    if cached_value is not sentinel:
        return cached_value, True
    value = factory()
    cache.set(cache_key, value, ttl_seconds=ttl_seconds)
    return value, False


def reset_runtime_state() -> None:
    cache = get_cache()
    if isinstance(cache, InMemoryCache):
        cache.clear()
    get_cache.cache_clear()
    get_rate_limiter.cache_clear()
