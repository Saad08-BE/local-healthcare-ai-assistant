"""Unit tests for dataset cleaning, validation, sampling, and cohort aggregation."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from app.ingestion.dataset_preprocessor import DatasetPreprocessor, HealthcareRecord


class PreprocessingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.preprocessor = DatasetPreprocessor(min_blood_glucose=10.0, min_hba1c=2.0)
        self.sample_row = {
            "Patient_ID": "TEST-12345-SECRET",
            "Age": "45",
            "Gender": "Female",
            "Region": "Tamil Nadu",
            "Socioeconomic_Status": "Middle",
            "Occupation": "Teacher",
            "Visit_Date": "2025-01-15",
            "Symptoms": "Fever, fatigue, increased thirst",
            "Primary_Diagnosis": "Type 2 Diabetes",
            "Blood_Glucose_mg_dL": "180.5",
            "HbA1c_%": "7.8",
            "Total_Cholesterol_mg_dL": "210.0",
            "Treatment_Type": "Medication",
            "Treatment_Outcome": "Improved",
            "Imaging_Type": "None",
            "Imaging_Findings": "No imaging performed",
            "Hospital_Type": "Government",
            "Insurance_Covered": "True",
            "BMI": "25.4",
        }

    def test_record_parsing_and_privacy(self) -> None:
        """Ensure Patient_ID is excluded from record attributes and semantic text."""
        record = HealthcareRecord.from_raw_dict(self.sample_row, record_id=1)
        self.assertEqual(record.record_id, 1)
        self.assertEqual(record.age, 45)
        self.assertEqual(record.primary_diagnosis, "Type 2 Diabetes")
        self.assertTrue(record.insurance_covered)
        self.assertNotIn("TEST-12345-SECRET", record.semantic_text)
        self.assertNotIn("Patient_ID", dir(record))
        self.assertIn("Age 45", record.semantic_text)
        self.assertIn("Type 2 Diabetes", record.semantic_text)

    def test_outlier_rejection(self) -> None:
        """Ensure negative or non-physiological measurements are rejected."""
        valid = self.preprocessor.is_valid_row(self.sample_row)
        self.assertTrue(valid)

        bad_glucose_row = dict(self.sample_row, Blood_Glucose_mg_dL="-11.7")
        self.assertFalse(self.preprocessor.is_valid_row(bad_glucose_row))

        zero_glucose_row = dict(self.sample_row, Blood_Glucose_mg_dL="0.0")
        self.assertFalse(self.preprocessor.is_valid_row(zero_glucose_row))

        low_hba1c_row = dict(self.sample_row, **{"HbA1c_%": "1.2"})
        self.assertFalse(self.preprocessor.is_valid_row(low_hba1c_row))

    def test_sampling_and_cohort_aggregates(self) -> None:
        """Test sampling and aggregate calculation on synthetic records."""
        records = []
        diagnoses = ["Type 2 Diabetes", "Hypertension", "Dengue"]
        for i in range(100):
            row = dict(
                self.sample_row,
                Primary_Diagnosis=diagnoses[i % 3],
                Blood_Glucose_mg_dL=str(100.0 + i),
            )
            records.append(HealthcareRecord.from_raw_dict(row, record_id=i + 1))

        # Test stratified sampling
        sampled = self.preprocessor._stratified_sample(records, sample_size=30, seed=42)
        self.assertEqual(len(sampled), 30)

        # Test cohort aggregates
        aggregates = self.preprocessor.compute_cohort_aggregates(sampled)
        self.assertEqual(aggregates["total_records_analyzed"], 30)
        self.assertIn("symptom_to_diagnosis_associations", aggregates)
        self.assertIn("diagnosis_to_treatment_associations", aggregates)
        self.assertIn("diagnosis_measurement_averages", aggregates)
        self.assertIn("Type 2 Diabetes", aggregates["diagnosis_measurement_averages"])

    def test_save_and_load_processed(self) -> None:
        """Test end-to-end saving of clean JSONL and metadata."""
        record = HealthcareRecord.from_raw_dict(self.sample_row, record_id=1)
        aggregates = self.preprocessor.compute_cohort_aggregates([record])
        metadata = {"sample_size": 1, "test": True}

        from app.ingestion.dataset_preprocessor import PreprocessedDataset

        dataset = PreprocessedDataset(
            records=[record],
            cohort_aggregates=aggregates,
            metadata=metadata,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            saved = self.preprocessor.save_processed(dataset, tmp_path, file_prefix="test_records")
            self.assertTrue(saved["records_path"].exists())
            self.assertTrue(saved["aggregates_path"].exists())
            self.assertTrue(saved["metadata_path"].exists())

            # Verify JSONL content
            lines = saved["records_path"].read_text(encoding="utf-8").strip().split("\n")
            self.assertEqual(len(lines), 1)
            loaded_json = json.loads(lines[0])
            self.assertEqual(loaded_json["primary_diagnosis"], "Type 2 Diabetes")
            self.assertNotIn("Patient_ID", loaded_json)

    def test_chatdoctor_preprocessing(self) -> None:
        """Test ChatDoctor record cleaning, validation, and serialization."""
        from app.ingestion.chatdoctor_preprocessor import ChatDoctorPreprocessor, ChatDoctorRecord

        preprocessor = ChatDoctorPreprocessor(min_input_len=10, min_output_len=15)
        valid_row = {
            "instruction": "Answer medical questions",
            "input": "I have persistent fever and sore throat for 3 days.",
            "output": "Please take paracetamol and stay well hydrated. Consult an ENT specialist if worsening.",
        }
        self.assertTrue(preprocessor.is_valid_row(valid_row))

        short_row = {"input": "Help", "output": "See doctor"}
        self.assertFalse(preprocessor.is_valid_row(short_row))

        record = ChatDoctorRecord.from_raw_dict(valid_row, record_id=1)
        self.assertIn("persistent fever", record.semantic_text)
        self.assertIn("Doctor Clinical Guidance", record.semantic_text)


if __name__ == "__main__":
    unittest.main()
