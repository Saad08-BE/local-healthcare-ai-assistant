#!/usr/bin/env python3
"""CLI utility to build and persist the local vector index from processed records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.embeddings.local_embedding import get_embedding_model
from app.retrieval.vector_store import LocalVectorStore


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build local vector index from processed healthcare JSONL."
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Path to clean_records JSONL file (defaults to data/processed/clean_records_10000.jsonl)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=256,
        help="Batch size for embedding generation (default: 256)",
    )
    args = parser.parse_args()

    processed_dir = project_root / "data" / "processed"
    vector_store_dir = project_root / "vector_store"

    if args.input:
        input_file = Path(args.input)
    else:
        candidates = list(processed_dir.glob("clean_records_*.jsonl"))
        if not candidates:
            print(f"Error: No processed records found in {processed_dir}. Run scripts/preprocess_dataset.py first.", file=sys.stderr)
            return 1
        input_file = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]

    print("=== Building Local Healthcare Vector Index ===")
    print(f"Input records: {input_file.name}")
    print(f"Output vector store: {vector_store_dir}")

    # Read records
    texts: list[str] = []
    metadatas: list[dict] = []
    record_ids: list[int] = []

    with open(input_file, mode="r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            doc = json.loads(line)
            record_ids.append(doc["record_id"])
            texts.append(doc["semantic_text"])
            # Keep structured metadata for hybrid filtering (Patient_ID is already excluded)
            meta = {
                "record_id": doc["record_id"],
                "age": doc["age"],
                "gender": doc["gender"],
                "region": doc["region"],
                "symptoms": doc["symptoms"],
                "primary_diagnosis": doc["primary_diagnosis"],
                "treatment_type": doc["treatment_type"],
                "treatment_outcome": doc["treatment_outcome"],
                "hospital_type": doc["hospital_type"],
                "bmi": doc["bmi"],
                "blood_glucose": doc["blood_glucose_mg_dl"],
                "hba1c": doc["hba1c_pct"],
            }
            metadatas.append(meta)

    total_records = len(texts)
    print(f"Loaded {total_records:,} records to index.")

    emb_model = get_embedding_model()
    print(f"Embedding model: {emb_model.__class__.__name__} (Dimension: {emb_model.dimension})")

    start_time = time.time()
    vector_store = LocalVectorStore(dimension=emb_model.dimension)

    # Process in batches
    batch_size = args.batch_size
    for i in range(0, total_records, batch_size):
        batch_texts = texts[i : i + batch_size]
        batch_meta = metadatas[i : i + batch_size]
        batch_ids = record_ids[i : i + batch_size]

        batch_embeddings = emb_model.embed_batch(batch_texts)
        vector_store.add(
            embeddings=batch_embeddings,
            texts=batch_texts,
            metadatas=batch_meta,
            record_ids=batch_ids,
        )
        print(f"Indexed {min(i + batch_size, total_records):,} / {total_records:,} records...", end="\r")

    print(f"\nCompleted embedding in {time.time() - start_time:.2f} seconds.")

    # Save to disk
    saved = vector_store.save(vector_store_dir, base_name="healthcare_index")
    print(f"Index successfully saved:")
    print(f" - Vectors: {saved['vectors_path'].name} ({saved['vectors_path'].stat().st_size / (1024*1024):.2f} MB)")
    print(f" - Metadata: {saved['metadata_path'].name} ({saved['metadata_path'].stat().st_size / (1024*1024):.2f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
