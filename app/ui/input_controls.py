"""Input controls: model fetcher and PDF upload modal (used by main.py unified bar)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable
from uuid import uuid4

if TYPE_CHECKING:
    import streamlit as st

from app.config.settings import AppSettings
from app.ingestion.pdf_ingestor import PDFIngestor
from app.llm.ollama_client import OllamaClient
from app.retrieval.document_retriever import DocumentRetriever


def get_available_models(settings: AppSettings) -> list[str]:
    """Retrieve locally installed models from Ollama with fallback to default."""
    client = OllamaClient(base_url=settings.ollama_base_url, timeout_seconds=1.5)
    models: list[str] = []
    if client.is_online():
        try:
            models = client.list_models()
        except Exception:
            pass
    if settings.llm_model not in models:
        models.insert(0, settings.llm_model)
    return models


def _safe_pdf_destination(documents_dir: Path, uploaded_name: str) -> Path:
    """Return a non-overwriting, project-local destination for an uploaded PDF."""
    filename = Path(uploaded_name).name
    if not filename or filename in {".", ".."} or Path(filename).suffix.lower() != ".pdf":
        raise ValueError("Please select a PDF file with a valid filename.")

    candidate = documents_dir / filename
    counter = 1
    while candidate.exists():
        candidate = documents_dir / f"{Path(filename).stem}_{counter}{Path(filename).suffix}"
        counter += 1
    return candidate


def save_and_index_pdf(
    uploaded_name: str,
    uploaded_bytes: bytes,
    settings: AppSettings,
) -> tuple[Path, int]:
    """Validate, save, and rebuild the local PDF index without overwriting documents.

    The upload is parsed from a hidden temporary PDF before it becomes visible in the
    document repository. Invalid or scanned-only files therefore never remain there.
    """
    doc_dir = settings.paths.documents_dir
    doc_dir.mkdir(parents=True, exist_ok=True)
    destination = _safe_pdf_destination(doc_dir, uploaded_name)
    temporary_path = doc_dir / f".{uuid4().hex}.pdf"

    try:
        temporary_path.write_bytes(uploaded_bytes)
        ingestor = PDFIngestor(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        chunks = ingestor.process_file(temporary_path)
        temporary_path.replace(destination)

        all_chunks = ingestor.process_directory(doc_dir)
        retriever = DocumentRetriever(embedding_model=None)
        retriever.index_chunks(all_chunks, settings.paths.vector_store_dir)
        return destination, len(chunks)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise



def list_saved_pdfs(settings: AppSettings) -> list[Path]:
    """Return saved local PDFs in a stable, user-friendly order."""
    documents_dir = settings.paths.documents_dir
    if not documents_dir.exists():
        return []
    return sorted(
        (
            path for path in documents_dir.iterdir()
            if path.is_file() and path.suffix.lower() == ".pdf" and not path.name.startswith(".")
        ),
        key=lambda path: path.name.lower(),
    )


def render_saved_pdf_library(st_module, settings: AppSettings) -> None:
    """Show the persistent local PDF library in the sidebar."""
    sidebar = st_module.sidebar
    saved_pdfs = list_saved_pdfs(settings)
    with sidebar.expander(f"📚 Uploaded PDFs ({len(saved_pdfs)})", expanded=True):
        if not saved_pdfs:
            st_module.caption("No PDFs saved yet. Use ＋ beside the question box to add one.")
            return

        st_module.caption("Saved on this Mac · available for future questions")
        document_options = [
            "Most relevant PDF (automatic)",
            "Search all PDFs",
            *[path.name for path in saved_pdfs],
        ]
        current_choice = st_module.session_state.get(
            "active_pdf_for_questions", "Most relevant PDF (automatic)"
        )
        if current_choice not in document_options:
            current_choice = "Most relevant PDF (automatic)"
        st_module.selectbox(
            "PDF source for questions",
            options=document_options,
            index=document_options.index(current_choice),
            key="active_pdf_for_questions",
            help=(
                "Choose once which PDF to use for follow-up questions. Automatic mode "
                "uses the single most relevant PDF for each question."
            ),
        )
        for pdf_path in saved_pdfs:
            try:
                size_kb = max(1, round(pdf_path.stat().st_size / 1024))
                st_module.markdown(f"**📄 {pdf_path.name}**")
                st_module.caption(f"{size_kb} KB · stored locally")
            except OSError:
                st_module.markdown(f"📄 {pdf_path.name}")


def render_pdf_upload_modal(
    st_module,
    settings: AppSettings,
    on_indexed: Callable[[], None] | None = None,
) -> None:
    """Render inline PDF upload panel when + is toggled."""
    with st_module.container():
        head_col1, head_col2 = st_module.columns([9, 1])
        with head_col1:
            st_module.markdown(
                """
                <div style="font-size:0.9rem;font-weight:600;color:#e3e3e3;padding:4px 0;">
                    📄 Add Medical PDF to Local Index
                </div>
                """,
                unsafe_allow_html=True,
            )
        with head_col2:
            if st_module.button("✕", key="btn_close_pdf_modal", help="Close uploader"):
                st_module.session_state.show_upload_modal = False
                st_module.rerun()

        uploaded_file = st_module.file_uploader(
            "Upload PDF",
            type=["pdf"],
            key="inline_pdf_uploader",
            label_visibility="collapsed",
        )
        if uploaded_file is not None:
            btn_col1, btn_col2 = st_module.columns([3, 1])
            with btn_col1:
                if st_module.button("Index Document Now", type="primary", use_container_width=True):
                    try:
                        with st_module.spinner("Processing & indexing PDF locally..."):
                            destination, chunk_count = save_and_index_pdf(
                                uploaded_file.name,
                                uploaded_file.getvalue(),
                                settings,
                            )
                        if on_indexed:
                            on_indexed()
                        st_module.success(f"✅ Indexed {chunk_count} chunk(s) from `{destination.name}`!")
                        st_module.session_state.show_upload_modal = False
                        st_module.rerun()
                    except (OSError, ValueError, RuntimeError) as exc:
                        st_module.error(f"Unable to index this PDF: {exc}")
            with btn_col2:
                if st_module.button("Cancel", use_container_width=True):
                    st_module.session_state.show_upload_modal = False
                    st_module.rerun()
