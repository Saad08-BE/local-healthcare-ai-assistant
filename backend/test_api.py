"""Small API contract tests that do not load embeddings or Ollama models."""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend import main as api_module


class LocalApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(api_module.app)

    def test_health_reports_local_mode_without_loading_pipeline(self) -> None:
        with patch.object(api_module, "_ollama_client") as client_factory:
            client_factory.return_value.is_online.return_value = False
            response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["privacy_mode"], "local-only")
        self.assertFalse(response.json()["pipeline_loaded"])

    def test_chat_rejects_empty_question(self) -> None:
        response = self.client.post("/api/chat", json={"question": "   "})
        self.assertEqual(response.status_code, 422)

    def test_chat_rejects_question_over_limit(self) -> None:
        response = self.client.post("/api/chat", json={"question": "x" * 4001})
        self.assertEqual(response.status_code, 422)

    def test_document_upload_rejects_non_pdf_extension(self) -> None:
        response = self.client.post("/api/documents", files={"file": ("notes.txt", b"hello", "text/plain")})
        self.assertEqual(response.status_code, 415)

    def test_document_upload_rejects_non_pdf_content(self) -> None:
        response = self.client.post("/api/documents", files={"file": ("notes.pdf", b"not a pdf", "application/pdf")})
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
