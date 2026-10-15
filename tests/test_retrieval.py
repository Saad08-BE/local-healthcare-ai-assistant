"""Unit tests for embedding models, vector store, and hybrid dataset retriever."""

from __future__ import annotations

import math
from pathlib import Path
import tempfile
import unittest

from app.embeddings.local_embedding import DeterministicLocalEmbedding
from app.retrieval.dataset_retriever import DatasetRetriever
from app.retrieval.vector_store import LocalVectorStore, VectorSearchResult


class RetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.embedding = DeterministicLocalEmbedding(dimension=64)
        self.sample_docs = [
            {
                "text": "Patient Age 45 with Type 2 Diabetes symptoms: frequent urination, fatigue.",
                "meta": {"age": 45, "primary_diagnosis": "Type 2 Diabetes", "symptoms": "frequent urination"},
            },
            {
                "text": "Patient Age 60 with Hypertension symptoms: high BP, headache.",
                "meta": {"age": 60, "primary_diagnosis": "Hypertension", "symptoms": "high BP"},
            },
            {
                "text": "Patient Age 30 with Malaria symptoms: high fever, joint pain.",
                "meta": {"age": 30, "primary_diagnosis": "Malaria", "symptoms": "high fever"},
            },
        ]
        self.cohort_aggregates = {
            "symptom_to_diagnosis_associations": {
                "frequent urination, blurred vision": [
                    {"diagnosis": "Type 2 Diabetes", "count": 280, "percentage": 75.0},
                    {"diagnosis": "Hypertension", "count": 50, "percentage": 13.4},
                ]
            },
            "diagnosis_to_treatment_associations": {
                "Type 2 Diabetes": [
                    {"treatment": "Insulin Therapy", "count": 120, "percentage": 42.8},
                    {"treatment": "Medication", "count": 90, "percentage": 32.1},
                ]
            },
            "diagnosis_to_outcome_associations": {
                "Type 2 Diabetes": [
                    {"outcome": "Improved", "count": 150, "percentage": 53.5}
                ]
            },
            "diagnosis_measurement_averages": {
                "Type 2 Diabetes": {
                    "mean_blood_glucose": 165.2,
                    "mean_hba1c": 7.9,
                    "mean_cholesterol": 215.0,
                    "mean_bmi": 26.4,
                }
            },
        }

    def test_embedding_normalization(self) -> None:
        """Verify embeddings are L2 normalized to unit length."""
        text = "Test clinical symptoms of fever and cough"
        vec = self.embedding.embed_text(text)
        self.assertEqual(len(vec), 64)
        norm = math.sqrt(sum(x * x for x in vec))
        self.assertAlmostEqual(norm, 1.0, places=5)

    def test_vector_store_search_and_persistence(self) -> None:
        """Test adding items, searching, saving, and loading the vector store."""
        store = LocalVectorStore(dimension=64)
        texts = [d["text"] for d in self.sample_docs]
        metas = [d["meta"] for d in self.sample_docs]
        embs = self.embedding.embed_batch(texts)

        store.add(embeddings=embs, texts=texts, metadatas=metas)
        self.assertEqual(len(store), 3)

        # Query search for diabetes
        query_vec = self.embedding.embed_text("Type 2 Diabetes urination")
        results = store.search(query_vector=query_vec, top_k=2)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].metadata["primary_diagnosis"], "Type 2 Diabetes")

        # Save and reload
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            store.save(tmp_path, base_name="test_index")

            loaded_store = LocalVectorStore.load(tmp_path, base_name="test_index")
            self.assertEqual(len(loaded_store), 3)
            loaded_results = loaded_store.search(query_vector=query_vec, top_k=1)
            self.assertEqual(loaded_results[0].metadata["primary_diagnosis"], "Type 2 Diabetes")

    def test_dataset_retriever_hybrid_context(self) -> None:
        """Test DatasetRetriever assembling semantic and cohort evidence."""
        store = LocalVectorStore(dimension=64)
        texts = [d["text"] for d in self.sample_docs]
        metas = [d["meta"] for d in self.sample_docs]
        embs = self.embedding.embed_batch(texts)
        store.add(embeddings=embs, texts=texts, metadatas=metas)

        retriever = DatasetRetriever(
            vector_store=store,
            embedding_model=self.embedding,
            cohort_aggregates=self.cohort_aggregates,
        )

        # Test structured search
        structured = retriever.structured_search(filters={"primary_diagnosis": "Hypertension"})
        self.assertEqual(len(structured), 1)
        self.assertEqual(structured[0].metadata["age"], 60)

        # Test hybrid retrieve_context
        ctx = retriever.retrieve_context(query="frequent urination and blurred vision Type 2 Diabetes", top_k=2)
        self.assertIn("Type 2 Diabetes", ctx.formatted_context_block)
        self.assertIn("EVIDENCE FROM LOCAL HEALTHCARE KNOWLEDGE BASE", ctx.formatted_context_block)
        self.assertIn("Cohort Statistical Associations", ctx.formatted_context_block)
        self.assertIn("Insulin Therapy", ctx.formatted_context_block)


if __name__ == "__main__":
    unittest.main()
