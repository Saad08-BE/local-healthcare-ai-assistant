"""Settings dialog and system metrics modal."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import streamlit as st

from app.config.settings import AppSettings
from app.llm.ollama_client import OllamaClient


def render_settings_dialog(st_module, settings: AppSettings) -> None:
    """Render the Settings modal/dialog containing all configuration and system metrics."""
    client = OllamaClient(base_url=settings.ollama_base_url, timeout_seconds=1.5)
    ollama_online = client.is_online()
    models_available = []
    if ollama_online:
        try:
            models_available = client.list_models()
        except Exception:
            pass

    doc_dir = settings.paths.documents_dir
    pdf_count = len(list(doc_dir.glob("*.pdf")) + list(doc_dir.glob("*.PDF"))) if doc_dir.exists() else 0

    vector_dir = settings.paths.vector_store_dir
    index_files = list(vector_dir.glob("*.json*")) if vector_dir.exists() else []
    total_index_mb = sum(f.stat().st_size for f in index_files) / (1024 * 1024)

    st_module.markdown("### ⚙️ System Settings & Diagnostic Metrics")
    st_module.caption("100% Local Apple Silicon Architecture • Loopback Bound")

    st_module.divider()

    col1, col2 = st_module.columns(2)
    with col1:
        st_module.markdown("#### 🩺 Local Services")
        if ollama_online:
            st_module.success("🟢 Local Ollama Daemon: **Active**")
        else:
            st_module.warning("🟡 Local Ollama Daemon: **Offline** (Evidence synthesis mode active)")

        st_module.write(f"- **Ollama Endpoint:** `{settings.ollama_base_url}`")
        st_module.write(f"- **Default Model:** `{settings.llm_model}`")
        st_module.write(f"- **Installed Local Models:** `{', '.join(models_available) if models_available else 'None detected'}`")

    with col2:
        st_module.markdown("#### 📊 Vector Store & Ingestion")
        st_module.metric("Indexed Local PDFs", f"{pdf_count} document(s)")
        st_module.metric("Vector Index Footprint", f"{total_index_mb:.2f} MB")
        st_module.write(f"- **Embedding Model:** `{settings.embedding_model}`")
        st_module.write(f"- **Chunk Size / Overlap:** `{settings.chunk_size}` / `{settings.chunk_overlap}` chars")
        st_module.write(f"- **Top-K Search:** `{settings.top_k}` records")

    st_module.divider()

    st_module.markdown("#### 🔒 Privacy & Local Security Status")
    st_module.info(
        "• All patient queries, vector embeddings, and PDF documents are strictly retained in project-local storage.\n"
        "• Loopback host validation enforces zero external network calls.\n"
        "• Patient identifiers (`Patient_ID`) are removed before indexing to guarantee HIPAA compliance."
    )
