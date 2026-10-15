"""UI components for system status and live metrics."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import streamlit as st

from app.config.settings import AppSettings
from app.llm.ollama_client import OllamaClient


def render_sidebar_status(st_module, settings: AppSettings) -> dict[str, bool | str | int]:
    """Render the sidebar status panel with live hardware and service checks."""
    client = OllamaClient(base_url=settings.ollama_base_url, timeout_seconds=1.5)
    ollama_online = client.is_online()
    models_available = []
    model_ready = False

    if ollama_online:
        try:
            models_available = client.list_models()
            model_ready = client.is_model_available(settings.llm_model)
        except Exception:
            pass

    # Count local documents
    doc_dir = settings.paths.documents_dir
    pdf_count = len(list(doc_dir.glob("*.pdf")) + list(doc_dir.glob("*.PDF"))) if doc_dir.exists() else 0

    st_module.sidebar.title("🩺 System Status")
    st_module.sidebar.caption("100% Local Apple Silicon Architecture")

    # Status Indicators
    if ollama_online:
        st_module.sidebar.success("🟢 Local Ollama: Online")
    else:
        st_module.sidebar.warning("🟡 Local Ollama: Offline (Evidence fallback active)")

    if model_ready:
        st_module.sidebar.success(f"🟢 Model `{settings.llm_model}`: Ready")
    elif ollama_online:
        st_module.sidebar.warning(f"🟡 Model `{settings.llm_model}`: Not found (Run `ollama pull {settings.llm_model}`)")
    else:
        st_module.sidebar.info(f"⚪ Configured Model: `{settings.llm_model}`")

    st_module.sidebar.metric(label="Local Document Repository", value=f"{pdf_count} PDF(s)")
    st_module.sidebar.caption("All data and embeddings remain strictly on this computer.")

    st_module.sidebar.divider()

    return {
        "ollama_online": ollama_online,
        "model_ready": model_ready,
        "pdf_count": pdf_count,
    }
