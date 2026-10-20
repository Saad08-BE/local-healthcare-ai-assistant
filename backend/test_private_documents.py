"""Privacy regression tests for per-conversation PDF storage and API boundaries."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend import main as api_module
from backend.database import initialize_database


class PrivateConversationDocumentTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "healthai.sqlite3"
        self.previous_path = os.environ.get("HEALTHAI_DATABASE_PATH")
        os.environ["HEALTHAI_DATABASE_PATH"] = str(self.database_path)
        initialize_database(self.database_path)
        self.client = TestClient(api_module.app)
        csrf = self.client.get("/api/auth/csrf").json()["csrf_token"]
        self.headers = {"X-CSRF-Token": csrf}
        self._register(self.client, "owner@example.com")
        created = self.client.post(
            "/api/conversations", json={"title": "Owner conversation"}, headers=self.headers
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.conversation_id = created.json()["conversation"]["id"]

    def tearDown(self):
        self.client.close()
        if self.previous_path is None:
            os.environ.pop("HEALTHAI_DATABASE_PATH", None)
        else:
            os.environ["HEALTHAI_DATABASE_PATH"] = self.previous_path
        self.temp_dir.cleanup()

    @staticmethod
    def _register(client, email):
        csrf = client.get("/api/auth/csrf").json()["csrf_token"]
        response = client.post(
            "/api/auth/register",
            json={"email": email, "password": "safe-password-123"},
            headers={"X-CSRF-Token": csrf},
        )
        if response.status_code != 201:
            raise AssertionError(response.text)

    def test_conversation_document_routes_require_login(self):
        client = TestClient(api_module.app)
        try:
            response = client.get(f"/api/conversations/{self.conversation_id}/documents")
            self.assertEqual(response.status_code, 401)
        finally:
            client.close()

    def test_other_user_cannot_list_or_delete_private_report(self):
        other = TestClient(api_module.app)
        try:
            self._register(other, "other@example.com")
            csrf = other.cookies.get("healthai_csrf")
            headers = {"X-CSRF-Token": csrf}
            self.assertEqual(
                other.get(f"/api/conversations/{self.conversation_id}/documents").status_code,
                404,
            )
            response = other.delete(
                f"/api/conversations/{self.conversation_id}/documents/not-a-document",
                headers=headers,
            )
            self.assertEqual(response.status_code, 404)
        finally:
            other.close()

    def test_legacy_global_document_library_is_disabled(self):
        self.assertEqual(self.client.get("/api/documents").status_code, 410)
        response = self.client.post(
            "/api/documents",
            files={"file": ("notes.pdf", b"%PDF-1.4 sample", "application/pdf")},
        )
        self.assertEqual(response.status_code, 410)

    def test_private_document_upload_rejects_non_pdf_before_storage(self):
        response = self.client.post(
            f"/api/conversations/{self.conversation_id}/documents",
            headers=self.headers,
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )
        self.assertEqual(response.status_code, 415)
        listed = self.client.get(f"/api/conversations/{self.conversation_id}/documents")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["documents"], [])

    def test_user_cannot_chat_in_another_users_conversation(self):
        other = TestClient(api_module.app)
        try:
            self._register(other, "other@example.com")
            csrf = other.cookies.get("healthai_csrf")
            response = other.post(
                "/api/chat",
                headers={"X-CSRF-Token": csrf},
                json={
                    "question": "Summarize my report",
                    "model": "qwen2.5:3b",
                    "conversation_id": self.conversation_id,
                },
            )
            self.assertEqual(response.status_code, 404)
        finally:
            other.close()


if __name__ == "__main__":
    unittest.main()
