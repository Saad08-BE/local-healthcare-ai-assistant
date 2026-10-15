"""End-to-end local Healthcare RAG pipeline orchestrating safety, retrieval, and LLM generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import time
from typing import Any

from app.config.settings import AppSettings
from app.llm.ollama_client import LLMGenerationResult, LocalServiceUnavailable, ModelUnavailableError, OllamaClient
from app.llm.prompts import HEALTHCARE_SYSTEM_PROMPT, build_grounded_prompt
from app.retrieval.dataset_retriever import DatasetRetriever, RetrievalContext
from app.retrieval.document_retriever import DocumentRetriever, DocumentSearchResult
from app.retrieval.vector_store import VectorSearchResult
from app.safety import SafetyDecision, healthcare_disclaimer, validate_question
from app.utils.logging import configure_logging, log_rag_query, log_security_event


@dataclass(frozen=True)
class RAGResponse:
    """Complete response object returned to the user or UI."""

    question: str
    answer: str
    retrieved_cases: list[VectorSearchResult]
    cohort_statistics: dict[str, Any]
    document_sources: list[DocumentSearchResult]
    disclaimer: str
    llm_model: str | None
    is_offline_fallback: bool
    urgent_warning: bool
    total_latency_seconds: float
    safety_decision: SafetyDecision


def _build_document_context_block(doc_results: list[DocumentSearchResult]) -> str:
    """Format document search results into a context block for the LLM prompt."""
    if not doc_results:
        return ""

    lines = ["--- EVIDENCE FROM LOCAL MEDICAL DOCUMENTS ---"]
    for idx, doc in enumerate(doc_results, 1):
        lines.append(
            f"\n[Document {idx}] Citation: {doc.citation} (Relevance: {doc.score:.2f}):\n{doc.text}"
        )
    lines.append("\n--- END OF DOCUMENT EVIDENCE ---")
    return "\n".join(lines)


class HealthcareRAGPipeline:
    """Orchestrates safety checks, hybrid retrieval (dataset + documents), and local LLM generation."""

    def __init__(
        self,
        retriever: DatasetRetriever,
        document_retriever: DocumentRetriever,
        ollama_client: OllamaClient,
        settings: AppSettings,
    ) -> None:
        self.retriever = retriever
        self.document_retriever = document_retriever
        self.ollama = ollama_client
        self.settings = settings
        self.logger = configure_logging(settings.paths.logs_dir, debug=settings.debug)

    @classmethod
    def initialize(cls, settings: AppSettings | None = None) -> "HealthcareRAGPipeline":
        """Factory initializing pipeline components from project settings and local disk."""
        app_settings = settings or AppSettings.from_environment()
        app_settings.paths.create_runtime_directories()

        retriever = DatasetRetriever.from_local_files(
            vector_store_dir=app_settings.paths.vector_store_dir,
            processed_data_dir=app_settings.paths.processed_data_dir,
        )
        document_retriever = DocumentRetriever.from_local_files(
            vector_store_dir=app_settings.paths.vector_store_dir,
        )
        ollama = OllamaClient(
            base_url=app_settings.ollama_base_url,
            timeout_seconds=60.0,
        )
        return cls(
            retriever=retriever,
            document_retriever=document_retriever,
            ollama_client=ollama,
            settings=app_settings,
        )

    def answer_question(self, question: str, model_override: str | None = None) -> RAGResponse:
        """Run full unified RAG pipeline for a user question.

        Evidence sources, in priority order:
          1. Safety triage (blocks disallowed queries immediately).
          2. Dataset: semantic clinical cases + ChatDoctor consultations + cohort statistics.
          3. Local documents: semantic PDF chunk search with page-level citations.
          4. Unified LLM prompt grounded on all available evidence.
          5. Graceful offline fallback when Ollama is unavailable.
        """
        start_time = time.time()
        effective_model = (model_override or self.settings.llm_model).strip()

        # --- 1. Safety Triage ---
        safety = validate_question(question)
        if not safety.allowed:
            log_security_event(self.logger, "SAFETY_BLOCK", f"allowed=False urgent={safety.urgent}")
            return RAGResponse(
                question=question,
                answer=safety.user_message,
                retrieved_cases=[],
                cohort_statistics={},
                document_sources=[],
                disclaimer=healthcare_disclaimer(),
                llm_model=None,
                is_offline_fallback=False,
                urgent_warning=False,
                total_latency_seconds=round(time.time() - start_time, 3),
                safety_decision=safety,
            )

        # --- 2. Dataset Hybrid Retrieval ---
        context: RetrievalContext = self.retriever.retrieve_context(
            query=question,
            top_k=self.settings.top_k,
            min_similarity=self.settings.similarity_threshold,
        )

        # --- 3. Document Semantic Retrieval ---
        doc_results: list[DocumentSearchResult] = self.document_retriever.search(
            query=question,
            top_k=4,
            min_similarity=self.settings.similarity_threshold,
        )
        document_context_block = _build_document_context_block(doc_results)

        # --- 4. Unified Prompt Construction ---
        grounded_prompt = build_grounded_prompt(
            question=question,
            evidence_context_block=context.formatted_context_block,
            document_context_block=document_context_block if doc_results else None,
        )

        # --- 5. Local LLM Generation (with graceful offline fallback) ---
        answer_text = ""
        used_model = None
        is_fallback = False

        try:
            llm_result: LLMGenerationResult = self.ollama.generate(
                prompt=grounded_prompt,
                model=effective_model,
                system=HEALTHCARE_SYSTEM_PROMPT,
                temperature=0.2,
            )
            answer_text = llm_result.response_text
            used_model = llm_result.model
        except (LocalServiceUnavailable, ModelUnavailableError) as exc:
            # Graceful degradation: synthesize retrieved evidence directly without LLM
            is_fallback = True
            used_model = None
            answer_text = self._build_offline_evidence_summary(question, context, doc_results, str(exc))

        # --- 6. Attach Disclaimers & Urgent Warning ---
        disclaimer = healthcare_disclaimer()
        if safety.urgent:
            answer_text = (
                "⚠️ **URGENT MEDICAL NOTICE**: Your question mentions acute or potentially serious symptoms. "
                "Please seek immediate medical evaluation or emergency care.\n\n"
                + answer_text
            )

        total_time = round(time.time() - start_time, 3)

        log_rag_query(
            logger=self.logger,
            query_length=len(question),
            retrieved_case_count=len(context.evidence_records),
            retrieved_doc_count=len(doc_results),
            latency_seconds=total_time,
            model=used_model,
            is_offline=is_fallback,
            urgent=safety.urgent,
        )

        return RAGResponse(
            question=question,
            answer=answer_text,
            retrieved_cases=context.evidence_records,
            cohort_statistics=context.cohort_statistics,
            document_sources=doc_results,
            disclaimer=disclaimer,
            llm_model=used_model,
            is_offline_fallback=is_fallback,
            urgent_warning=safety.urgent,
            total_latency_seconds=total_time,
            safety_decision=safety,
        )

    def _build_offline_evidence_summary(
        self,
        question: str,
        context: RetrievalContext,
        doc_results: list[DocumentSearchResult],
        offline_reason: str,
    ) -> str:
        """Construct a structured evidence summary when the local LLM is offline."""
        lines = [
            f"ℹ️ *Local LLM is offline ({offline_reason}). Displaying retrieved evidence directly:*\n",
            "### Retrieved Local Healthcare Evidence\n",
        ]

        if context.cohort_statistics.get("symptom_evidence"):
            lines.append("**Cohort Statistical Associations**:")
            for symp, diags in context.cohort_statistics["symptom_evidence"].items():
                diag_list = ", ".join(f"**{d['diagnosis']}** ({d['percentage']}%)" for d in diags)
                lines.append(f"- Symptoms *'{symp}'* correlate with: {diag_list}")
            lines.append("")

        if context.cohort_statistics.get("diagnosis_evidence"):
            lines.append("**Treatment & Outcome Trends**:")
            for diag, info in context.cohort_statistics["diagnosis_evidence"].items():
                treats = ", ".join(f"{t['treatment']} ({t['percentage']}%)" for t in info["common_treatments"])
                outcomes = ", ".join(f"{o['outcome']} ({o['percentage']}%)" for o in info["outcomes"])
                lines.append(f"- **{diag}**: Common Treatments: [{treats}]; Outcomes: [{outcomes}]")
            lines.append("")

        if context.evidence_records:
            lines.append("**Matching De-Identified Cases**:")
            for idx, case in enumerate(context.evidence_records[:3], 1):
                lines.append(f"{idx}. {case.text}")
            lines.append("")

        if doc_results:
            lines.append("**Local Medical Document Evidence**:")
            for idx, doc in enumerate(doc_results[:3], 1):
                lines.append(f"{idx}. [{doc.citation}]: {doc.text[:300]}...")
            lines.append("")

        if not context.evidence_records and not context.cohort_statistics and not doc_results:
            lines.append("No direct evidence met the similarity threshold.")

        return "\n".join(lines)
