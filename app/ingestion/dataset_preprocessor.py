"""Dataset analysis, cleaning, and preprocessing for the local healthcare RAG pipeline."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import csv
import json
from pathlib import Path
import random
from typing import Any


@dataclass(frozen=True)
class HealthcareRecord:
    """A clean, de-identified clinical record from the healthcare dataset.

    Note: Patient_ID is intentionally omitted to uphold local patient privacy.
    """

    record_id: int
    age: int
    gender: str
    region: str
    socioeconomic_status: str
    occupation: str
    visit_date: str
    symptoms: str
    primary_diagnosis: str
    blood_glucose_mg_dl: float
    hba1c_pct: float
    total_cholesterol_mg_dl: float
    treatment_type: str
    treatment_outcome: str
    imaging_type: str
    imaging_findings: str
    hospital_type: str
    insurance_covered: bool
    bmi: float
    semantic_text: str

    @classmethod
    def from_raw_dict(cls, row: dict[str, str], record_id: int) -> "HealthcareRecord":
        """Parse, sanitize, and create a structured record from raw CSV row."""
        age = int(float(row.get("Age", 0)))
        gender = row.get("Gender", "").strip()
        region = row.get("Region", "").strip()
        socioeconomic_status = row.get("Socioeconomic_Status", "").strip()
        occupation = row.get("Occupation", "").strip()
        visit_date = row.get("Visit_Date", "").strip()
        symptoms = row.get("Symptoms", "").strip()
        primary_diagnosis = row.get("Primary_Diagnosis", "").strip()
        blood_glucose = float(row.get("Blood_Glucose_mg_dL", 0.0))
        hba1c = float(row.get("HbA1c_%", 0.0))
        cholesterol = float(row.get("Total_Cholesterol_mg_dL", 0.0))
        treatment_type = row.get("Treatment_Type", "").strip()
        treatment_outcome = row.get("Treatment_Outcome", "").strip()
        imaging_type = row.get("Imaging_Type", "").strip()
        imaging_findings = row.get("Imaging_Findings", "").strip()
        hospital_type = row.get("Hospital_Type", "").strip()
        insurance_str = row.get("Insurance_Covered", "").strip().lower()
        insurance_covered = insurance_str in ("true", "1", "yes")
        bmi = float(row.get("BMI", 0.0))

        # Build natural language semantic text for local embeddings (privacy-safe, no Patient_ID)
        semantic_text = (
            f"Patient Demographic: Age {age}, Gender {gender}, Region {region}, "
            f"Socioeconomic Status {socioeconomic_status}. "
            f"Reported Symptoms: {symptoms}. "
            f"Primary Diagnosis: {primary_diagnosis}. "
            f"Clinical Measurements: Blood Glucose {blood_glucose:.1f} mg/dL, "
            f"HbA1c {hba1c:.1f}%, Cholesterol {cholesterol:.1f} mg/dL, BMI {bmi:.1f}. "
            f"Treatment: {treatment_type} with outcome {treatment_outcome}. "
            f"Diagnostic Imaging: {imaging_type} ({imaging_findings}). "
            f"Hospital Facility: {hospital_type}."
        )

        return cls(
            record_id=record_id,
            age=age,
            gender=gender,
            region=region,
            socioeconomic_status=socioeconomic_status,
            occupation=occupation,
            visit_date=visit_date,
            symptoms=symptoms,
            primary_diagnosis=primary_diagnosis,
            blood_glucose_mg_dl=round(blood_glucose, 1),
            hba1c_pct=round(hba1c, 1),
            total_cholesterol_mg_dl=round(cholesterol, 1),
            treatment_type=treatment_type,
            treatment_outcome=treatment_outcome,
            imaging_type=imaging_type,
            imaging_findings=imaging_findings,
            hospital_type=hospital_type,
            insurance_covered=insurance_covered,
            bmi=round(bmi, 1),
            semantic_text=semantic_text,
        )


@dataclass
class PreprocessedDataset:
    """Container holding cleaned records, cohort summaries, and metadata."""

    records: list[HealthcareRecord]
    cohort_aggregates: dict[str, Any]
    metadata: dict[str, Any]


class DatasetPreprocessor:
    """Preprocesses raw healthcare records into clean samples and cohort aggregates."""

    def __init__(
        self,
        min_blood_glucose: float = 10.0,
        min_hba1c: float = 2.0,
        min_age: int = 1,
    ) -> None:
        self.min_blood_glucose = min_blood_glucose
        self.min_hba1c = min_hba1c
        self.min_age = min_age

    def is_valid_row(self, row: dict[str, str]) -> bool:
        """Validate physiological plausibility of the row."""
        try:
            glucose = float(row.get("Blood_Glucose_mg_dL", 0.0))
            hba1c = float(row.get("HbA1c_%", 0.0))
            age = float(row.get("Age", 0.0))
            if glucose < self.min_blood_glucose:
                return False
            if hba1c < self.min_hba1c:
                return False
            if age < self.min_age:
                return False
            return True
        except (ValueError, TypeError):
            return False

    def load_and_clean(
        self,
        raw_csv_path: Path,
        sample_size: int | None = 10000,
        seed: int = 42,
    ) -> PreprocessedDataset:
        """Read raw CSV, sanitize records, sample deterministically, and compute aggregates."""
        if not raw_csv_path.exists():
            raise FileNotFoundError(f"Raw dataset file not found at {raw_csv_path}")

        raw_total = 0
        cleaned_records: list[HealthcareRecord] = []
        dropped_outliers = 0

        with open(raw_csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw_total += 1
                if not self.is_valid_row(row):
                    dropped_outliers += 1
                    continue
                record = HealthcareRecord.from_raw_dict(row, record_id=len(cleaned_records) + 1)
                cleaned_records.append(record)

        # Apply deterministic sampling if sample_size is set and smaller than total
        if sample_size and sample_size < len(cleaned_records):
            sampled_records = self._stratified_sample(
                cleaned_records, sample_size=sample_size, seed=seed
            )
        else:
            sampled_records = cleaned_records

        # Compute cohort summaries on sampled records
        cohort_aggregates = self.compute_cohort_aggregates(sampled_records)

        metadata = {
            "source_file": raw_csv_path.name,
            "raw_total_rows": raw_total,
            "dropped_outliers": dropped_outliers,
            "valid_clean_rows": len(cleaned_records),
            "sample_size": len(sampled_records),
            "random_seed": seed,
            "sampling_method": "stratified_by_primary_diagnosis" if sample_size else "full_dataset",
        }

        return PreprocessedDataset(
            records=sampled_records,
            cohort_aggregates=cohort_aggregates,
            metadata=metadata,
        )

    def _stratified_sample(
        self,
        records: list[HealthcareRecord],
        sample_size: int,
        seed: int = 42,
    ) -> list[HealthcareRecord]:
        """Perform deterministic stratified sampling across Primary_Diagnosis."""
        rng = random.Random(seed)
        strata = defaultdict(list)
        for r in records:
            strata[r.primary_diagnosis].append(r)

        total_count = len(records)
        sampled: list[HealthcareRecord] = []

        for diagnosis, group in strata.items():
            # Calculate proportion for this stratum
            stratum_target = max(1, int(round((len(group) / total_count) * sample_size)))
            shuffled_group = list(group)
            rng.shuffle(shuffled_group)
            sampled.extend(shuffled_group[:stratum_target])

        # Adjust in case rounding produced slight discrepancy
        rng.shuffle(sampled)
        if len(sampled) > sample_size:
            sampled = sampled[:sample_size]
        elif len(sampled) < sample_size:
            remaining = [r for r in records if r not in set(sampled)]
            rng.shuffle(remaining)
            sampled.extend(remaining[: sample_size - len(sampled)])

        # Re-index record IDs sequentially
        reindexed = [
            HealthcareRecord(
                record_id=idx + 1,
                age=r.age,
                gender=r.gender,
                region=r.region,
                socioeconomic_status=r.socioeconomic_status,
                occupation=r.occupation,
                visit_date=r.visit_date,
                symptoms=r.symptoms,
                primary_diagnosis=r.primary_diagnosis,
                blood_glucose_mg_dl=r.blood_glucose_mg_dl,
                hba1c_pct=r.hba1c_pct,
                total_cholesterol_mg_dl=r.total_cholesterol_mg_dl,
                treatment_type=r.treatment_type,
                treatment_outcome=r.treatment_outcome,
                imaging_type=r.imaging_type,
                imaging_findings=r.imaging_findings,
                hospital_type=r.hospital_type,
                insurance_covered=r.insurance_covered,
                bmi=r.bmi,
                semantic_text=r.semantic_text,
            )
            for idx, r in enumerate(sampled)
        ]
        return reindexed

    def compute_cohort_aggregates(self, records: list[HealthcareRecord]) -> dict[str, Any]:
        """Calculate structured clinical distributions for symptom & treatment reasoning."""
        total = len(records)
        if total == 0:
            return {}

        symptom_to_diagnoses = defaultdict(Counter)
        diagnosis_to_treatments = defaultdict(Counter)
        diagnosis_to_outcomes = defaultdict(Counter)
        diagnosis_to_measurements = defaultdict(
            lambda: {"glucose": [], "hba1c": [], "cholesterol": [], "bmi": []}
        )
        hospital_distributions = Counter()
        region_distributions = Counter()

        for r in records:
            symptom_to_diagnoses[r.symptoms][r.primary_diagnosis] += 1
            diagnosis_to_treatments[r.primary_diagnosis][r.treatment_type] += 1
            diagnosis_to_outcomes[r.primary_diagnosis][r.treatment_outcome] += 1
            meas = diagnosis_to_measurements[r.primary_diagnosis]
            meas["glucose"].append(r.blood_glucose_mg_dl)
            meas["hba1c"].append(r.hba1c_pct)
            meas["cholesterol"].append(r.total_cholesterol_mg_dl)
            meas["bmi"].append(r.bmi)
            hospital_distributions[r.hospital_type] += 1
            region_distributions[r.region] += 1

        # Format associations with percentages
        symptom_associations = {}
        for symp, diag_counts in symptom_to_diagnoses.items():
            symp_total = sum(diag_counts.values())
            symptom_associations[symp] = [
                {
                    "diagnosis": diag,
                    "count": count,
                    "percentage": round((count / symp_total) * 100, 2),
                }
                for diag, count in diag_counts.most_common()
            ]

        treatment_associations = {}
        for diag, treat_counts in diagnosis_to_treatments.items():
            diag_total = sum(treat_counts.values())
            treatment_associations[diag] = [
                {
                    "treatment": treat,
                    "count": count,
                    "percentage": round((count / diag_total) * 100, 2),
                }
                for treat, count in treat_counts.most_common()
            ]

        outcome_associations = {}
        for diag, out_counts in diagnosis_to_outcomes.items():
            diag_total = sum(out_counts.values())
            outcome_associations[diag] = [
                {
                    "outcome": out,
                    "count": count,
                    "percentage": round((count / diag_total) * 100, 2),
                }
                for out, count in out_counts.most_common()
            ]

        measurement_summaries = {}
        for diag, m in diagnosis_to_measurements.items():
            n = len(m["glucose"])
            measurement_summaries[diag] = {
                "sample_count": n,
                "mean_blood_glucose": round(sum(m["glucose"]) / n, 1) if n else 0.0,
                "mean_hba1c": round(sum(m["hba1c"]) / n, 1) if n else 0.0,
                "mean_cholesterol": round(sum(m["cholesterol"]) / n, 1) if n else 0.0,
                "mean_bmi": round(sum(m["bmi"]) / n, 1) if n else 0.0,
            }

        return {
            "total_records_analyzed": total,
            "symptom_to_diagnosis_associations": symptom_associations,
            "diagnosis_to_treatment_associations": treatment_associations,
            "diagnosis_to_outcome_associations": outcome_associations,
            "diagnosis_measurement_averages": measurement_summaries,
            "hospital_breakdown": dict(hospital_distributions),
            "region_breakdown": dict(region_distributions),
        }

    def save_processed(
        self,
        dataset: PreprocessedDataset,
        output_dir: Path,
        file_prefix: str = "clean_records_sample",
    ) -> dict[str, Path]:
        """Save clean records, aggregates, and metadata to project-local output directory."""
        output_dir.mkdir(parents=True, exist_ok=True)

        records_file = output_dir / f"{file_prefix}.jsonl"
        aggregates_file = output_dir / "cohort_aggregates.json"
        metadata_file = output_dir / "dataset_metadata.json"

        # Save clean records as JSONL
        with open(records_file, mode="w", encoding="utf-8") as f:
            for record in dataset.records:
                f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

        # Save cohort aggregates
        with open(aggregates_file, mode="w", encoding="utf-8") as f:
            json.dump(dataset.cohort_aggregates, f, indent=2, ensure_ascii=False)

        # Save metadata
        with open(metadata_file, mode="w", encoding="utf-8") as f:
            json.dump(dataset.metadata, f, indent=2, ensure_ascii=False)

        return {
            "records_path": records_file,
            "aggregates_path": aggregates_file,
            "metadata_path": metadata_file,
        }
