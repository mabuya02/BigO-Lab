from __future__ import annotations

import time
import unittest
from collections import Counter
from dataclasses import dataclass

from app.core.performance import TimedResult, build_cache_key, measure, normalize_result, stable_json_dumps, timer


@dataclass
class ExamplePayload:
    name: str
    values: tuple[int, ...]


class PerformanceTests(unittest.TestCase):
    def test_timer_records_elapsed_time(self) -> None:
        with timer() as state:
            time.sleep(0.01)

        self.assertGreater(state["elapsed_ms"], 0)
        self.assertGreaterEqual(state["finished_at"], state["started_at"])

    def test_measure_wraps_call_result(self) -> None:
        result = measure(lambda left, right: left + right, 2, 3)

        self.assertIsInstance(result, TimedResult)
        self.assertEqual(result.value, 5)
        self.assertGreaterEqual(result.finished_at, result.started_at)

    def test_normalize_result_handles_dataclasses_and_counters(self) -> None:
        payload = ExamplePayload(name="demo", values=(1, 2, 3))
        normalized = normalize_result({"payload": payload, "counts": Counter({"b": 1, "a": 2})})

        self.assertEqual(normalized["payload"]["name"], "demo")
        self.assertEqual(normalized["payload"]["values"], [1, 2, 3])
        self.assertEqual(normalized["counts"], {"a": 2, "b": 1})

    def test_stable_json_and_cache_key_are_order_independent(self) -> None:
        left = {"b": 2, "a": 1}
        right = {"a": 1, "b": 2}

        self.assertEqual(stable_json_dumps(left), stable_json_dumps(right))
        self.assertEqual(
            build_cache_key("experiments", left),
            build_cache_key("experiments", right),
        )

