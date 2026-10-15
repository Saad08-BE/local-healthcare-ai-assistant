#!/usr/bin/env python3
"""CLI utility to ask a healthcare question and run the full local RAG pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.config.settings import AppSettings
from app.llm.rag_pipeline import HealthcareRAGPipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Query the local healthcare RAG pipeline.")
    parser.add_argument("question", nargs="*", help="The healthcare question or symptom description.")
    args = parser.parse_args()

    question_text = " ".join(args.question).strip()
    if not question_text:
        question_text = input("Enter healthcare question: ").strip()

    if not question_text:
        print("Error: Empty question.", file=sys.stderr)
        return 1

    print(f"\nProcessing Query: '{question_text}'...")
    settings = AppSettings.from_environment()
    pipeline = HealthcareRAGPipeline.initialize(settings)

    response = pipeline.answer_question(question_text)

    print("\n" + "=" * 60)
    print("HEALTHCARE INTELLIGENCE RESPONSE")
    print("=" * 60)
    print(response.answer)
    print("\n" + "-" * 60)
    print(f"Latency: {response.total_latency_seconds}s | LLM: {response.llm_model or 'Direct Evidence (Offline LLM)'}")
    print(f"Retrieved Cases: {len(response.retrieved_cases)} | Urgent Flag: {response.urgent_warning}")
    print("=" * 60)
    print(f"\n{response.disclaimer}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
