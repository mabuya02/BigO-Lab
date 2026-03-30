from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, is_dataclass
from hashlib import sha256
from time import perf_counter
from typing import Any, Callable, Iterator, Mapping
import json


@dataclass(frozen=True, slots=True)
class TimedResult:
    value: Any
    elapsed_ms: float
    started_at: float
    finished_at: float


@contextmanager
def timer() -> Iterator[dict[str, float]]:
    started_at = perf_counter()
    state = {"started_at": started_at, "finished_at": started_at, "elapsed_ms": 0.0}
    try:
        yield state
    finally:
        finished_at = perf_counter()
        state["finished_at"] = finished_at
        state["elapsed_ms"] = (finished_at - started_at) * 1000.0


def measure(callable_obj: Callable[..., Any], /, *args: Any, **kwargs: Any) -> TimedResult:
    started_at = perf_counter()
    value = callable_obj(*args, **kwargs)
    finished_at = perf_counter()
    return TimedResult(
        value=value,
        elapsed_ms=(finished_at - started_at) * 1000.0,
        started_at=started_at,
        finished_at=finished_at,
    )


def normalize_result(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if is_dataclass(value):
        return normalize_result(asdict(value))
    if hasattr(value, "model_dump") and callable(value.model_dump):  # Pydantic-compatible
        return normalize_result(value.model_dump())
    if isinstance(value, Mapping):
        return {str(key): normalize_result(item) for key, item in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [normalize_result(item) for item in value]
    if isinstance(value, set):
        return [normalize_result(item) for item in sorted(value, key=lambda item: repr(item))]
    if hasattr(value, "items") and callable(value.items):
        try:
            return normalize_result(dict(value.items()))
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        return normalize_result(vars(value))
    return repr(value)


def stable_json_dumps(value: Any) -> str:
    return json.dumps(normalize_result(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def build_cache_key(namespace: str, payload: Any, *, prefix: str = "big-o") -> str:
    normalized = stable_json_dumps(payload)
    digest = sha256(normalized.encode("utf-8")).hexdigest()
    return f"{prefix}:{namespace}:{digest}"


__all__ = [
    "TimedResult",
    "build_cache_key",
    "measure",
    "normalize_result",
    "stable_json_dumps",
    "timer",
]
