from __future__ import annotations

import time
import unittest

from tests.helpers import get_client


class ExecutionApiTests(unittest.TestCase):
    def test_run_code_sync(self) -> None:
        with get_client() as client:
            response = client.post(
                "/api/v1/execution/run",
                json={
                    "code": "print('hello from sandbox')\n",
                    "stdin": "",
                    "backend": "local",
                },
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["status"], "completed")
            self.assertEqual(payload["stdout"], "hello from sandbox\n")
            self.assertEqual(payload["exit_code"], 0)
            self.assertEqual(payload["backend"], "local")

    def test_run_code_with_instrumentation(self) -> None:
        with get_client() as client:
            response = client.post(
                "/api/v1/execution/run",
                json={
                    "code": (
                        "def square_sum(limit):\n"
                        "    total = 0\n"
                        "    for value in range(limit):\n"
                        "        total += value * value\n"
                        "    return total\n"
                        "\n"
                        "print(square_sum(4))\n"
                    ),
                    "backend": "local",
                    "instrument": True,
                },
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["status"], "completed")
            self.assertEqual(payload["stdout"], "14\n")
            self.assertIsNotNone(payload["instrumentation"])
            self.assertEqual(payload["instrumentation"]["function_call_counts"]["square_sum"], 1)
            self.assertEqual(next(iter(payload["instrumentation"]["loop_iteration_counts"].values())), 4)
            self.assertIn(3, payload["instrumentation"]["line_numbers"])

    def test_run_code_timeout(self) -> None:
        with get_client() as client:
            response = client.post(
                "/api/v1/execution/run",
                json={
                    "code": "import time\ntime.sleep(10)\n",
                    "timeout_seconds": 1,
                    "backend": "local",
                },
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["status"], "timeout")
            self.assertTrue(payload["timed_out"])

    def test_queue_execution_job_and_poll_result(self) -> None:
        with get_client() as client:
            submit_response = client.post(
                "/api/v1/execution/jobs",
                json={
                    "code": "print('queued execution complete')\n",
                    "backend": "local",
                },
            )
            self.assertEqual(submit_response.status_code, 202)
            job_id = submit_response.json()["job_id"]

            final_payload = None
            for _ in range(40):
                poll_response = client.get(
                    f"/api/v1/execution/jobs/{job_id}",
                )
                self.assertEqual(poll_response.status_code, 200)
                final_payload = poll_response.json()
                if final_payload["status"] in {"completed", "failed", "timeout"}:
                    break
                time.sleep(0.05)

            self.assertIsNotNone(final_payload)
            self.assertEqual(final_payload["status"], "completed")
            self.assertEqual(final_payload["result"]["stdout"], "queued execution complete\n")
