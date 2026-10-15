"""Unit tests for Phase 7 Streamlit UI components and chat session state."""

from __future__ import annotations

from pathlib import Path
import tempfile
from unittest.mock import MagicMock
import unittest

from app.config.settings import AppSettings
from app.llm.rag_pipeline import RAGResponse
from app.retrieval.document_retriever import DocumentSearchResult
from app.retrieval.vector_store import VectorSearchResult
from app.safety.policy import SafetyDecision
from app.ui.chat_state import ChatSession, get_current_session, initialize_session_state
from app.ui.evidence_viewer import render_evidence_panel
from app.ui.status import render_sidebar_status
from app.ui.input_controls import _safe_pdf_destination


class UITests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = AppSettings.from_environment()

    def test_sidebar_status_reports_local_metrics(self) -> None:
        """Verify render_sidebar_status queries local endpoints and metrics."""
        mock_st = MagicMock()
        status = render_sidebar_status(mock_st, self.settings)

        self.assertIn("ollama_online", status)
        self.assertIn("model_ready", status)
        self.assertIn("pdf_count", status)
        self.assertIsInstance(status["pdf_count"], int)
        mock_st.sidebar.metric.assert_called_once()

    def test_evidence_panel_renders_documents_and_cases(self) -> None:
        """Verify render_evidence_panel properly formats all evidence sources."""
        mock_st = MagicMock()
        mock_tab1, mock_tab2, mock_tab3 = MagicMock(), MagicMock(), MagicMock()
        mock_st.tabs.return_value = [mock_tab1, mock_tab2, mock_tab3]

        doc = DocumentSearchResult(
            chunk_id="chunk_1",
            doc_id="doc_1",
            filename="Test_Report.pdf",
            page_number=1,
            score=0.88,
            text="Patient blood sugar within normal limits.",
            citation="Test_Report.pdf (Page 1)",
        )
        case = VectorSearchResult(
            record_id=1,
            score=0.75,
            text="Patient with fever and cough managed with hydration.",
            metadata={"primary_diagnosis": "Viral Infection"},
        )
        response = RAGResponse(
            question="What is the patient status?",
            answer="Patient is stable.",
            retrieved_cases=[case],
            cohort_statistics={"symptom_evidence": {"fever": [{"diagnosis": "Viral", "percentage": 80.0}]}},
            document_sources=[doc],
            disclaimer="Educational only",
            llm_model="qwen2.5:3b",
            is_offline_fallback=False,
            urgent_warning=False,
            total_latency_seconds=0.45,
            safety_decision=SafetyDecision(allowed=True, normalized_question="What is the patient status?"),
        )

        render_evidence_panel(mock_st, response)
        mock_st.expander.assert_called_once()
        mock_st.tabs.assert_called_once()

    def test_chat_session_state_and_auto_title(self) -> None:
        """Verify ChatSession auto-titling from user query and message persistence."""
        session = ChatSession.create_new(title="New Consultation")
        self.assertEqual(session.title, "New Consultation")

        # First message should auto-title
        session.add_message("user", "What are the common symptoms of asthma?")
        self.assertTrue(session.title.startswith("What are the common"))
        self.assertEqual(len(session.messages), 1)

        # Assistant response should be appended
        session.add_message("assistant", "Common symptoms include wheezing and shortness of breath.")
        self.assertEqual(len(session.messages), 2)

    def test_temporary_chat_mode_isolation(self) -> None:
        """Verify temporary chat session remains marked as temporary."""
        temp_sess = ChatSession.create_new(is_temporary=True)
        self.assertTrue(temp_sess.is_temporary)
        temp_sess.add_message("user", "Secret question that shouldn't change title")
        self.assertEqual(temp_sess.title, "🔒 Temporary Consultation")

    def test_pdf_upload_destination_is_local_and_does_not_overwrite(self) -> None:
        """Uploaded filenames must not escape the document directory or replace a prior file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            document_dir = Path(tmp_dir)
            (document_dir / "report.pdf").write_bytes(b"existing")

            destination = _safe_pdf_destination(document_dir, "../../report.pdf")

            self.assertEqual(destination.parent, document_dir)
            self.assertEqual(destination.name, "report_1.pdf")
            self.assertEqual((document_dir / "report.pdf").read_bytes(), b"existing")

    def test_pdf_upload_destination_rejects_non_pdf(self) -> None:
        """The document repository only accepts PDF upload names."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaises(ValueError):
                _safe_pdf_destination(Path(tmp_dir), "medical-notes.txt")


if __name__ == "__main__":
    unittest.main()
