"""Preprocessor for the ChatDoctor-HealthCareMagic natural clinical Q&A dataset."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import csv
import json
from pathlib import Path
import random
from typing import Any


@dataclass(frozen=True)
class ChatDoctorRecord:
    """A clean doctor-patient consultation record."""

    record_id: int
    patient_query: str
    doctor_advice: str
    semantic_text: str

    @classmethod
    def from_raw_dict(cls, row: dict[str, str], record_id: int) -> "ChatDoctorRecord":
        patient_query = row.get("input", "").strip()
        doctor_advice = row.get("output", "").strip()

        # Build clean semantic representation for local vector embeddings
        semantic_text = (
            f"Patient Inquiry: {patient_query}\n"
            f"Doctor Clinical Guidance: {doctor_advice}"
        )

        return cls(
            record_id=record_id,
            patient_query=patient_query,
            doctor_advice=doctor_advice,
            semantic_text=semantic_text,
        )


class ChatDoctorPreprocessor:
    """Cleans, filters, and samples ChatDoctor-HealthCareMagic records."""

    def __init__(self, min_input_len: int = 15, min_output_len: int = 30) -> None:
        self.min_input_len = min_input_len
        self.min_output_len = min_output_len

    def is_valid_row(self, row: dict[str, str]) -> bool:
        inp = row.get("input", "").strip()
        out = row.get("output", "").strip()
        return len(inp) >= self.min_input_len and len(out) >= self.min_output_len

    def load_and_clean(
        self,
        raw_csv_path: Path,
        sample_size: int | None = 10000,
        seed: int = 42,
    ) -> list[ChatDoctorRecord]:
        if not raw_csv_path.exists():
            raise FileNotFoundError(f"ChatDoctor dataset not found at {raw_csv_path}")

        records: list[ChatDoctorRecord] = []
        with open(raw_csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not self.is_valid_row(row):
                    continue
                records.append(ChatDoctorRecord.from_raw_dict(row, record_id=len(records) + 1))

        if sample_size and sample_size < len(records):
            rng = random.Random(seed)
            sampled = list(records)
            rng.shuffle(sampled)
            sampled = sampled[:sample_size]
            # Reindex
            records = [
                ChatDoctorRecord(
                    record_id=idx + 1,
                    patient_query=r.patient_query,
                    doctor_advice=r.doctor_advice,
                    semantic_text=r.semantic_text,
                )
                for idx, r in enumerate(sampled)
            ]

        return records

    def save_processed(
        self,
        records: list[ChatDoctorRecord],
        output_dir: Path,
        file_name: str = "clean_chatdoctor_10000.jsonl",
    ) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        out_file = output_dir / file_name
        with open(out_file, mode="w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
        return out_file
