#!/usr/bin/env python3
"""Build local vector index for ChatDoctor-HealthCareMagic consultations."""

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
    parser = argparse.ArgumentParser(description="Index ChatDoctor consultations.")
    parser.add_argument("--batch-size", type=int, default=256, help="Batch size (default: 256)")
    args = parser.parse_args()

    processed_file = project_root / "data" / "processed" / "clean_chatdoctor_10000.jsonl"
    vector_store_dir = project_root / "vector_store"

    if not processed_file.exists():
        print(f"Error: {processed_file} not found. Run scripts/preprocess_chatdoctor.py first.", file=sys.stderr)
        return 1

    print("=== Building Local ChatDoctor Vector Index ===")
    print(f"Input records: {processed_file.name}")
    print(f"Output vector store: {vector_store_dir}")

    texts: list[str] = []
    metadatas: list[dict] = []
    record_ids: list[int] = []

    with open(processed_file, mode="r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            doc = json.loads(line)
            record_ids.append(doc["record_id"])
            texts.append(doc["semantic_text"])
            metadatas.append({
                "record_id": doc["record_id"],
                "source": "ChatDoctor-HealthCareMagic",
                "patient_query": doc["patient_query"][:300],
                "doctor_advice": doc["doctor_advice"][:500],
            })

    total = len(texts)
    print(f"Loaded {total:,} doctor-patient consultations to index.")

    emb_model = get_embedding_model()
    print(f"Embedding model: {emb_model.__class__.__name__} (Dimension: {emb_model.dimension})")

    start_time = time.time()
    vector_store = LocalVectorStore(dimension=emb_model.dimension)

    for i in range(0, total, args.batch_size):
        b_texts = texts[i : i + args.batch_size]
        b_meta = metadatas[i : i + args.batch_size]
        b_ids = record_ids[i : i + args.batch_size]

        b_embeddings = emb_model.embed_batch(b_texts)
        vector_store.add(
            embeddings=b_embeddings,
            texts=b_texts,
            metadatas=b_meta,
            record_ids=b_ids,
        )
        print(f"Indexed {min(i + args.batch_size, total):,} / {total:,} records...", end="\r")

    print(f"\nCompleted embedding in {time.time() - start_time:.2f} seconds.")

    saved = vector_store.save(vector_store_dir, base_name="chatdoctor_index")
    print("Index successfully saved:")
    print(f" - Vectors: {saved['vectors_path'].name} ({saved['vectors_path'].stat().st_size / (1024*1024):.2f} MB)")
    print(f" - Metadata: {saved['metadata_path'].name} ({saved['metadata_path'].stat().st_size / (1024*1024):.2f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
