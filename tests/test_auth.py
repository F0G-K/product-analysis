from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from backend.main import create_app


class AuthenticationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_default_admin_can_login_and_read_current_user(self) -> None:
        response = self.client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        self.assertEqual(response.status_code, 200)
        token = response.json()["data"]["access_token"]

        current_user = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(current_user.status_code, 200)
        self.assertEqual(current_user.json()["data"]["name"], "管理员")

    def test_wrong_password_is_rejected(self) -> None:
        response = self.client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrong"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], 40101)

    def test_business_api_requires_login(self) -> None:
        response = self.client.get("/api/v1/tasks")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], 40101)

    def test_logout_invalidates_token(self) -> None:
        login = self.client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        token = login.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        self.assertEqual(
            self.client.post("/api/v1/auth/logout", headers=headers).status_code,
            200,
        )
        self.assertEqual(
            self.client.get("/api/v1/auth/me", headers=headers).status_code,
            401,
        )


if __name__ == "__main__":
    unittest.main()
