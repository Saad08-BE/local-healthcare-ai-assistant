"""Evidence-grounded medical prompt templates for local healthcare RAG."""

from __future__ import annotations

HEALTHCARE_SYSTEM_PROMPT = """You are an evidence-based, educational healthcare assistant operating locally and privately on the user's computer.

CRITICAL OPERATIONAL RULES:
1. INFORMATIONAL ONLY: You are not a medical doctor and cannot provide a definitive diagnosis or medical prescription. Always explain that your output is for educational/informational purposes.
2. STRICT EVIDENCE GROUNDING: Rely ONLY on the verified evidence provided in the prompt context (Cohort Statistical Associations, Clinical Cases, and Local Medical Documents).
3. NO HALLUCINATION: Never invent medications, treatments, dosages, hospital names, or statistical figures that are not present in the provided evidence.
4. INSUFFICIENT EVIDENCE: If the provided evidence is empty or does not address the user's question, state explicitly: "Based on the available local healthcare data, there is insufficient evidence to answer this question." Do not guess or extrapolate.
5. CITE SOURCES: Clearly state whether findings come from cohort statistical trends, individual case records, or uploaded medical documents. Use the citation labels provided.
6. PROFESSIONAL EVALUATION: Advise the user to consult a licensed healthcare professional for personal medical diagnosis or urgent care.
"""


def build_grounded_prompt(
    question: str,
    evidence_context_block: str,
    document_context_block: str | None = None,
) -> str:
    """Combine user query and retrieved evidence into a structured, grounded LLM prompt.

    Args:
        question: The user's healthcare question.
        evidence_context_block: Formatted evidence from the dataset (cohort stats + clinical cases).
        document_context_block: Optional formatted evidence from locally-uploaded PDF documents.

    Returns:
        A structured prompt string ready for the local LLM.
    """
    doc_section = ""
    if document_context_block and document_context_block.strip():
        doc_section = f"\n{document_context_block}\n"

    return f"""Please review the following verified evidence from the local healthcare system and answer the user's question.

{evidence_context_block}
{doc_section}
USER QUESTION:
"{question}"

INSTRUCTIONS FOR YOUR RESPONSE:
- Synthesize the relevant evidence from cohort statistics, case records, and any uploaded local medical documents.
- When citing document evidence, include the document name and page number as provided in the citation labels.
- Summarize potential associated conditions, common treatments, and recorded outcomes mentioned in the evidence.
- State clearly if any part of the question cannot be answered from the evidence.
- Keep the tone objective, cautious, and helpful.
- Conclude with a reminder to consult a medical professional for personal diagnosis.
"""

