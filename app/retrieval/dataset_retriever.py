"""Hybrid retrieval engine combining semantic vector search and structured cohort statistics."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Callable

from app.embeddings.local_embedding import BaseEmbeddingModel, get_embedding_model
from app.retrieval.vector_store import LocalVectorStore, VectorSearchResult


@dataclass(frozen=True)
class RetrievalContext:
    """Assembled evidence context for downstream prompt grounding."""

    query: str
    evidence_records: list[VectorSearchResult]
    cohort_statistics: dict[str, Any]
    formatted_context_block: str


class DatasetRetriever:
    """Retrieval manager supporting vector similarity over clinical cases, doctor consultations, and cohort lookup."""

    def __init__(
        self,
        vector_store: LocalVectorStore | None = None,
        chatdoctor_store: LocalVectorStore | None = None,
        embedding_model: BaseEmbeddingModel | None = None,
        cohort_aggregates: dict[str, Any] | None = None,
    ) -> None:
        self.vector_store = vector_store
        self.chatdoctor_store = chatdoctor_store
        self.embedding_model = embedding_model or get_embedding_model()
        self.cohort_aggregates = cohort_aggregates or {}

    @classmethod
    def from_local_files(
        cls,
        vector_store_dir: Path,
        processed_data_dir: Path,
        embedding_model: BaseEmbeddingModel | None = None,
    ) -> "DatasetRetriever":
        """Load available vector stores and cohort statistics from local project paths."""
        emb = embedding_model or get_embedding_model()

        # Load primary healthcare index if present
        store = None
        if (vector_store_dir / "healthcare_index_vectors.json").exists():
            try:
                store = LocalVectorStore.load(vector_store_dir, base_name="healthcare_index")
            except Exception:
                pass

        # Load ChatDoctor consultations index if present
        chatdoctor_store = None
        if (vector_store_dir / "chatdoctor_index_vectors.json").exists():
            try:
                chatdoctor_store = LocalVectorStore.load(vector_store_dir, base_name="chatdoctor_index")
            except Exception:
                pass

        cohort_file = processed_data_dir / "cohort_aggregates.json"
        aggregates = {}
        if cohort_file.exists():
            with open(cohort_file, mode="r", encoding="utf-8") as f:
                aggregates = json.load(f)

        return cls(
            vector_store=store,
            chatdoctor_store=chatdoctor_store,
            embedding_model=emb,
            cohort_aggregates=aggregates,
        )

    def semantic_search(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.20,
        filter_fn: Callable[[dict[str, Any]], bool] | None = None,
    ) -> list[VectorSearchResult]:
        """Perform semantic similarity search using local embeddings."""
        if not query.strip():
            return []
        query_vector = self.embedding_model.embed_text(query)
        results = []
        if self.vector_store:
            results.extend(
                self.vector_store.search(
                    query_vector=query_vector,
                    top_k=top_k,
                    min_similarity=min_similarity,
                    filter_fn=filter_fn,
                )
            )
        return results

    def search_doctor_consultations(
        self,
        query: str,
        top_k: int = 3,
        min_similarity: float = 0.15,
    ) -> list[VectorSearchResult]:
        """Search ChatDoctor consultation records for clinical guidance."""
        if not self.chatdoctor_store or not query.strip():
            return []
        query_vector = self.embedding_model.embed_text(query)
        return self.chatdoctor_store.search(
            query_vector=query_vector,
            top_k=top_k,
            min_similarity=min_similarity,
        )

    def structured_search(
        self,
        filters: dict[str, Any],
        limit: int = 5,
    ) -> list[VectorSearchResult]:
        """Filter dataset records by exact structured metadata criteria."""
        if not self.vector_store:
            return []
        def match_filter(meta: dict[str, Any]) -> bool:
            for k, v in filters.items():
                if k not in meta:
                    return False
                if isinstance(v, str) and isinstance(meta[k], str):
                    if v.lower() not in meta[k].lower():
                        return False
                elif meta[k] != v:
                    return False
            return True

        matches: list[VectorSearchResult] = []
        for doc in self.vector_store.documents:
            if match_filter(doc["metadata"]):
                matches.append(
                    VectorSearchResult(
                        record_id=doc["record_id"],
                        score=1.0,
                        text=doc["text"],
                        metadata=doc["metadata"],
                    )
                )
                if len(matches) >= limit:
                    break
        return matches

    def get_cohort_statistics_for_query(self, query: str) -> dict[str, Any]:
        """Extract matching aggregated statistics from precomputed cohort summaries."""
        if not self.cohort_aggregates:
            return {}

        query_lower = query.lower()
        matched_stats: dict[str, Any] = {}

        # Check symptom associations
        symptom_assocs = self.cohort_aggregates.get("symptom_to_diagnosis_associations", {})
        matched_symptoms = {}
        for symptom_phrase, diag_list in symptom_assocs.items():
            words = [w.strip() for w in symptom_phrase.lower().split(",")]
            if any(w in query_lower for w in words if len(w) > 3):
                matched_symptoms[symptom_phrase] = diag_list[:3]

        if matched_symptoms:
            matched_stats["symptom_evidence"] = matched_symptoms

        # Check diagnosis associations (treatments and outcomes)
        diag_treatments = self.cohort_aggregates.get("diagnosis_to_treatment_associations", {})
        diag_outcomes = self.cohort_aggregates.get("diagnosis_to_outcome_associations", {})
        diag_averages = self.cohort_aggregates.get("diagnosis_measurement_averages", {})

        matched_diagnoses = {}
        for diag, treat_list in diag_treatments.items():
            if diag.lower() in query_lower:
                matched_diagnoses[diag] = {
                    "common_treatments": treat_list[:3],
                    "outcomes": diag_outcomes.get(diag, [])[:3],
                    "measurements": diag_averages.get(diag, {}),
                }

        if matched_diagnoses:
            matched_stats["diagnosis_evidence"] = matched_diagnoses

        return matched_stats

    def retrieve_context(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.20,
        structured_filters: dict[str, Any] | None = None,
    ) -> RetrievalContext:
        """Assemble a complete hybrid retrieval context for the user query."""
        filter_fn = None
        if structured_filters:
            def filter_fn(meta: dict[str, Any]) -> bool:
                for k, v in structured_filters.items():
                    if k not in meta or meta[k] != v:
                        return False
                return True

        evidence_records = self.semantic_search(
            query=query,
            top_k=top_k,
            min_similarity=min_similarity,
            filter_fn=filter_fn,
        )

        doctor_consultations = self.search_doctor_consultations(
            query=query,
            top_k=3,
            min_similarity=0.15,
        )

        cohort_stats = self.get_cohort_statistics_for_query(query)

        # Build clean formatted context block for LLM prompt
        context_lines = ["--- EVIDENCE FROM LOCAL HEALTHCARE KNOWLEDGE BASE ---"]

        if doctor_consultations:
            context_lines.append("\n[Verified Doctor Consultations & Clinical Guidance]:")
            for idx, c in enumerate(doctor_consultations, 1):
                context_lines.append(f"Consultation {idx} (Relevance: {c.score:.2f}):")
                context_lines.append(f"{c.text}\n")

        if cohort_stats.get("symptom_evidence"):
            context_lines.append("\n[Cohort Statistical Associations]:")
            for symp, diags in cohort_stats["symptom_evidence"].items():
                diag_str = ", ".join(f"{d['diagnosis']} ({d['percentage']}%)" for d in diags)
                context_lines.append(f"- Symptoms '{symp}' frequently associated with: {diag_str}")

        if cohort_stats.get("diagnosis_evidence"):
            context_lines.append("\n[Condition Treatment & Outcome Statistics]:")
            for diag, info in cohort_stats["diagnosis_evidence"].items():
                treat_str = ", ".join(f"{t['treatment']} ({t['percentage']}%)" for t in info["common_treatments"])
                out_str = ", ".join(f"{o['outcome']} ({o['percentage']}%)" for o in info["outcomes"])
                context_lines.append(f"- {diag}: Common Treatments: [{treat_str}], Typical Outcomes: [{out_str}]")

        if evidence_records:
            context_lines.append("\n[Representative Clinical Records (De-Identified)]:")
            for idx, rec in enumerate(evidence_records, 1):
                context_lines.append(f"Case {idx} (Similarity: {rec.score:.2f}): {rec.text}")

        if not doctor_consultations and not cohort_stats and not evidence_records:
            context_lines.append("\n[Evidence]: No high-confidence matching clinical records or consultations.")

        context_lines.append("\n--- END OF EVIDENCE ---")
        formatted_block = "\n".join(context_lines)

        all_evidence = doctor_consultations + evidence_records

        return RetrievalContext(
            query=query,
            evidence_records=all_evidence,
            cohort_statistics=cohort_stats,
            formatted_context_block=formatted_block,
        )
