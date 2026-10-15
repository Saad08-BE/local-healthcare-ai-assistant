"""Enhanced healthcare request validation, privacy guardrails, and emergency triage."""

from __future__ import annotations

from dataclasses import dataclass
import re

_PATIENT_RECORD_PATTERNS = (
    r"\b(find|show|look up|search|retrieve|get|display)\b.*\b(patient|patient id|record|mrn|medical record)\b",
    r"\b(patient|patient id|record|mrn)\b.*\b(find|show|look up|search|retrieve|get|display)\b",
    r"\b(ssn|social security|aadhaar|id\s*#?:\s*[0-9a-z-]+)\b",
)

_URGENT_PATTERNS = (
    r"\b(chest pain|difficulty breathing|can'?t breathe|unconscious|severe bleeding|stroke|heart attack|anaphylaxis|poisoning|suicidal|blue lips|sudden numbness|coughing up blood)\b",
)

_HARMFUL_PATTERNS = (
    r"\b(how to commit suicide|how to overdose|lethal dose of|how to end my life|kill myself)\b",
)


@dataclass(frozen=True)
class SafetyDecision:
    """Outcome of safety policy inspection."""

    allowed: bool
    normalized_question: str
    user_message: str | None = None
    urgent: bool = False
    crisis_block: bool = False


def healthcare_disclaimer() -> str:
    """Standard educational disclosure required on all outputs."""
    return (
        "This tool provides educational information from local sources and is not a medical diagnosis. "
        "For urgent or severe symptoms, seek immediate help from a qualified healthcare professional or emergency service."
    )


def validate_question(question: str) -> SafetyDecision:
    """Sanitize and validate healthcare queries with multi-layer defensive filters."""
    normalized = " ".join(question.strip().split())
    if not normalized:
        return SafetyDecision(False, "", "Enter a healthcare question or symptoms to continue.")

    # Guard against prompt injection / excessively long payload attacks (> 4000 chars)
    if len(normalized) > 4000:
        return SafetyDecision(
            False,
            normalized[:200],
            "Query length exceeds the maximum permitted limit (4,000 characters). Please provide a concise question.",
        )

    lowered = normalized.lower()

    # Crisis / Harmful self-harm detection
    if any(re.search(pattern, lowered) for pattern in _HARMFUL_PATTERNS):
        return SafetyDecision(
            False,
            normalized,
            "If you or someone you know is in crisis or danger, please immediately call your local emergency service or a suicide prevention helpline (e.g., 988 or 112).",
            urgent=True,
            crisis_block=True,
        )

    # Patient privacy protection (strict block on individual lookups)
    if any(re.search(pattern, lowered) for pattern in _PATIENT_RECORD_PATTERNS):
        return SafetyDecision(
            False,
            normalized,
            "Patient-record search is not available. Ask a general, de-identified healthcare question instead.",
        )

    # Emergency / urgent symptoms warning flag
    urgent = any(re.search(pattern, lowered) for pattern in _URGENT_PATTERNS)
    return SafetyDecision(True, normalized, urgent=urgent)
