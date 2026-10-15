#!/usr/bin/env python3
"""CLI utility to run dataset cleaning and preprocessing on Indian_healthcare.csv."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.ingestion.dataset_preprocessor import DatasetPreprocessor


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preprocess and sample Indian_healthcare.csv for local RAG."
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=10000,
        help="Number of records to sample (default: 10000; set 0 for full dataset)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic random seed for sampling (default: 42)",
    )
    args = parser.parse_args()

    sample_size = None if args.sample_size <= 0 else args.sample_size
    project_root = Path(__file__).resolve().parents[1]
    raw_csv = project_root / "data" / "raw" / "Indian_healthcare.csv"
    processed_dir = project_root / "data" / "processed"

    print(f"=== Starting Healthcare Dataset Preprocessing ===")
    print(f"Source file: {raw_csv}")
    print(f"Sample size target: {sample_size or 'FULL (100,000)'}")
    print(f"Random seed: {args.seed}")

    preprocessor = DatasetPreprocessor()
    try:
        dataset = preprocessor.load_and_clean(
            raw_csv_path=raw_csv,
            sample_size=sample_size,
            seed=args.seed,
        )
    except Exception as exc:
        print(f"Error during preprocessing: {exc}", file=sys.stderr)
        return 1

    saved = preprocessor.save_processed(
        dataset=dataset,
        output_dir=processed_dir,
        file_prefix=f"clean_records_{len(dataset.records)}",
    )

    print("\n=== Preprocessing Complete ===")
    print(f"Raw rows read: {dataset.metadata['raw_total_rows']:,}")
    print(f"Dropped outliers (e.g. negative blood glucose): {dataset.metadata['dropped_outliers']}")
    print(f"Clean valid rows: {dataset.metadata['valid_clean_rows']:,}")
    print(f"Final sampled records: {dataset.metadata['sample_size']:,}")
    print(f"\nArtifacts saved to {processed_dir}:")
    print(f" - Records: {saved['records_path'].name}")
    print(f" - Cohort Aggregates: {saved['aggregates_path'].name}")
    print(f" - Metadata: {saved['metadata_path'].name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
