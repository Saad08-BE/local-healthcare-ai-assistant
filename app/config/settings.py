"""Configuration for the local-only application runtime."""

from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address
import os
from pathlib import Path
from urllib.parse import urlparse


class SettingsError(ValueError):
    """Raised when configuration would violate the local-only design."""


@dataclass(frozen=True)
class LocalPathPolicy:
    """Project-owned locations for healthcare inputs and derived artifacts."""

    project_root: Path
    raw_data_dir: Path
    processed_data_dir: Path
    documents_dir: Path
    vector_store_dir: Path
    models_dir: Path
    logs_dir: Path

    @classmethod
    def for_project(cls, project_root: Path) -> "LocalPathPolicy":
        root = project_root.resolve()
        return cls(
            project_root=root,
            raw_data_dir=root / "data" / "raw",
            processed_data_dir=root / "data" / "processed",
            documents_dir=root / "data" / "documents",
            vector_store_dir=root / "vector_store",
            models_dir=root / "models",
            logs_dir=root / "logs",
        )

    def create_runtime_directories(self) -> None:
        """Create only project-local directories used for derived local data."""
        for path in (
            self.processed_data_dir,
            self.documents_dir,
            self.vector_store_dir,
            self.models_dir,
            self.logs_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


def _is_loopback_host(hostname: str | None) -> bool:
    if not hostname:
        return False
    if hostname.lower() == "localhost":
        return True
    try:
        return ip_address(hostname).is_loopback
    except ValueError:
        return False


def validate_local_endpoint(endpoint: str) -> str:
    """Accept only an HTTP endpoint bound to localhost or loopback IP space."""
    parsed = urlparse(endpoint)
    if parsed.scheme != "http" or not _is_loopback_host(parsed.hostname):
        raise SettingsError(
            "HEALTHCARE_OLLAMA_BASE_URL must be an http:// localhost or loopback endpoint."
        )
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise SettingsError("The local Ollama endpoint must not contain credentials or query data.")
    return endpoint.rstrip("/")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise SettingsError(f"{name} must be an integer.") from exc


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError as exc:
        raise SettingsError(f"{name} must be a number.") from exc


@dataclass(frozen=True)
class AppSettings:
    """Validated runtime settings with safe defaults for an M1 8 GB machine."""

    paths: LocalPathPolicy
    ollama_base_url: str
    llm_model: str
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    top_k: int
    similarity_threshold: float
    host: str
    port: int
    debug: bool

    @classmethod
    def from_environment(cls, project_root: Path | None = None) -> "AppSettings":
        root = project_root or Path(__file__).resolve().parents[2]
        chunk_size = _env_int("HEALTHCARE_CHUNK_SIZE", 600)
        chunk_overlap = _env_int("HEALTHCARE_CHUNK_OVERLAP", 100)
        top_k = _env_int("HEALTHCARE_TOP_K", 5)
        port = _env_int("HEALTHCARE_PORT", 8501)
        threshold = _env_float("HEALTHCARE_SIMILARITY_THRESHOLD", 0.35)
        debug = os.getenv("HEALTHCARE_DEBUG", "false").strip().lower() == "true"
        settings = cls(
            paths=LocalPathPolicy.for_project(root),
            ollama_base_url=validate_local_endpoint(
                os.getenv("HEALTHCARE_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
            ),
            llm_model=os.getenv("HEALTHCARE_LLM_MODEL", "qwen2.5:3b"),
            embedding_model=os.getenv(
                "HEALTHCARE_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
            ),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            top_k=top_k,
            similarity_threshold=threshold,
            host=os.getenv("HEALTHCARE_HOST", "127.0.0.1"),
            port=port,
            debug=debug,
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.chunk_size <= 0:
            raise SettingsError("HEALTHCARE_CHUNK_SIZE must be positive.")
        if not 0 <= self.chunk_overlap < self.chunk_size:
            raise SettingsError("HEALTHCARE_CHUNK_OVERLAP must be at least 0 and smaller than chunk size.")
        if self.top_k <= 0:
            raise SettingsError("HEALTHCARE_TOP_K must be positive.")
        if not 0.0 <= self.similarity_threshold <= 1.0:
            raise SettingsError("HEALTHCARE_SIMILARITY_THRESHOLD must be between 0 and 1.")
        if not _is_loopback_host(self.host):
            raise SettingsError("HEALTHCARE_HOST must be localhost or a loopback address.")
        if not 1 <= self.port <= 65535:
            raise SettingsError("HEALTHCARE_PORT must be between 1 and 65535.")
        if not self.llm_model.strip() or not self.embedding_model.strip():
            raise SettingsError("Model names cannot be empty.")

