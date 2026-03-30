from __future__ import annotations

def check_redis(redis_url: str) -> bool:
    try:
        import redis

        client = redis.Redis.from_url(redis_url, socket_connect_timeout=1, socket_timeout=1)
        return bool(client.ping())
    except Exception:
        return False
