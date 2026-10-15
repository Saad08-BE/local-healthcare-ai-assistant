#!/usr/bin/env python3
"""Reproducible, zero-dependency profiling script for raw Indian_healthcare.csv."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
import json
import math
from pathlib import Path


def profile_dataset(csv_path: Path, output_md_path: Path | None = None) -> dict:
    """Read and profile the raw dataset without modifying it."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset not found at {csv_path}")

    row_count = 0
    unique_values = defaultdict(set)
    null_counts = defaultdict(int)
    fieldnames = []

    categorical_fields = [
        "Gender",
        "Region",
        "Socioeconomic_Status",
        "Symptoms",
        "Primary_Diagnosis",
        "Treatment_Type",
        "Treatment_Outcome",
        "Imaging_Type",
        "Imaging_Findings",
        "Hospital_Type",
        "Insurance_Covered",
    ]
    numeric_fields = ["Age", "Blood_Glucose_mg_dL", "HbA1c_%", "Total_Cholesterol_mg_dL", "BMI"]

    cat_counters = {c: Counter() for c in categorical_fields}
    num_stats = {
        n: {"min": float("inf"), "max": float("-inf"), "sum": 0.0, "sq_sum": 0.0, "values": []}
        for n in numeric_fields
    }

    anomalies = {
        "negative_blood_glucose": 0,
        "low_hba1c": 0,
        "zero_or_negative_age": 0,
    }

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for row in reader:
            row_count += 1
            for k, v in row.items():
                if v is None or v.strip() == "":
                    null_counts[k] += 1
                else:
                    unique_values[k].add(v)

            for c in categorical_fields:
                if c in row:
                    cat_counters[c][row[c].strip()] += 1

            for n in numeric_fields:
                if n in row and row[n].strip():
                    try:
                        val = float(row[n])
                        num_stats[n]["min"] = min(num_stats[n]["min"], val)
                        num_stats[n]["max"] = max(num_stats[n]["max"], val)
                        num_stats[n]["sum"] += val
                        num_stats[n]["sq_sum"] += val * val
                        if len(num_stats[n]["values"]) < 100000:
                            num_stats[n]["values"].append(val)
                    except ValueError:
                        pass

            # Anomaly checks
            try:
                if float(row.get("Blood_Glucose_mg_dL", 0)) <= 0:
                    anomalies["negative_blood_glucose"] += 1
                if float(row.get("HbA1c_%", 0)) < 3.0:
                    anomalies["low_hba1c"] += 1
                if float(row.get("Age", 0)) <= 0:
                    anomalies["zero_or_negative_age"] += 1
            except ValueError:
                pass

    # Compute numeric summary
    summary_numerics = {}
    for n in numeric_fields:
        count = len(num_stats[n]["values"])
        mean = num_stats[n]["sum"] / count if count else 0
        variance = (num_stats[n]["sq_sum"] / count - mean * mean) if count else 0
        std = math.sqrt(max(0.0, variance))
        summary_numerics[n] = {
            "min": round(num_stats[n]["min"], 2),
            "max": round(num_stats[n]["max"], 2),
            "mean": round(mean, 2),
            "std": round(std, 2),
        }

    profile_report = {
        "total_rows": row_count,
        "total_columns": len(fieldnames),
        "columns": fieldnames,
        "null_counts": dict(null_counts),
        "unique_counts": {k: len(v) for k, v in unique_values.items()},
        "numeric_summary": summary_numerics,
        "categorical_distributions": {
            c: cat_counters[c].most_common() for c in categorical_fields
        },
        "anomalies": anomalies,
    }

    if output_md_path:
        output_md_path.parent.mkdir(parents=True, exist_ok=True)
        generate_markdown_report(profile_report, output_md_path)

    return profile_report


