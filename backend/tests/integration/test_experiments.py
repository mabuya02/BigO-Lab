from __future__ import annotations

import unittest

from tests.helpers import auth_headers, get_client


class ExperimentApiTests(unittest.TestCase):
    def test_create_experiment_shell(self) -> None:
        with get_client() as client:
            headers = auth_headers(client)

            project_response = client.post(
                "/api/v1/projects",
                json={"name": "Sorting Lab", "description": "Compare sort algorithms"},
                headers=headers,
            )
            self.assertEqual(project_response.status_code, 201)
            project_id = project_response.json()["id"]

            snippet_response = client.post(
                f"/api/v1/projects/{project_id}/snippets",
                json={
                    "title": "Bubble Sort",
                    "language": "python",
                    "code": "def bubble_sort(items):\n    return items\n",
                },
                headers=headers,
            )
            self.assertEqual(snippet_response.status_code, 201)
            snippet_id = snippet_response.json()["id"]

            experiment_response = client.post(
                f"/api/v1/projects/{project_id}/experiments",
                json={
                    "name": "Baseline run",
                    "snippet_id": snippet_id,
                    "language": "python",
                    "input_sizes": [10, 100, 1000],
                    "repetitions": 3,
                },
                headers=headers,
            )
            self.assertEqual(experiment_response.status_code, 201)
            self.assertEqual(experiment_response.json()["input_sizes"], [10, 100, 1000])

            list_response = client.get(
                f"/api/v1/projects/{project_id}/experiments",
                headers=headers,
            )
            self.assertEqual(list_response.status_code, 200)
            self.assertEqual(len(list_response.json()), 1)

    def test_run_experiment_persists_runs_metrics_and_complexity(self) -> None:
        with get_client() as client:
            headers = auth_headers(client)

            project_response = client.post(
                "/api/v1/projects",
                json={"name": "Runtime Lab", "description": "Execution analysis"},
                headers=headers,
            )
            self.assertEqual(project_response.status_code, 201)
            project_id = project_response.json()["id"]

            snippet_response = client.post(
                f"/api/v1/projects/{project_id}/snippets",
                json={
                    "title": "Reader",
                    "language": "python",
                    "code": (
                        "import json\n"
                        "values = json.loads(input())\n"
                        "total = 0\n"
                        "for value in values:\n"
                        "    total += value\n"
                        "print(total)\n"
                    ),
                },
                headers=headers,
            )
            self.assertEqual(snippet_response.status_code, 201)
            snippet_id = snippet_response.json()["id"]

            experiment_response = client.post(
                f"/api/v1/projects/{project_id}/experiments",
                json={
                    "name": "Input sweep",
                    "snippet_id": snippet_id,
                    "language": "python",
                    "input_kind": "array",
                    "input_profile": "sorted",
                    "input_sizes": [2, 4, 8],
                    "repetitions": 1,
                },
                headers=headers,
            )
            self.assertEqual(experiment_response.status_code, 201)
            experiment_id = experiment_response.json()["id"]

            run_response = client.post(
                f"/api/v1/projects/{project_id}/experiments/{experiment_id}/run",
                json={"backend": "local", "refresh_complexity": True},
                headers=headers,
            )
            self.assertEqual(run_response.status_code, 200)
            payload = run_response.json()
            self.assertEqual(payload["status"], "completed")
            self.assertEqual(len(payload["runs"]), 3)
            self.assertIsNotNone(payload["metrics_snapshot"])
            self.assertGreaterEqual(payload["metrics_snapshot"]["summary"]["total_line_executions"], 1)
            self.assertIsNotNone(payload["latest_complexity_estimate"])

            metrics_response = client.get(
                f"/api/v1/projects/{project_id}/experiments/{experiment_id}/metrics",
                headers=headers,
            )
            self.assertEqual(metrics_response.status_code, 200)
            self.assertEqual(metrics_response.json()["summary"]["total_runs"], 3)
