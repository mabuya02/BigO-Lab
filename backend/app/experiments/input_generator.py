from __future__ import annotations

import json
import hashlib
import random
from dataclasses import dataclass, field
from typing import Any, Literal, Sequence

InputKind = Literal["array", "numbers", "string"]
InputProfile = Literal["random", "sorted", "reversed", "duplicate-heavy", "nearly-sorted"]


@dataclass(slots=True)
class GeneratedInput:
    input_size: int
    kind: InputKind
    profile: InputProfile
    payload: Any
    stdin: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _build_rng(seed: int | None, input_size: int, profile: str) -> random.Random:
    if seed is not None:
        derived_seed = seed
    else:
        digest = hashlib.sha256(f"{input_size}:{profile}".encode("utf-8")).digest()
        derived_seed = int.from_bytes(digest[:8], "big")
    return random.Random(derived_seed)


def _generate_array(size: int, profile: InputProfile, rng: random.Random) -> list[int]:
    if size <= 0:
        return []

    values = list(range(size))

    if profile == "sorted":
        return values

    if profile == "reversed":
        return list(reversed(values))

    if profile == "duplicate-heavy":
        bucket_count = max(1, min(5, size))
        return [rng.randrange(bucket_count) for _ in range(size)]

    if profile == "nearly-sorted":
        values = list(range(size))
        swaps = max(1, size // 10)
        for _ in range(swaps):
            left = rng.randrange(size)
            right = rng.randrange(size)
            values[left], values[right] = values[right], values[left]
        return values

    rng.shuffle(values)
    return values


def _generate_numbers(size: int, profile: InputProfile, rng: random.Random) -> list[int]:
    if profile in {"sorted", "nearly-sorted"}:
        return list(range(size))
    if profile == "reversed":
        return list(reversed(range(size)))
    if profile == "duplicate-heavy":
        return [rng.randrange(max(1, size // 3 or 1)) for _ in range(size)]
    return [rng.randrange(max(1, size * 10)) for _ in range(size)]


def _generate_string(size: int, profile: InputProfile, rng: random.Random) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    if size <= 0:
        return ""
    if profile == "sorted":
        return "".join(alphabet[i % len(alphabet)] for i in range(size))
    if profile == "reversed":
        return "".join(reversed([alphabet[i % len(alphabet)] for i in range(size)]))
    if profile == "duplicate-heavy":
        return "".join(rng.choice("aaaaab") for _ in range(size))
    return "".join(rng.choice(alphabet) for _ in range(size))


def encode_stdin(payload: Any) -> str:
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload if payload.endswith("\n") else f"{payload}\n"
    if isinstance(payload, (int, float)):
        return f"{payload}\n"
    return f"{json.dumps(payload, separators=(',', ':'))}\n"


class InputGenerator:
    def generate(
        self,
        input_size: int,
        *,
        kind: InputKind = "array",
        profile: InputProfile = "random",
        seed: int | None = None,
    ) -> GeneratedInput:
        rng = _build_rng(seed, input_size, profile)

        if kind == "array":
            payload = _generate_array(input_size, profile, rng)
        elif kind == "numbers":
            payload = _generate_numbers(input_size, profile, rng)
        elif kind == "string":
            payload = _generate_string(input_size, profile, rng)
        else:  # pragma: no cover - guarded by Literal
            raise ValueError(f"Unsupported input kind: {kind}")

        metadata = {
            "kind": kind,
            "profile": profile,
            "seed": seed,
        }
        return GeneratedInput(
            input_size=input_size,
            kind=kind,
            profile=profile,
            payload=payload,
            stdin=encode_stdin(payload),
            metadata=metadata,
        )

    def generate_series(
        self,
        input_sizes: Sequence[int],
        *,
        kind: InputKind = "array",
        profile: InputProfile = "random",
        seed: int | None = None,
    ) -> list[GeneratedInput]:
        return [
            self.generate(size, kind=kind, profile=profile, seed=None if seed is None else seed + index)
            for index, size in enumerate(input_sizes)
        ]
