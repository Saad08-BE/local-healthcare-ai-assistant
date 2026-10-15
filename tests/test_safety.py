import unittest

from app.safety import healthcare_disclaimer, validate_question


class SafetyTests(unittest.TestCase):
    def test_empty_question_is_rejected(self) -> None:
        decision = validate_question("   ")

        self.assertFalse(decision.allowed)
        self.assertIn("Enter a healthcare question", decision.user_message or "")

    def test_patient_record_search_is_rejected(self) -> None:
        decision = validate_question("Find patient ID P-12345")

        self.assertFalse(decision.allowed)
        self.assertIn("Patient-record search", decision.user_message or "")

    def test_general_question_is_allowed(self) -> None:
        decision = validate_question("What symptoms are associated with diabetes?")

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.normalized_question, "What symptoms are associated with diabetes?")

    def test_urgent_wording_is_flagged(self) -> None:
        decision = validate_question("I have chest pain")

        self.assertTrue(decision.allowed)
        self.assertTrue(decision.urgent)
        self.assertIn("not a medical diagnosis", healthcare_disclaimer())
