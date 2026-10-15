"""Document retriever for local medical reports and clinical guideline PDFs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from app.embeddings.local_embedding import BaseEmbeddingModel, get_embedding_model
from app.ingestion.pdf_ingestor import DocumentChunk
from app.retrieval.vector_store import LocalVectorStore, VectorSearchResult


@dataclass(frozen=True)
class DocumentSearchResult:
    """A retrieved medical document chunk with page-level citation."""

    chunk_id: str
    doc_id: str
    filename: str
    page_number: int
    score: float
    text: str
    citation: str


class DocumentRetriever:
    """Manages indexing and semantic search over user-uploaded PDF healthcare documents."""

    def __init__(
        self,
        vector_store: LocalVectorStore | None = None,
        embedding_model: BaseEmbeddingModel | None = None,
    ) -> None:
        self.embedding_model = embedding_model or get_embedding_model()
        self.vector_store = vector_store

    @classmethod
    def from_local_files(
        cls,
        vector_store_dir: Path,
        embedding_model: BaseEmbeddingModel | None = None,
    ) -> "DocumentRetriever":
        """Load document vector store from disk if present."""
        emb = embedding_model or get_embedding_model()
        store = None
        vectors_file = vector_store_dir / "document_index_vectors.json"
        if vectors_file.exists():
            try:
                store = LocalVectorStore.load(vector_store_dir, base_name="document_index")
            except Exception:
                store = None
        return cls(vector_store=store, embedding_model=emb)

    def index_chunks(
        self,
        chunks: Sequence[DocumentChunk],
        vector_store_dir: Path,
        batch_size: int = 128,
    ) -> dict[str, Path]:
        """Generate embeddings for document chunks and save the vector store."""
        if not chunks:
            raise ValueError("No document chunks provided for indexing.")

        vector_store = LocalVectorStore(dimension=self.embedding_model.dimension)
        texts = [c.text for c in chunks]
        metas = [
            {
                "chunk_id": c.chunk_id,
                "doc_id": c.doc_id,
                "filename": c.filename,
                "page_number": c.page_number,
                "chunk_index": c.chunk_index,
                "citation": c.citation,
            }
            for c in chunks
        ]
        ids = [c.chunk_id for c in chunks]

        # Batch embedding
        for i in range(0, len(texts), batch_size):
            b_texts = texts[i : i + batch_size]
            b_metas = metas[i : i + batch_size]
            b_ids = ids[i : i + batch_size]
            b_embeddings = self.embedding_model.embed_batch(b_texts)

            vector_store.add(
                embeddings=b_embeddings,
                texts=b_texts,
                metadatas=b_metas,
                record_ids=b_ids,
            )

        self.vector_store = vector_store
        return vector_store.save(vector_store_dir, base_name="document_index")

    def search(
        self,
        query: str,
        top_k: int = 4,
        min_similarity: float = 0.20,
    ) -> list[DocumentSearchResult]:
        """Search indexed document chunks by semantic cosine similarity."""
        if not self.vector_store or not query.strip():
            return []

        query_vec = self.embedding_model.embed_text(query)
        raw_results = self.vector_store.search(
            query_vector=query_vec,
            top_k=top_k,
            min_similarity=min_similarity,
        )

        return [
            DocumentSearchResult(
                chunk_id=str(r.record_id),
                doc_id=r.metadata.get("doc_id", "doc"),
                filename=r.metadata.get("filename", "document.pdf"),
                page_number=r.metadata.get("page_number", 1),
                score=r.score,
                text=r.text,
                citation=r.metadata.get("citation", f"{r.metadata.get('filename')} (Page {r.metadata.get('page_number')})"),
            )
            for r in raw_results
        ]
