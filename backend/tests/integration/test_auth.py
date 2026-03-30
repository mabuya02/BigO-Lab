from __future__ import annotations

import unittest

from tests.helpers import get_client


class AuthApiTests(unittest.TestCase):
    def test_register_login_and_current_user(self) -> None:
        with get_client() as client:
            register_response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": "learner@example.com",
                    "password": "strongpassword123",
                    "full_name": "Learner One",
                },
            )
            self.assertEqual(register_response.status_code, 201)
            self.assertEqual(register_response.json()["email"], "learner@example.com")

            login_response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": "learner@example.com",
                    "password": "strongpassword123",
                },
            )
            self.assertEqual(login_response.status_code, 200)
            token = login_response.json()["access_token"]
            self.assertTrue(token)

            me_response = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(me_response.status_code, 200)
            self.assertEqual(me_response.json()["full_name"], "Learner One")
