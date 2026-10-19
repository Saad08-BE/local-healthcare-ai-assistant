"""Tests for registration, password hashing, CSRF, and session authentication."""

import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend import main as api_module
from backend.database import initialize_database


class AuthenticationApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "auth-test.sqlite3"
        self.previous_database_path = os.environ.get("HEALTHAI_DATABASE_PATH")
        os.environ["HEALTHAI_DATABASE_PATH"] = str(self.database_path)
        initialize_database(self.database_path)
        self.client = TestClient(api_module.app)
        token_response = self.client.get("/api/auth/csrf")
        self.csrf_token = token_response.json()["csrf_token"]
        self.headers = {"X-CSRF-Token": self.csrf_token}

    def tearDown(self) -> None:
        self.client.close()
        if self.previous_database_path is None:
            os.environ.pop("HEALTHAI_DATABASE_PATH", None)
        else:
            os.environ["HEALTHAI_DATABASE_PATH"] = self.previous_database_path
        self.temp_dir.cleanup()

    def test_registration_creates_account_and_authenticated_session(self) -> None:
        response = self.client.post(
            "/api/auth/register",
            json={"email": "Person@example.com", "password": "correct-horse-123"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["user"]["email"], "person@example.com")
        self.assertNotIn("password", response.json()["user"])
        self.assertTrue(response.cookies.get("healthai_session"))
        me = self.client.get("/api/auth/me")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["user"]["email"], "person@example.com")

    def test_registration_requires_csrf_header(self) -> None:
        response = self.client.post(
            "/api/auth/register",
            json={"email": "person@example.com", "password": "correct-horse-123"},
        )
        self.assertEqual(response.status_code, 403)

    def test_duplicate_email_is_rejected_case_insensitively(self) -> None:
        first = self.client.post(
            "/api/auth/register",
            json={"email": "Person@example.com", "password": "correct-horse-123"},
            headers=self.headers,
        )
        second = self.client.post(
            "/api/auth/register",
            json={"email": "PERSON@example.com", "password": "another-password-123"},
            headers=self.headers,
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 409)

    def test_login_rejects_wrong_password(self) -> None:
        self.client.post(
            "/api/auth/register",
            json={"email": "person@example.com", "password": "correct-horse-123"},
            headers=self.headers,
        )
        response = self.client.post(
            "/api/auth/login",
            json={"email": "person@example.com", "password": "wrong-password-123"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 401)

    def test_logout_invalidates_session(self) -> None:
        self.client.post(
            "/api/auth/register",
            json={"email": "person@example.com", "password": "correct-horse-123"},
            headers=self.headers,
        )
        response = self.client.post("/api/auth/logout", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

    def test_private_me_endpoint_requires_login(self) -> None:
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)


if __name__ == "__main__":
    unittest.main()
