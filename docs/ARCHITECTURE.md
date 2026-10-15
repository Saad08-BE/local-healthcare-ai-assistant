# Proposed Architecture

## Design goals

The system will run entirely on the user's computer during normal operation. It
will use the supplied healthcare CSV and user-selected PDFs as separate local
knowledge sources. It is an educational information system, not a diagnostic
or clinical decision-making device.

The design targets an Apple Silicon Mac with 8 GB RAM. Components are loaded
only when needed, indexes live on disk, and retrieval context is kept small.

## Components

```text
Streamlit local web interface
          |
          v
Query validation + intent classification + safety triage
          |
          v
Hybrid retrieval coordinator
   |                     |                         |
   v                     v                         v
Structured CSV filters   Semantic dataset index     Local PDF index
   |                     |                         |
   +---------------------+-------------------------+
                         |
                         v
Evidence ranking, de-duplication, and context limiting
                         |
                         v
Configurable local LLM adapter (Ollama only; no cloud fallback)
                         |
                         v
Grounded answer, sources, and healthcare disclaimer
```

## Planned implementation choices

| Concern | Decision | Reason |
| --- | --- | --- |
| UI | Streamlit | Simple, local, and suitable for a demonstrable final-year project. |
| Structured data | Pandas during preprocessing; SQLite for local queryable summaries if profiling justifies it | Keeps numerical and categorical filtering separate from semantic search. |
| Semantic index | Local NumPy cosine-similarity index initially | Avoids a heavyweight vector-database dependency for the expected dataset scale; can be replaced behind an interface if measurements show a need. |
| Embeddings | Configurable local `sentence-transformers` model, initially `all-MiniLM-L6-v2` | 384-dimensional, comparatively small, and CPU-compatible. Model acquisition must occur before offline use; embeddings run locally thereafter. |
| LLM | Configurable Ollama model, recommended `qwen2.5:3b-instruct-q4_K_M` or another 3B-class quantized model available locally | A practical quality/resource compromise for an 8 GB M1, with graceful failure when Ollama or the selected model is unavailable. |
| PDF extraction | PyMuPDF | Local extraction with page-level citations and good error reporting. OCR is not planned in the initial version. |
| Persistence | Project-local `data/processed/`, `data/documents/`, and `vector_store/` | Makes storage location explicit and supports local-only operation. |

## Dataset representation policy

The supplied `Indian_healthcare.csv` is present at `data/raw/` with 100,000
records and 19 columns. Phase 2 will perform a full reproducible profile
without modifying the original file. The expected approach is:

- retain IDs and exact measurements only in structured local data; do not pass
  patient identifiers to the LLM;
- make a compact, de-identified semantic summary per useful record or grouped
  cohort, after confirming actual columns and data quality;
- use numerical fields and categorical metadata for filters/aggregations rather
  than embedding arbitrary cells;
- show citations as dataset-record or aggregate evidence without exposing
  unnecessary patient-level information.

## Local privacy boundary

At runtime, user questions, PDF text, embeddings, indexes, logs, and local LLM
prompts remain on the computer. No cloud LLM, cloud embedding API, remote vector
database, or external patient-data service will be used. Package/model downloads
may require internet during setup; this will be documented separately and never
used to transmit user data.

## Resource considerations and limitations

The local LLM is the resource-intensive component and may consume several GB of
unified memory. The application will make it optional: retrieval and source
display must still work if the model is unavailable. Final model and index
choices will be validated with actual latency/memory measurements rather than
claimed in advance.

## First implementation task

Phase 1: create the Python project foundation, configuration model, dependency
manifest, local-path policy, and test scaffold. Dataset preprocessing must wait
until `Indian_healthcare.csv` is placed in `data/raw/` (or its actual location is
provided).
