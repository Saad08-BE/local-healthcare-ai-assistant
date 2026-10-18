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

    st_module.markdown("### ⚙️ Settings & system health")
    st_module.caption("A quick overview of the services and local resources used by HealthAI.")
    st_module.markdown(
        '<div style="padding:12px 15px;border:1px solid rgba(155,188,255,.18);'
        'background:rgba(125,166,255,.055);border-radius:13px;margin:10px 0 16px;">'
        '<span style="font-weight:600;color:#c7d9ff;">🔐 Local-first design</span><br>'
        '<span style="font-size:.88rem;color:#a9b8cc;">Your documents and local model are managed on this computer. '
        'Check the configured endpoint and local services below.</span></div>',
        unsafe_allow_html=True,
    )

    st_module.divider()

    col1, col2 = st_module.columns(2)
    with col1:
        st_module.markdown("#### 🩺 Local services")
        st_module.markdown("**Model connection**")
        if ollama_online:
            st_module.success("🟢 Local Ollama Daemon: **Active**")
        else:
            st_module.warning("🟡 Local Ollama Daemon: **Offline** (Evidence synthesis mode active)")

        st_module.write(f"- **Ollama Endpoint:** `{settings.ollama_base_url}`")
        st_module.write(f"- **Default Model:** `{settings.llm_model}`")
        st_module.write(f"- **Installed Local Models:** `{', '.join(models_available) if models_available else 'None detected'}`")

    with col2:
        st_module.markdown("#### 📚 Documents & search")
        st_module.markdown("**Local index**")
        st_module.metric("Indexed Local PDFs", f"{pdf_count} document(s)")
        st_module.metric("Vector Index Footprint", f"{total_index_mb:.2f} MB")
        st_module.write(f"- **Embedding Model:** `{settings.embedding_model}`")
        st_module.write(f"- **Chunk Size / Overlap:** `{settings.chunk_size}` / `{settings.chunk_overlap}` chars")
        st_module.write(f"- **Top-K Search:** `{settings.top_k}` records")

    st_module.divider()

    st_module.markdown("#### 🔒 Privacy & Local Security Status")
    st_module.info(
        "• Uploaded PDFs and the search index are stored in project-local folders.\n"
        "• The application is configured for a local Ollama endpoint; verify the endpoint and network settings on your machine.\n"
        "• Privacy safeguards are intended for this academic project and do not constitute a certification or guarantee of regulatory compliance."
    )
