#!/usr/bin/env python3
"""CLI utility to extract, chunk, and index local PDF documents."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.config.settings import AppSettings
from app.ingestion.pdf_ingestor import PDFIngestor
from app.retrieval.document_retriever import DocumentRetriever


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest local PDF documents into the document vector index.")
    parser.add_argument("--file", type=str, default=None, help="Path to single PDF file to ingest")
    parser.add_argument("--dir", type=str, default=None, help="Directory containing PDF files (default: data/documents/)")
    args = parser.parse_args()

    settings = AppSettings.from_environment()
    settings.paths.create_runtime_directories()

    docs_dir = Path(args.dir) if args.dir else settings.paths.documents_dir
    vector_store_dir = settings.paths.vector_store_dir

    print("=== Starting Local Medical Document Ingestion ===")
    ingestor = PDFIngestor(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    if args.file:
        target_file = Path(args.file)
        if not target_file.exists():
            print(f"Error: File '{target_file}' does not exist.", file=sys.stderr)
            return 1
        print(f"Ingesting single file: {target_file.name}")
        chunks = ingestor.process_file(target_file)
    else:
        print(f"Scanning directory: {docs_dir}")
        chunks = ingestor.process_directory(docs_dir)

    if not chunks:
        print("No valid PDF chunks were extracted. Ensure valid PDFs exist in data/documents/.", file=sys.stderr)
        return 1

    print(f"Extracted {len(chunks)} citation-aware chunks from local documents.")
    print("Building document vector index...")

    start_time = time.time()
    retriever = DocumentRetriever(embedding_model=None)
    saved = retriever.index_chunks(chunks=chunks, vector_store_dir=vector_store_dir)

    print(f"\nDocument indexing completed in {time.time() - start_time:.2f} seconds.")
    print(f"Artifacts saved in {vector_store_dir}:")
    print(f" - Vectors: {saved['vectors_path'].name}")
    print(f" - Metadata: {saved['metadata_path'].name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
