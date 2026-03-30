from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from textwrap import dedent
import unittest

from app.instrumentation.parser import compile_instrumented_source, instrument_source
from app.instrumentation.tracker import ExecutionTracker


def run_code(source: str, *, tracker: ExecutionTracker | None = None) -> tuple[str, dict]:
    namespace: dict = {"__name__": "__main__"}
    if tracker is not None:
        namespace["_big_o_tracker"] = tracker

    buffer = StringIO()
    with redirect_stdout(buffer):
        exec(compile(source, "<test>", "exec"), namespace)
    return buffer.getvalue(), namespace


class InstrumentationTests(unittest.TestCase):
    def test_tracker_snapshot_and_reset(self) -> None:
        tracker = ExecutionTracker()
        tracker.line(10)
        tracker.line(10)
        tracker.function_call("outer.inner")
        tracker.loop_iteration("outer@12:For")

        snapshot = tracker.snapshot()
        self.assertEqual(snapshot.line_counts[10], 2)
        self.assertEqual(snapshot.function_call_counts["outer.inner"], 1)
        self.assertEqual(snapshot.loop_iteration_counts["outer@12:For"], 1)

        tracker.reset()
        reset_snapshot = tracker.snapshot()
        self.assertEqual(reset_snapshot.line_counts, {})
        self.assertEqual(reset_snapshot.function_call_counts, {})
        self.assertEqual(reset_snapshot.loop_iteration_counts, {})

    def test_instrumented_source_preserves_output_and_records_counts(self) -> None:
        source = dedent(
            """
            from __future__ import annotations

            def accumulate(limit):
                \"\"\"Return the sum of even numbers below limit.\"\"\"
                total = 0
                for index in range(limit):
                    if index % 2 == 0:
                        total += index
                return total

            print(accumulate(6))
            """
        ).strip()

        original_stdout, _ = run_code(source)
        instrumented = instrument_source(source, tracker_name="_big_o_tracker")
        tracker = ExecutionTracker()
        instrumented_stdout, _ = run_code(
            instrumented.instrumented_source,
            tracker=tracker,
        )

        self.assertEqual(instrumented_stdout, original_stdout)
        self.assertEqual(instrumented_stdout, "6\n")
        self.assertEqual(instrumented.metadata.function_names, ["accumulate"])
        self.assertEqual(instrumented.metadata.loop_line_numbers, [6])

        snapshot = tracker.snapshot()
        self.assertEqual(snapshot.function_call_counts["accumulate"], 1)
        self.assertEqual(snapshot.loop_iteration_counts["accumulate@6:For"], 6)
        self.assertEqual(snapshot.line_counts[5], 1)
        self.assertEqual(snapshot.line_counts[6], 1)
        self.assertEqual(snapshot.line_counts[7], 6)
        self.assertEqual(snapshot.line_counts[8], 3)
        self.assertEqual(snapshot.line_counts[9], 1)

    def test_nested_functions_use_qualified_names(self) -> None:
        source = dedent(
            """
            def outer(n):
                def inner(value):
                    count = 0
                    while count < value:
                        count += 1
                    return count

                return inner(n)

            print(outer(3))
            """
        ).strip()

        instrumented = instrument_source(source, tracker_name="_big_o_tracker")
        tracker = ExecutionTracker()
        stdout, _ = run_code(instrumented.instrumented_source, tracker=tracker)

        self.assertEqual(stdout, "3\n")
        snapshot = tracker.snapshot()
        self.assertEqual(snapshot.function_call_counts["outer"], 1)
        self.assertEqual(snapshot.function_call_counts["outer.inner"], 1)
        self.assertEqual(snapshot.loop_iteration_counts["outer.inner@4:While"], 3)
        self.assertEqual(snapshot.line_counts[3], 1)
        self.assertEqual(snapshot.line_counts[4], 1)
        self.assertEqual(snapshot.line_counts[5], 3)
        self.assertEqual(snapshot.line_counts[6], 1)

    def test_compile_helper_returns_executable_code(self) -> None:
        source = "print('ok')\n"
        instrumented = instrument_source(source)
        compiled = compile_instrumented_source(instrumented)
        tracker = ExecutionTracker()
        stdout_buffer = StringIO()
        namespace = {"__name__": "__main__", "_big_o_tracker": tracker}

        with redirect_stdout(stdout_buffer):
            exec(compiled, namespace)

        self.assertEqual(stdout_buffer.getvalue(), "ok\n")
