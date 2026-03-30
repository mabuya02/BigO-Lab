from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class InstrumentationSnapshot:
    line_counts: dict[int, int] = field(default_factory=dict)
    function_call_counts: dict[str, int] = field(default_factory=dict)
    loop_iteration_counts: dict[str, int] = field(default_factory=dict)


class ExecutionTracker:
    def __init__(self) -> None:
        self._line_counts: Counter[int] = Counter()
        self._function_call_counts: Counter[str] = Counter()
        self._loop_iteration_counts: Counter[str] = Counter()

    def line(self, line_no: int) -> None:
        self._line_counts[int(line_no)] += 1

    def function_call(self, qualname: str) -> None:
        self._function_call_counts[qualname] += 1

    def loop_iteration(self, loop_key: str) -> None:
        self._loop_iteration_counts[loop_key] += 1

    def snapshot(self) -> InstrumentationSnapshot:
        return InstrumentationSnapshot(
            line_counts=dict(self._line_counts),
            function_call_counts=dict(self._function_call_counts),
            loop_iteration_counts=dict(self._loop_iteration_counts),
        )

    def reset(self) -> None:
        self._line_counts.clear()
        self._function_call_counts.clear()
        self._loop_iteration_counts.clear()

    def to_dict(self) -> dict[str, Any]:
        snapshot = self.snapshot()
        return {
            "line_counts": snapshot.line_counts,
            "function_call_counts": snapshot.function_call_counts,
            "loop_iteration_counts": snapshot.loop_iteration_counts,
        }


def create_tracker() -> ExecutionTracker:
    return ExecutionTracker()


__all__ = ["ExecutionTracker", "InstrumentationSnapshot", "create_tracker"]
