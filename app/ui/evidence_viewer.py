"""UI components for displaying multi-source evidence and citations."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import streamlit as st

from app.llm.rag_pipeline import RAGResponse


def render_evidence_panel(st_module, response: RAGResponse) -> None:
    """Render an expandable, tabbed evidence drawer showing the exact grounding data."""
    with st_module.expander("🔍 View Retrieved Grounding Evidence & Citations", expanded=False):
        tab_docs, tab_cohort, tab_cases = st_module.tabs([
            f"📄 PDF Documents ({len(response.document_sources)})",
            "📊 Cohort Statistics",
            f"🩺 Consultations & Cases ({len(response.retrieved_cases)})",
        ])

        # Tab 1: PDF Documents
        with tab_docs:
            if response.document_sources:
                for idx, doc in enumerate(response.document_sources, 1):
                    st_module.markdown(f"**[{idx}] {doc.citation}** — *Similarity Score: `{doc.score:.2f}`*")
                    st_module.info(doc.text)
            else:
                st_module.caption("No matching excerpts found in local PDF documents.")

        # Tab 2: Cohort Statistics
        with tab_cohort:
            cohort_stats = response.cohort_statistics
            if cohort_stats:
                symptom_evidence = cohort_stats.get("symptom_evidence", {})
                if symptom_evidence:
                    st_module.markdown("##### Symptom-to-Condition Associations")
                    for symp, diags in symptom_evidence.items():
                        diag_str = ", ".join(f"**{d['diagnosis']}** ({d['percentage']}%)" for d in diags)
                        st_module.write(f"- *{symp}*: {diag_str}")

                diag_evidence = cohort_stats.get("diagnosis_evidence", {})
                if diag_evidence:
                    st_module.markdown("##### Treatments & Outcomes")
                    for diag, info in diag_evidence.items():
                        treats = ", ".join(f"{t['treatment']} ({t['percentage']}%)" for t in info.get("common_treatments", []))
                        outcomes = ", ".join(f"{o['outcome']} ({o['percentage']}%)" for o in info.get("outcomes", []))
                        st_module.write(f"- **{diag}**: Treatments: [{treats}] | Outcomes: [{outcomes}]")
            else:
                st_module.caption("No statistical cohort correlations triggered for this query.")

        # Tab 3: Consultations and Cases
        with tab_cases:
            if response.retrieved_cases:
                for idx, case in enumerate(response.retrieved_cases, 1):
                    st_module.markdown(f"**Case / Consultation {idx}** — *Similarity: `{case.score:.2f}`*")
                    st_module.text_area(
                        label=f"Case text {idx}",
                        value=case.text,
                        height=120,
                        disabled=True,
                        label_visibility="collapsed",
                        key=f"case_view_{idx}_{hash(case.text[:30])}",
                    )
            else:
                st_module.caption("No individual clinical consultations matched above the similarity threshold.")
