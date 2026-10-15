#!/usr/bin/env python3
"""CLI utility to clean and sample ChatDoctor-HealthCareMagic-100k.csv."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.ingestion.chatdoctor_preprocessor import ChatDoctorPreprocessor


def main() -> int:
    parser = argparse.ArgumentParser(description="Preprocess ChatDoctor-HealthCareMagic dataset.")
    parser.add_argument("--sample-size", type=int, default=10000, help="Sample size (default: 10000)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    args = parser.parse_args()

    raw_csv = project_root / "data" / "raw" / "ChatDoctor-HealthCareMagic-100k.csv"
    processed_dir = project_root / "data" / "processed"

    print("=== Preprocessing ChatDoctor-HealthCareMagic Dataset ===")
    print(f"Source file: {raw_csv}")
    print(f"Sample size: {args.sample_size}")

    preprocessor = ChatDoctorPreprocessor()
    records = preprocessor.load_and_clean(
        raw_csv_path=raw_csv,
        sample_size=args.sample_size,
        seed=args.seed,
    )

    out_file = preprocessor.save_processed(
        records=records,
        output_dir=processed_dir,
        file_name=f"clean_chatdoctor_{len(records)}.jsonl",
    )

    print(f"\nSuccessfully processed {len(records):,} doctor-patient consultations.")
    print(f"Saved to: {out_file} ({out_file.stat().st_size / (1024*1024):.2f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
