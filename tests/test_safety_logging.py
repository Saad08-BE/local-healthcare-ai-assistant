"""Unit tests for Phase 8 safety, validation, logging, and robustness."""

from __future__ import annotations

import logging
from pathlib import Path
import tempfile
import unittest

from app.safety.policy import SafetyDecision, healthcare_disclaimer, validate_question
from app.utils.logging import configure_logging, log_rag_query, log_security_event


class SafetyAndLoggingTests(unittest.TestCase):
    def test_crisis_and_harmful_queries_are_blocked(self) -> None:
        """Verify queries involving self-harm or lethal doses are blocked with emergency helpline message."""
        crisis_query = "how to overdose on paracetamol"
        decision = validate_question(crisis_query)
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.urgent)
        self.assertTrue(decision.crisis_block)
        self.assertIn("crisis", decision.user_message.lower())

    def test_excessively_long_queries_are_rejected(self) -> None:
        """Verify queries exceeding 4,000 characters are rejected as potential buffer/injection attacks."""
        long_query = "symptom " * 600  # > 4,000 chars
        decision = validate_question(long_query)
        self.assertFalse(decision.allowed)
        self.assertIn("maximum permitted limit", decision.user_message)

    def test_ssn_and_aadhaar_patterns_are_blocked(self) -> None:
        """Verify queries with identification numbers (SSN, Aadhaar, ID numbers) are blocked."""
        id_query = "look up patient with ssn 123-45-6789"
        decision = validate_question(id_query)
        self.assertFalse(decision.allowed)

    def test_urgent_red_flags_expansion(self) -> None:
        """Verify critical symptoms (stroke, heart attack, anaphylaxis) trigger urgent flags."""
        urgent_queries = [
            "I think my father is having a stroke with sudden numbness",
            "severe heart attack symptoms chest pain",
            "patient is coughing up blood",
        ]
        for q in urgent_queries:
            decision = validate_question(q)
            self.assertTrue(decision.allowed)
            self.assertTrue(decision.urgent)

    def test_operational_logger_never_records_query_text(self) -> None:
        """Verify the operational log records telemetry without saving raw query text or private health data."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_dir = Path(tmp_dir)
            logger = configure_logging(log_dir, debug=False)

            secret_patient_query = "My secret health condition is unusual fever"
            log_rag_query(
                logger=logger,
                query_length=len(secret_patient_query),
                retrieved_case_count=3,
                retrieved_doc_count=1,
                latency_seconds=0.25,
                model="qwen2.5:3b",
                is_offline=False,
                urgent=False,
            )

            # Flush handlers
            for handler in logger.handlers:
                handler.flush()

            log_file = log_dir / "operational.log"
            self.assertTrue(log_file.exists())
            log_content = log_file.read_text(encoding="utf-8")

            # Must contain metadata
            self.assertIn("cases_retrieved=3", log_content)
            self.assertIn("chars=43", log_content)
            self.assertIn("latency=0.250s", log_content)

            # Must NEVER contain the raw health text
            self.assertNotIn("secret health condition", log_content)
            self.assertNotIn("unusual fever", log_content)


if __name__ == "__main__":
    unittest.main()
