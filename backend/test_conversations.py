"""Tests for authenticated persistent conversation endpoints."""

import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend import main as api_module
from backend.database import initialize_database


class ConversationApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "conversations.sqlite3"
        self.previous_database_path = os.environ.get("HEALTHAI_DATABASE_PATH")
        os.environ["HEALTHAI_DATABASE_PATH"] = str(self.database_path)
        initialize_database(self.database_path)
        self.client = TestClient(api_module.app)
        csrf = self.client.get("/api/auth/csrf")
        self.headers = {"X-CSRF-Token": csrf.json()["csrf_token"]}

    def tearDown(self) -> None:
        self.client.close()
        if self.previous_database_path is None:
            os.environ.pop("HEALTHAI_DATABASE_PATH", None)
        else:
            os.environ["HEALTHAI_DATABASE_PATH"] = self.previous_database_path
        self.temp_dir.cleanup()

    def _register(self, email: str) -> None:
        response = self.client.post(
            "/api/auth/register",
            json={"email": email, "password": "safe-password-123"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 201, response.text)

    def test_conversation_endpoints_require_login(self) -> None:
        response = self.client.get("/api/conversations")
        self.assertEqual(response.status_code, 401)

    def test_create_list_and_reopen_conversation(self) -> None:
        self._register("owner@example.com")
        created = self.client.post(
            "/api/conversations",
            json={"title": "My report discussion"},
            headers=self.headers,
        )
        self.assertEqual(created.status_code, 201, created.text)
        conversation_id = created.json()["conversation"]["id"]

        listed = self.client.get("/api/conversations")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["conversations"][0]["id"], conversation_id)

        reopened = self.client.get(f"/api/conversations/{conversation_id}")
        self.assertEqual(reopened.status_code, 200)
        self.assertEqual(reopened.json()["messages"], [])

    def test_user_cannot_read_or_delete_another_users_conversation(self) -> None:
        self._register("owner@example.com")
        created = self.client.post(
            "/api/conversations",
            json={"title": "Private"},
            headers=self.headers,
        )
        conversation_id = created.json()["conversation"]["id"]

        other_client = TestClient(api_module.app)
        try:
            csrf = other_client.get("/api/auth/csrf").json()["csrf_token"]
            response = other_client.post(
                "/api/auth/register",
                json={"email": "other@example.com", "password": "safe-password-456"},
                headers={"X-CSRF-Token": csrf},
            )
            self.assertEqual(response.status_code, 201)
            self.assertEqual(other_client.get(f"/api/conversations/{conversation_id}").status_code, 404)
            deleted = other_client.delete(
                f"/api/conversations/{conversation_id}",
                headers={"X-CSRF-Token": csrf},
            )
            self.assertEqual(deleted.status_code, 404)
            self.assertEqual(self.client.get(f"/api/conversations/{conversation_id}").status_code, 200)
        finally:
            other_client.close()

    def test_delete_conversation_requires_csrf(self) -> None:
        self._register("owner@example.com")
        created = self.client.post(
            "/api/conversations",
            json={"title": "Private"},
            headers=self.headers,
        )
        conversation_id = created.json()["conversation"]["id"]
        response = self.client.delete(f"/api/conversations/{conversation_id}")
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