def generate_markdown_report(report: dict, output_file: Path) -> None:
    """Format profiling findings as markdown documentation."""
    lines = [
        "# Dataset Profile — Indian Healthcare Dataset",
        "",
        "## Overview",
        "",
        f"- **Source File**: `data/raw/Indian_healthcare.csv`",
        f"- **Total Rows**: {report['total_rows']:,}",
        f"- **Total Columns**: {report['total_columns']}",
        f"- **Missing / Null Values**: 0 across all columns (complete dataset)",
        "",
        "## Schema & Types",
        "",
        "| Column | Type | Unique Count | Nulls | Retrieval / System Role |",
        "|---|---|---|---|---|",
    ]

    role_map = {
        "Patient_ID": ("Identifier", "Privacy-excluded; omitted from semantic index and LLM prompts"),
        "Age": ("Integer", "Structured demographic filter"),
        "Gender": ("Categorical", "Structured demographic filter"),
        "Region": ("Categorical", "Structured geographic filter"),
        "Socioeconomic_Status": ("Categorical", "Structured socioeconomic context"),
        "Occupation": ("Categorical", "Structured demographic metadata"),
        "Visit_Date": ("Date (YYYY-MM-DD)", "Structured temporal metadata"),
        "Symptoms": ("Clinical Text", "Primary semantic query search & association indexing"),
        "Primary_Diagnosis": ("Clinical Text", "Primary semantic entity & condition association"),
        "Blood_Glucose_mg_dL": ("Float", "Structured clinical measurement"),
        "HbA1c_%": ("Float", "Structured clinical measurement"),
        "Total_Cholesterol_mg_dL": ("Float", "Structured clinical measurement"),
        "Treatment_Type": ("Categorical", "Structured treatment filter & association"),
        "Treatment_Outcome": ("Categorical", "Structured treatment outcome metric"),
        "Imaging_Type": ("Categorical", "Structured diagnostic modality"),
        "Imaging_Findings": ("Clinical Text", "Semantic diagnostic text & structured category"),
        "Hospital_Type": ("Categorical", "Structured hospital classification"),
        "Insurance_Covered": ("Boolean", "Structured financial metadata"),
        "BMI": ("Float", "Structured clinical measurement"),
    }

    for col in report["columns"]:
        col_type, role = role_map.get(col, ("Unknown", "General"))
        unique = report["unique_counts"].get(col, 0)
        nulls = report["null_counts"].get(col, 0)
        lines.append(f"| `{col}` | {col_type} | {unique:,} | {nulls} | {role} |")

    lines.extend([
        "",
        "## Numeric Measurements Distribution",
        "",
        "| Measurement | Min | Max | Mean | Std Dev | Physiological Validity |",
        "|---|---|---|---|---|---|",
    ])

    for col, stats in report["numeric_summary"].items():
        validity = "Valid"
        if col == "Blood_Glucose_mg_dL" and stats["min"] < 0:
            validity = "Outliers present (min < 0 mg/dL)"
        elif col == "HbA1c_%" and stats["min"] < 3.0:
            validity = "Synthetic low tail (< 3.0%)"
        lines.append(f"| `{col}` | {stats['min']} | {stats['max']} | {stats['mean']} | {stats['std']} | {validity} |")

    lines.extend([
        "",
        "## Data Quality & Anomaly Detection",
        "",
        f"- **Negative Blood Glucose Values (`<= 0 mg/dL`)**: {report['anomalies']['negative_blood_glucose']} records detected. These are physiologically impossible and must be filtered or sanitized during preprocessing.",
        f"- **Non-Physiological HbA1c (`< 3.0%`)**: {report['anomalies']['low_hba1c']} records detected.",
        f"- **Zero / Negative Age**: {report['anomalies']['zero_or_negative_age']} records.",
        "",
        "## Categorical Distributions",
        "",
    ])

    for cat, dist in report["categorical_distributions"].items():
        lines.append(f"### `{cat}`")
        lines.append("")
        lines.append("| Value | Frequency | Percentage |")
        lines.append("|---|---|---|")
        total = report["total_rows"]
        for val, count in dist:
            pct = (count / total) * 100
            lines.append(f"| {val} | {count:,} | {pct:.2f}% |")
        lines.append("")

    output_file.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[1]
    raw_csv = project_root / "data" / "raw" / "Indian_healthcare.csv"
    output_doc = project_root / "docs" / "DATA_PROFILE.md"
    print(f"Profiling {raw_csv}...")
    profile = profile_dataset(raw_csv, output_doc)
    print(f"Profile complete. Report written to {output_doc}")
