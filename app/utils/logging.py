"""Privacy-preserving operational logger.

Guarantees:
- Never logs raw patient questions, health data, or document contents.
- Logs strictly operational telemetry: query lengths, retrieval counts, latencies, model names, and system errors.
"""

from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(log_directory: Path, debug: bool = False) -> logging.Logger:
    """Configure a local log with event metadata only, never prompts or document text."""
    log_directory.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("healthcare_intelligence")
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    log_file = (log_directory / "operational.log").resolve()
    # Check if a FileHandler targeting this specific log_file already exists
    has_target_handler = any(
        isinstance(h, logging.FileHandler) and Path(h.baseFilename).resolve() == log_file
        for h in logger.handlers
    )
    if not has_target_handler:
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(handler)

    return logger


def log_rag_query(
    logger: logging.Logger,
    query_length: int,
    retrieved_case_count: int,
    retrieved_doc_count: int,
    latency_seconds: float,
    model: str | None,
    is_offline: bool,
    urgent: bool,
) -> None:
    """Log privacy-safe operational telemetry for a RAG query."""
    logger.info(
        f"Query processed | chars={query_length} | cases_retrieved={retrieved_case_count} | "
        f"docs_retrieved={retrieved_doc_count} | latency={latency_seconds:.3f}s | "
        f"model={model or 'offline'} | offline_fallback={is_offline} | urgent_flag={urgent}"
    )


def log_security_event(logger: logging.Logger, event_type: str, detail: str) -> None:
    """Log safety blocks or security events without revealing private inputs."""
    logger.warning(f"Security event: {event_type} | detail={detail}")
