"""UI components for local medical document uploading and live re-indexing."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import streamlit as st

from app.config.settings import AppSettings
from app.ui.input_controls import save_and_index_pdf


def render_document_uploader(st_module, settings: AppSettings) -> bool:
    """Render the document uploader panel. Returns True if a new file was indexed."""
    st_module.sidebar.subheader("📄 Upload Medical PDF")
    st_module.sidebar.caption("Reports, lab results, or clinical practice guidelines")

    uploaded_file = st_module.sidebar.file_uploader(
        "Select a local PDF to index",
        type=["pdf"],
        help="The document is saved locally into data/documents/ and indexed immediately.",
        key="pdf_uploader",
    )

    if uploaded_file is not None:
        save_btn = st_module.sidebar.button("Index Document Locally", type="primary")
        if save_btn:
            with st_module.sidebar.status("Processing PDF locally..."):
                try:
                    destination, chunk_count = save_and_index_pdf(
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        settings,
                    )
                    st_module.sidebar.success(f"Indexed {chunk_count} chunk(s) from `{destination.name}`!")
                    return True
                except (OSError, ValueError, RuntimeError) as exc:
                    st_module.sidebar.error(f"Failed to index: {exc}")
                    return False

    return False
