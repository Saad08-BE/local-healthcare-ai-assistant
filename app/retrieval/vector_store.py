"""Local, lightweight, disk-persisted vector store."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import heapq
import json
import math
from pathlib import Path
from typing import Any, Sequence


@dataclass(frozen=True)
class VectorSearchResult:
    """Retrieved evidence document from the vector store."""

    record_id: int | str
    score: float
    text: str
    metadata: dict[str, Any]


class LocalVectorStore:
    """Lightweight, disk-persisted vector store using normalized cosine similarity."""

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension
        self.vectors: list[list[float]] = []
        self.documents: list[dict[str, Any]] = []

    def __len__(self) -> int:
        return len(self.documents)

    def add(
        self,
        embeddings: Sequence[Sequence[float]],
        texts: Sequence[str],
        metadatas: Sequence[dict[str, Any]],
        record_ids: Sequence[int | str] | None = None,
    ) -> None:
        """Add vectors, texts, and metadata to the store."""
        if not (len(embeddings) == len(texts) == len(metadatas)):
            raise ValueError("Embeddings, texts, and metadatas must have identical length.")

        for i, (emb, text, meta) in enumerate(zip(embeddings, texts, metadatas)):
            r_id = record_ids[i] if record_ids is not None else len(self.documents) + 1
            doc_entry = {
                "record_id": r_id,
                "text": text,
                "metadata": dict(meta),
            }
            self.vectors.append(list(emb))
            self.documents.append(doc_entry)

    def search(
        self,
        query_vector: Sequence[float],
        top_k: int = 5,
        min_similarity: float = 0.0,
        filter_fn: Any | None = None,
    ) -> list[VectorSearchResult]:
        """Perform cosine similarity search and return top-k matches."""
        if not self.vectors:
            return []

        # Vector is already normalized; cosine similarity = dot product
        results: list[tuple[float, int]] = []

        for idx, (vec, doc) in enumerate(zip(self.vectors, self.documents)):
            if filter_fn and not filter_fn(doc["metadata"]):
                continue

            # Dot product calculation
            dot = sum(a * b for a, b in zip(query_vector, vec))
            if dot >= min_similarity:
                results.append((dot, idx))

        # Top-k largest scores
        top_matches = heapq.nlargest(top_k, results, key=lambda x: x[0])

        return [
            VectorSearchResult(
                record_id=self.documents[idx]["record_id"],
                score=round(score, 4),
                text=self.documents[idx]["text"],
                metadata=self.documents[idx]["metadata"],
            )
            for score, idx in top_matches
        ]

    def save(self, directory: Path, base_name: str = "healthcare_index") -> dict[str, Path]:
        """Save vector store to disk in JSON / binary format."""
        directory.mkdir(parents=True, exist_ok=True)
        vectors_file = directory / f"{base_name}_vectors.json"
        metadata_file = directory / f"{base_name}_metadata.jsonl"

        with open(vectors_file, mode="w", encoding="utf-8") as f:
            json.dump(
                {
                    "dimension": self.dimension,
                    "count": len(self.vectors),
                    "vectors": self.vectors,
                },
                f,
            )

        with open(metadata_file, mode="w", encoding="utf-8") as f:
            for doc in self.documents:
                f.write(json.dumps(doc, ensure_ascii=False) + "\n")

        return {"vectors_path": vectors_file, "metadata_path": metadata_file}

    @classmethod
    def load(cls, directory: Path, base_name: str = "healthcare_index") -> "LocalVectorStore":
        """Load vector store from disk."""
        vectors_file = directory / f"{base_name}_vectors.json"
        metadata_file = directory / f"{base_name}_metadata.jsonl"

        if not vectors_file.exists() or not metadata_file.exists():
            raise FileNotFoundError(f"Index files missing at {directory}")

        with open(vectors_file, mode="r", encoding="utf-8") as f:
            data = json.load(f)

        store = cls(dimension=data.get("dimension", 384))
        store.vectors = data.get("vectors", [])

        with open(metadata_file, mode="r", encoding="utf-8") as f:
            store.documents = [json.loads(line) for line in f if line.strip()]

        return store
