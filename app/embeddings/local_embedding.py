"""Local embedding adapters for the privacy-based healthcare RAG system."""

from __future__ import annotations

from abc import ABC, abstractmethod
import hashlib
import math
import re
from typing import Sequence


class BaseEmbeddingModel(ABC):
    """Abstract interface for local embedding models."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the vector dimension."""
        ...

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """Generate a normalized embedding vector for a single text string."""
        ...

    @abstractmethod
    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate normalized embedding vectors for a batch of text strings."""
        ...


class SentenceTransformerEmbedding(BaseEmbeddingModel):
    """Local SentenceTransformer embedding model (e.g. all-MiniLM-L6-v2)."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model = None
        self._dimension = 384

    def _ensure_loaded(self) -> None:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
                self._dimension = self._model.get_sentence_embedding_dimension() or 384
            except ImportError as exc:
                raise RuntimeError(
                    "sentence-transformers is not installed. Run 'pip install sentence-transformers' "
                    "or use DeterministicLocalEmbedding for test environments."
                ) from exc

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_text(self, text: str) -> list[float]:
        self._ensure_loaded()
        vec = self._model.encode(text, normalize_embeddings=True, show_progress_bar=False)
        return vec.tolist() if hasattr(vec, "tolist") else list(vec)

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        self._ensure_loaded()
        vecs = self._model.encode(list(texts), normalize_embeddings=True, show_progress_bar=False)
        return vecs.tolist() if hasattr(vecs, "tolist") else [list(v) for v in vecs]


class DeterministicLocalEmbedding(BaseEmbeddingModel):
    """A zero-dependency, local feature-hash embedding model for tests and lightweight CPU operation.

    Computes normalized 384-dimensional dense vectors using character and token n-gram hashing.
    Runs 100% offline with zero dependencies and deterministic outputs.
    """

    def __init__(self, dimension: int = 384) -> None:
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def _hash_token(self, token: str) -> int:
        md5 = hashlib.md5(token.encode("utf-8")).hexdigest()
        return int(md5, 16) % self._dimension

    def embed_text(self, text: str) -> list[float]:
        vec = [0.0] * self._dimension
        tokens = re.findall(r"\b\w+\b", text.lower())
        if not tokens:
            return vec

        # Bag of words + bi-grams hashing
        for i, token in enumerate(tokens):
            idx = self._hash_token(token)
            vec[idx] += 1.0
            if i + 1 < len(tokens):
                bigram = f"{token}_{tokens[i+1]}"
                b_idx = self._hash_token(bigram)
                vec[b_idx] += 1.5

        # L2 Normalization
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        return [self.embed_text(t) for t in texts]


def get_embedding_model(model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> BaseEmbeddingModel:
    """Return configured embedding model or fallback to deterministic embedding if library missing."""
    try:
        import sentence_transformers  # noqa: F401

        return SentenceTransformerEmbedding(model_name=model_name)
    except ImportError:
        return DeterministicLocalEmbedding(dimension=384)
