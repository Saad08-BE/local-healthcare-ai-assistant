"""Local Streamlit entry point for the healthcare intelligence system with Gemini-styled UI."""

from __future__ import annotations

from pathlib import Path
import sys

# Streamlit executes this file as a script, so explicitly expose the project
# root before importing the top-level ``app`` package.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from app.config import AppSettings, SettingsError
from app.llm.rag_pipeline import HealthcareRAGPipeline, RAGResponse
from app.safety import healthcare_disclaimer
from app.ui.chat_state import get_current_session, initialize_session_state
from app.ui.evidence_viewer import render_evidence_panel
from app.ui.input_controls import get_available_models, render_pdf_upload_modal
from app.ui.settings_dialog import render_settings_dialog
from app.ui.sidebar import render_sidebar_navigation
from app.ui.theme import apply_gemini_theme


@st.cache_resource(show_spinner="Initializing local healthcare intelligence engine...")
def get_pipeline(settings: AppSettings) -> HealthcareRAGPipeline:
    """Cache the loaded RAG pipeline across user interactions for instant responses."""
    return HealthcareRAGPipeline.initialize(settings)


def run() -> None:
    """Render the full local-only Streamlit healthcare RAG application in Gemini-inspired dark UI."""
    st.set_page_config(
        page_title="HealthAI",
        page_icon="✨",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 1. Apply Dark Gemini Aesthetic
    apply_gemini_theme(st)

    # 2. Configuration & Path Verification
    try:
        settings = AppSettings.from_environment()
        settings.paths.create_runtime_directories()
    except SettingsError as exc:
        st.error(f"Local configuration error: {exc}")
        st.stop()

    # 3. Session State Initialization
    initialize_session_state(st)

    # Ensure selected_model is initialised
    available_models = get_available_models(settings)
    if "selected_model" not in st.session_state or st.session_state.selected_model not in available_models:
        st.session_state.selected_model = available_models[0] if available_models else settings.llm_model

    # 4. Settings Dialog / Modal check
    if st.session_state.show_settings_dialog:
        with st.container():
            render_settings_dialog(st, settings)
            if st.button("✕ Close Settings", type="secondary"):
                st.session_state.show_settings_dialog = False
                st.rerun()
            st.divider()

    # 5. Left Sidebar Navigation
    render_sidebar_navigation(st, settings)

    # 6. Top Status Bar  (privacy pill LEFT | incognito toggle RIGHT)
    top_col1, top_col2 = st.columns([8, 2])
    with top_col1:
        if st.session_state.temp_mode:
            st.markdown(
                '<span class="temp-pill">🔒 Incognito Consultation (Not saved)</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<span class="privacy-pill">🔒 100% Local · Apple Silicon</span>',
                unsafe_allow_html=True,
            )
    with top_col2:
        # Incognito toggle lives here — beside the privacy pill
        incog = st.toggle(
            "Incognito",
            value=st.session_state.temp_mode,
            help="Temporary mode: queries are NOT saved to conversation history.",
            key="top_incognito_toggle",
        )
        if incog != st.session_state.temp_mode:
            st.session_state.temp_mode = incog
            st.rerun()

    # 7. Main Content Area
    current_session = get_current_session(st)

    # Hero Screen (empty session)
    if not current_session.messages:
        st.markdown(
            """
            <div class="gemini-hero-container">
                <div class="gemini-hero-title">Where should we start?</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    else:
        # Render Conversation Message Thread
        for msg in current_session.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if "response" in msg and msg["response"] is not None:
                    render_evidence_panel(st, msg["response"])

    # 8. PDF upload panel (shown when + is toggled)
    if st.session_state.show_upload_modal:
        render_pdf_upload_modal(st, settings, on_indexed=get_pipeline.clear)

    # 9. ── Unified Gemini-style input pill ──
    #    Layout: [➕]  [text input .................]  [model▾]  [➤]
    with st.form("unified_chat_form", clear_on_submit=True):
        c_plus, c_text, c_model, c_send = st.columns([0.55, 7, 1.8, 0.55])

        with c_plus:
            attach_clicked = st.form_submit_button(
                "＋",
                help="Upload a local medical PDF to index",
                use_container_width=True,
            )

        with c_text:
            user_query = st.text_input(
                "query",
                placeholder="Ask a healthcare question or inquire about medical PDFs...",
                label_visibility="collapsed",
                key="unified_query_input",
            )

        with c_model:
            sel_model = st.selectbox(
                "Model",
                options=available_models,
                index=(
                    available_models.index(st.session_state.selected_model)
                    if st.session_state.selected_model in available_models
                    else 0
                ),
                label_visibility="collapsed",
                key="unified_model_select",
            )

        with c_send:
            send_clicked = st.form_submit_button(
                "➤",
                type="primary",
                use_container_width=True,
            )

    # Handle + (PDF toggle) — capture model before rerun
    if attach_clicked:
        st.session_state.show_upload_modal = not st.session_state.show_upload_modal
        st.rerun()

    # Handle Send
    query_to_run = user_query.strip() if send_clicked and user_query else None

    if query_to_run:
        # Automatically collapse upload modal when asking a question
        st.session_state.show_upload_modal = False
        # Persist the chosen model
        st.session_state.selected_model = sel_model

        # Append user message
        current_session.add_message(role="user", content=query_to_run)
        with st.chat_message("user"):
            st.markdown(query_to_run)

        # Run pipeline
        pipeline = get_pipeline(settings)
        with st.chat_message("assistant"):
            with st.spinner(f"Consulting local clinical evidence using `{sel_model}`..."):
                response: RAGResponse = pipeline.answer_question(
                    query_to_run,
                    model_override=sel_model,
                )

            if response.urgent_warning:
                st.warning(
                    "⚠️ **Urgent Medical Notice**: Emergency symptoms detected. "
                    "Seek immediate emergency medical care."
                )

            st.markdown(response.answer)

            mode_badge = (
                f"🟢 Local LLM ({response.llm_model})"
                if not response.is_offline_fallback
                else "🟡 Offline Evidence Synthesis"
            )
            st.caption(
                f"⏱️ Latency: `{response.total_latency_seconds:.2f}s` | "
                f"Mode: {mode_badge} | "
                f"Citations: `{len(response.document_sources)}` PDF doc(s), "
                f"`{len(response.retrieved_cases)}` clinical case(s)"
            )

            render_evidence_panel(st, response)
            current_session.add_message(role="assistant", content=response.answer, response=response)

    # Footer Disclaimer
    st.markdown(
        f"<div style='text-align:center;color:#5f6368;font-size:0.72rem;margin-top:20px;'>"
        f"{healthcare_disclaimer()}</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    run()
