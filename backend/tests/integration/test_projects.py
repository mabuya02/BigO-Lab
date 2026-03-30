from __future__ import annotations

import unittest

from tests.helpers import auth_headers, get_client


class ProjectAndSnippetApiTests(unittest.TestCase):
    def test_create_project_and_save_code(self) -> None:
        with get_client() as client:
            headers = auth_headers(client)

            project_response = client.post(
                "/api/v1/projects",
                json={
                    "name": "Playground Workspace",
                    "description": "Personal algorithm experiments",
                },
                headers=headers,
            )
            self.assertEqual(project_response.status_code, 201)
            project_id = project_response.json()["id"]

            snippet_response = client.post(
                f"/api/v1/projects/{project_id}/snippets",
                json={
                    "title": "Linear Search",
                    "language": "python",
                    "code": "def linear_search(items, target):\n    return -1\n",
                },
                headers=headers,
            )
            self.assertEqual(snippet_response.status_code, 201)
            snippet_id = snippet_response.json()["id"]
            self.assertEqual(snippet_response.json()["version"], 1)

            update_response = client.put(
                f"/api/v1/projects/{project_id}/snippets/{snippet_id}",
                json={
                    "code": "def linear_search(items, target):\n    return items.index(target) if target in items else -1\n"
                },
                headers=headers,
            )
            self.assertEqual(update_response.status_code, 200)
            self.assertEqual(update_response.json()["version"], 2)

            project_list_response = client.get("/api/v1/projects", headers=headers)
            self.assertEqual(project_list_response.status_code, 200)
            self.assertEqual(len(project_list_response.json()), 1)

            snippet_list_response = client.get(
                f"/api/v1/projects/{project_id}/snippets",
                headers=headers,
            )
            self.assertEqual(snippet_list_response.status_code, 200)
            self.assertEqual(len(snippet_list_response.json()), 1)
