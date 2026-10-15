"""Unit tests for local PDF document extraction, chunking, and document retrieval."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from app.embeddings.local_embedding import DeterministicLocalEmbedding
from app.ingestion.pdf_ingestor import (
    DocumentChunk,
    DocumentPage,
    PDFExtractionError,
    PDFIngestor,
)
from app.retrieval.document_retriever import DocumentRetriever


class PDFIngestionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ingestor = PDFIngestor(chunk_size=150, chunk_overlap=30)
        self.embedding = DeterministicLocalEmbedding(dimension=64)

    def test_chunking_and_citation_metadata(self) -> None:
        """Verify page text is split into chunks with sentence awareness and page citations."""
        page = DocumentPage(
            doc_id="testdoc123",
            filename="Diabetes_Care.pdf",
            page_number=2,
            total_pages=5,
            text=(
                "Patients diagnosed with Type 2 Diabetes should maintain balanced nutrition. "
                "Regular exercise helps improve insulin sensitivity significantly. "
                "Blood glucose monitoring should be performed daily as recommended by the physician. "
                "Any sudden spikes in blood sugar must be reported promptly."
            ),
        )

        chunks = self.ingestor.chunk_page(page)
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertEqual(c.filename, "Diabetes_Care.pdf")
            self.assertEqual(c.page_number, 2)
            self.assertEqual(c.doc_id, "testdoc123")
            self.assertEqual(c.citation, "Diabetes_Care.pdf (Page 2)")
            self.assertLessEqual(c.char_count, 180)

    def test_empty_and_corrupted_handling(self) -> None:
        """Verify empty and non-existent files raise appropriate errors."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            empty_file = Path(tmp_dir) / "empty.pdf"
            empty_file.write_bytes(b"")

            with self.assertRaises(PDFExtractionError):
                self.ingestor.extract_pages(empty_file)

            missing_file = Path(tmp_dir) / "non_existent.pdf"
            with self.assertRaises(FileNotFoundError):
                self.ingestor.extract_pages(missing_file)

    def test_document_retriever_indexing_and_search(self) -> None:
        """Test document indexing and semantic retrieval with page citation."""
        chunks = [
            DocumentChunk(
                chunk_id="chunk_1",
                doc_id="doc_a",
                filename="Respiratory_Guide.pdf",
                page_number=1,
                chunk_index=1,
                text="Acute cough and fever can be relieved by warm hydration and steam inhalation.",
                char_count=80,
            ),
            DocumentChunk(
                chunk_id="chunk_2",
                doc_id="doc_a",
                filename="Respiratory_Guide.pdf",
                page_number=2,
                chunk_index=2,
                text="Hypertension treatment involves low-sodium diet and ACE inhibitors.",
                char_count=68,
            ),
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            retriever = DocumentRetriever(embedding_model=self.embedding)
            retriever.index_chunks(chunks=chunks, vector_store_dir=tmp_path)

            results = retriever.search(query="cough and fever hydration", top_k=1)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].filename, "Respiratory_Guide.pdf")
            self.assertEqual(results[0].page_number, 1)
            self.assertEqual(results[0].citation, "Respiratory_Guide.pdf (Page 1)")
            self.assertIn("warm hydration", results[0].text)


if __name__ == "__main__":
    unittest.main()
