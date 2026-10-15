"""Unit tests for local LLM adapters, medical grounding prompts, and the RAG pipeline."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.config.settings import AppSettings
from app.llm.ollama_client import LLMGenerationResult, LocalServiceUnavailable, OllamaClient
from app.llm.prompts import HEALTHCARE_SYSTEM_PROMPT, build_grounded_prompt
from app.llm.rag_pipeline import HealthcareRAGPipeline
from app.retrieval.dataset_retriever import DatasetRetriever, RetrievalContext
from app.retrieval.document_retriever import DocumentRetriever
from app.retrieval.vector_store import VectorSearchResult


class LLMTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = AppSettings.from_environment()
        # Shared no-op document retriever stub used in all pipeline tests
        self._mock_doc_retriever = MagicMock(spec=DocumentRetriever)
        self._mock_doc_retriever.search.return_value = []

    def test_grounded_prompt_construction(self) -> None:
        """Verify prompt template properly encapsulates evidence and instructions."""
        evidence = "--- EVIDENCE ---\n- Fever correlates to Dengue (60%)"
        question = "What causes high fever?"
        prompt = build_grounded_prompt(question, evidence)

        self.assertIn("--- EVIDENCE ---", prompt)
        self.assertIn("What causes high fever?", prompt)
        self.assertIn("INSTRUCTIONS FOR YOUR RESPONSE", prompt)
        self.assertIn("STRICT EVIDENCE GROUNDING", HEALTHCARE_SYSTEM_PROMPT)

    def test_ollama_client_offline_detection(self) -> None:
        """Verify OllamaClient detects offline daemon on unused loopback port."""
        client = OllamaClient(base_url="http://127.0.0.1:59999", timeout_seconds=0.5)
        self.assertFalse(client.is_online())
        with self.assertRaises(LocalServiceUnavailable):
            client.list_models()

    def test_pipeline_safety_rejection(self) -> None:
        """Verify pipeline rejects patient ID lookups immediately without calling LLM."""
        mock_retriever = MagicMock(spec=DatasetRetriever)
        mock_ollama = MagicMock(spec=OllamaClient)
        pipeline = HealthcareRAGPipeline(
            mock_retriever, self._mock_doc_retriever, mock_ollama, self.settings
        )

        response = pipeline.answer_question("Find patient details for ID 21D74F65-E20")
        self.assertFalse(response.safety_decision.allowed)
        self.assertIn("Patient-record search is not available", response.answer)
        mock_retriever.retrieve_context.assert_not_called()
        mock_ollama.generate.assert_not_called()

    def test_pipeline_offline_fallback_execution(self) -> None:
        """Verify pipeline gracefully provides retrieved evidence when Ollama is offline."""
        mock_retriever = MagicMock(spec=DatasetRetriever)
        mock_retriever.retrieve_context.return_value = RetrievalContext(
            query="high fever and joint pain",
            evidence_records=[
                VectorSearchResult(
                    record_id=1,
                    score=0.85,
                    text="Patient Age 30 with Malaria symptoms: high fever, joint pain.",
                    metadata={"primary_diagnosis": "Malaria"},
                )
            ],
            cohort_statistics={
                "symptom_evidence": {
                    "high fever, joint pain": [{"diagnosis": "Malaria", "percentage": 70.0}]
                }
            },
            formatted_context_block="Evidence block",
        )

        mock_ollama = MagicMock(spec=OllamaClient)
        mock_ollama.generate.side_effect = LocalServiceUnavailable("Ollama offline")

        pipeline = HealthcareRAGPipeline(
            mock_retriever, self._mock_doc_retriever, mock_ollama, self.settings
        )
        response = pipeline.answer_question("What causes high fever and joint pain?")

        self.assertTrue(response.is_offline_fallback)
        self.assertIn("Local LLM is offline", response.answer)
        self.assertIn("Malaria", response.answer)
        self.assertEqual(len(response.retrieved_cases), 1)

    def test_pipeline_urgent_symptom_warning(self) -> None:
        """Verify pipeline attaches urgent medical warning when emergency terms are present."""
        mock_retriever = MagicMock(spec=DatasetRetriever)
        mock_retriever.retrieve_context.return_value = RetrievalContext(
            query="severe chest pain and shortness of breath",
            evidence_records=[],
            cohort_statistics={},
            formatted_context_block="Empty",
        )
        mock_ollama = MagicMock(spec=OllamaClient)
        mock_ollama.generate.return_value = LLMGenerationResult(
            response_text="Based on evidence, chest pain relates to cardiovascular conditions.",
            model="qwen2.5:3b",
            total_duration_seconds=1.2,
        )

        pipeline = HealthcareRAGPipeline(
            mock_retriever, self._mock_doc_retriever, mock_ollama, self.settings
        )
        response = pipeline.answer_question("I have severe chest pain and shortness of breath")

        self.assertTrue(response.urgent_warning)
        self.assertIn("URGENT MEDICAL NOTICE", response.answer)


if __name__ == "__main__":
    unittest.main()
