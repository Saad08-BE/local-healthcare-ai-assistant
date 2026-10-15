"""Integration tests for the unified Healthcare RAG pipeline (Phase 6)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

from app.config.settings import AppSettings
from app.llm.ollama_client import LLMGenerationResult, LocalServiceUnavailable
from app.llm.prompts import build_grounded_prompt
from app.llm.rag_pipeline import (
    HealthcareRAGPipeline,
    RAGResponse,
    _build_document_context_block,
)
from app.retrieval.dataset_retriever import DatasetRetriever, RetrievalContext
from app.retrieval.document_retriever import DocumentRetriever, DocumentSearchResult
from app.retrieval.vector_store import VectorSearchResult
from app.safety import SafetyDecision


# ---------------------------------------------------------------------------
# Helpers / stubs
# ---------------------------------------------------------------------------

def _make_settings() -> AppSettings:
    """Return in-memory AppSettings pointing to a temp directory."""
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    return AppSettings(
        paths=__import__("app.config.settings", fromlist=["LocalPathPolicy"]).LocalPathPolicy.for_project(tmp),
        ollama_base_url="http://127.0.0.1:11434",
        llm_model="qwen2.5:3b",
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        chunk_size=600,
        chunk_overlap=100,
        top_k=5,
        similarity_threshold=0.20,
        host="127.0.0.1",
        port=8501,
        debug=False,
    )


def _stub_retrieval_context(empty: bool = False) -> RetrievalContext:
    records = [] if empty else [
        VectorSearchResult(
            record_id="r1",
            score=0.75,
            text="Patient: 45M, symptoms: fever, cough. Diagnosis: Pneumonia. Treatment: Antibiotics.",
            metadata={"age": 45, "gender": "Male"},
        )
    ]
    cohort = {} if empty else {
        "symptom_evidence": {
            "fever, cough": [{"diagnosis": "Pneumonia", "percentage": 42}]
        }
    }
    return RetrievalContext(
        query="fever and cough",
        evidence_records=records,
        cohort_statistics=cohort,
        formatted_context_block="[Dataset evidence block]",
    )


def _stub_doc_results() -> list[DocumentSearchResult]:
    return [
        DocumentSearchResult(
            chunk_id="chunk_001",
            doc_id="doc_A",
            filename="Clinical_Guidelines.pdf",
            page_number=3,
            score=0.68,
            text="Pneumonia treatment guidelines: administer amoxicillin for mild community-acquired cases.",
            citation="Clinical_Guidelines.pdf (Page 3)",
        )
    ]


def _make_pipeline(settings: AppSettings) -> HealthcareRAGPipeline:
    retriever = MagicMock(spec=DatasetRetriever)
    doc_retriever = MagicMock(spec=DocumentRetriever)
    ollama = MagicMock()

    retriever.retrieve_context.return_value = _stub_retrieval_context()
    doc_retriever.search.return_value = _stub_doc_results()

    return HealthcareRAGPipeline(
        retriever=retriever,
        document_retriever=doc_retriever,
        ollama_client=ollama,
        settings=settings,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class UnifiedRAGPipelineTests(unittest.TestCase):
    """Integration tests for HealthcareRAGPipeline Phase 6."""

    def setUp(self) -> None:
        self.settings = _make_settings()
        self.settings.paths.create_runtime_directories()
        self.pipeline = _make_pipeline(self.settings)

    # ------------------------------------------------------------------
    # 1. Safety blocking
    # ------------------------------------------------------------------

    def test_safety_blocked_query_returns_immediately(self) -> None:
        """Blocked queries must never reach retrieval or LLM."""
        response: RAGResponse = self.pipeline.answer_question("")
        self.assertFalse(response.safety_decision.allowed)
        self.assertEqual(response.retrieved_cases, [])
        self.assertEqual(response.document_sources, [])
        self.assertIsNone(response.llm_model)
        # Retrieval must NOT be called
        self.pipeline.retriever.retrieve_context.assert_not_called()
        self.pipeline.document_retriever.search.assert_not_called()

    def test_patient_record_search_blocked(self) -> None:
        """Patient-specific record lookups must be rejected by safety policy."""
        response = self.pipeline.answer_question("Look up patient ID 12345 records")
        self.assertFalse(response.safety_decision.allowed)

    # ------------------------------------------------------------------
    # 2. Normal online pipeline (LLM available)
    # ------------------------------------------------------------------

    def test_both_retrieval_sources_are_queried(self) -> None:
        """Both dataset retriever and document retriever must be called for valid queries."""
        self.pipeline.ollama.generate.return_value = LLMGenerationResult(
            response_text="Fever and cough may indicate respiratory infection.",
            model="qwen2.5:3b",
            total_duration_seconds=0.5,
        )
        response = self.pipeline.answer_question("What causes fever and cough?")
        self.pipeline.retriever.retrieve_context.assert_called_once()
        self.pipeline.document_retriever.search.assert_called_once()

    def test_response_carries_document_sources(self) -> None:
        """RAGResponse.document_sources must be populated when PDFs are retrieved."""
        self.pipeline.ollama.generate.return_value = LLMGenerationResult(
            response_text="Evidence-based answer.",
            model="qwen2.5:3b",
            total_duration_seconds=0.4,
        )
        response = self.pipeline.answer_question("fever treatment")
        self.assertEqual(len(response.document_sources), 1)
        self.assertEqual(response.document_sources[0].citation, "Clinical_Guidelines.pdf (Page 3)")

    def test_response_carries_dataset_cases(self) -> None:
        """RAGResponse.retrieved_cases must include dataset evidence records."""
        self.pipeline.ollama.generate.return_value = LLMGenerationResult(
            response_text="Answer grounded in dataset.",
            model="qwen2.5:3b",
            total_duration_seconds=0.3,
        )
        response = self.pipeline.answer_question("fever and cough")
        self.assertGreater(len(response.retrieved_cases), 0)

    def test_response_not_offline_fallback_when_llm_online(self) -> None:
        """When Ollama responds successfully, is_offline_fallback must be False."""
        self.pipeline.ollama.generate.return_value = LLMGenerationResult(
            response_text="Answer.",
            model="qwen2.5:3b",
            total_duration_seconds=0.2,
        )
        response = self.pipeline.answer_question("common cold symptoms")
        self.assertFalse(response.is_offline_fallback)
        self.assertEqual(response.llm_model, "qwen2.5:3b")

    # ------------------------------------------------------------------
    # 3. Graceful offline fallback
    # ------------------------------------------------------------------

    def test_offline_fallback_when_ollama_unavailable(self) -> None:
        """When Ollama is offline, pipeline must fall back gracefully and still return evidence."""
        self.pipeline.ollama.generate.side_effect = LocalServiceUnavailable("Connection refused")
        response = self.pipeline.answer_question("fever and cough")
        self.assertTrue(response.is_offline_fallback)
        self.assertIsNone(response.llm_model)
        self.assertIn("Local LLM is offline", response.answer)

    def test_offline_fallback_includes_document_evidence(self) -> None:
        """Offline fallback summary must reference retrieved document sources when available."""
        self.pipeline.ollama.generate.side_effect = LocalServiceUnavailable("Connection refused")
        response = self.pipeline.answer_question("pneumonia treatment")
        self.assertIn("Local Medical Document Evidence", response.answer)

    def test_offline_fallback_when_no_evidence(self) -> None:
        """Offline fallback with empty retrieval must gracefully say no evidence found."""
        self.pipeline.retriever.retrieve_context.return_value = _stub_retrieval_context(empty=True)
        self.pipeline.document_retriever.search.return_value = []
        self.pipeline.ollama.generate.side_effect = LocalServiceUnavailable("Connection refused")
        response = self.pipeline.answer_question("unknown condition xyz")
        self.assertTrue(response.is_offline_fallback)
        self.assertIn("no direct evidence", response.answer.lower())

    # ------------------------------------------------------------------
    # 4. Urgent query handling
    # ------------------------------------------------------------------

    def test_urgent_query_prepends_warning(self) -> None:
        """Queries with urgency signals must prepend the URGENT MEDICAL NOTICE."""
        self.pipeline.ollama.generate.return_value = LLMGenerationResult(
            response_text="Seek emergency care.",
            model="qwen2.5:3b",
            total_duration_seconds=0.2,
        )
        response = self.pipeline.answer_question("I have chest pain and difficulty breathing")
        self.assertTrue(response.urgent_warning)
        self.assertIn("URGENT MEDICAL NOTICE", response.answer)

    # ------------------------------------------------------------------
    # 5. Latency and disclaimer
    # ------------------------------------------------------------------

    def test_response_latency_is_recorded(self) -> None:
        """Total latency must be non-negative."""
        self.pipeline.ollama.generate.return_value = LLMGenerationResult(
            response_text="Answer.", model="qwen2.5:3b", total_duration_seconds=0.1
        )
        response = self.pipeline.answer_question("diabetes treatment")
        self.assertGreaterEqual(response.total_latency_seconds, 0)

    def test_disclaimer_is_always_present(self) -> None:
        """Healthcare disclaimer must be non-empty on every response."""
        self.pipeline.ollama.generate.return_value = LLMGenerationResult(
            response_text="Answer.", model="qwen2.5:3b", total_duration_seconds=0.1
        )
        response = self.pipeline.answer_question("blood pressure")
        self.assertTrue(response.disclaimer.strip())


class DocumentContextBlockTests(unittest.TestCase):
    """Unit tests for the document context block formatter."""

    def test_empty_results_return_empty_string(self) -> None:
        self.assertEqual(_build_document_context_block([]), "")

    def test_non_empty_results_produce_header_and_citation(self) -> None:
        docs = _stub_doc_results()
        block = _build_document_context_block(docs)
        self.assertIn("LOCAL MEDICAL DOCUMENTS", block)
        self.assertIn("Clinical_Guidelines.pdf (Page 3)", block)
        self.assertIn("amoxicillin", block)


class BuildGroundedPromptTests(unittest.TestCase):
    """Unit tests for the updated build_grounded_prompt function."""

    def test_prompt_without_documents_has_no_document_section(self) -> None:
        prompt = build_grounded_prompt("What is diabetes?", "[dataset block]", None)
        self.assertIn("[dataset block]", prompt)
        self.assertNotIn("LOCAL MEDICAL DOCUMENTS", prompt)

    def test_prompt_with_documents_includes_document_block(self) -> None:
        prompt = build_grounded_prompt(
            "What is diabetes?",
            "[dataset block]",
            "--- EVIDENCE FROM LOCAL MEDICAL DOCUMENTS ---\nDoc chunk here.",
        )
        self.assertIn("Doc chunk here", prompt)

    def test_prompt_with_empty_document_block_omits_it(self) -> None:
        prompt = build_grounded_prompt("question", "[dataset]", "   ")
        self.assertNotIn("MEDICAL DOCUMENTS", prompt)


if __name__ == "__main__":
    unittest.main()
