# Local Privacy-Based Healthcare Intelligence System

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![Privacy: 100% Local](https://img.shields.io/badge/privacy-100%25%20Local-green.svg)]()
[![Hardware: Apple Silicon M1](https://img.shields.io/badge/hardware-MacBook%20Air%20M1%208GB-orange.svg)]()
[![Tests: 51 Passed](https://img.shields.io/badge/tests-51%20passed-brightgreen.svg)]()

A modular, privacy-first, locally-hosted **Healthcare Retrieval-Augmented Generation (RAG)** application designed for academic demonstration and final-year engineering defense. 

The system retrieves clinical evidence from both structured healthcare records, real doctor–patient consultations, and user-uploaded medical PDF documents, then synthesizes grounded responses using a **local LLM (via Ollama on Apple Silicon Metal)**.

> [!IMPORTANT]
> **Privacy Guarantee**: All healthcare data, patient records, vector embeddings, uploaded PDFs, query logs, and LLM inference run **100% locally on your computer**. Zero cloud APIs, zero external databases, and zero data leakage.

---

## 🏗️ System Architecture

```text
                                  USER QUERY
                                      │
                                      ▼
                     ┌──────────────────────────────────┐
                     │ 1. Safety Triage & Validation    │
                     │  • Empty/malformed checks        │
                     │  • Privacy guard (blocks ID lookups)
                     │  • Emergency red-flag detection  │
                     └────────────────┬─────────────────┘
                                      │
                                      ▼
                     ┌──────────────────────────────────┐
                     │ 2. Multi-Source Hybrid Retriever │
                     └───────┬───────────────┬──────────┘
                             │               │
        ┌────────────────────┴───┐       ┌───┴────────────────────────┐
        ▼                        ▼       ▼                            ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────────────┐
│ Statistical   │ │ Clinical Case │ │ Doctor Q&A    │ │ Uploaded Medical PDFs │
│ Cohort Probs  │ │ Vectors       │ │ Consultations │ │ (PyMuPDF Chunk Index) │
│ (Precomputed) │ │ (10k Sample)  │ │ (ChatDoctor)  │ │ (Page Citations)      │
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘ └───────────┬───────────┘
        │                 │                 │                     │
        └─────────────────┼─────────────────┼─────────────────────┘
                          │                 │
                          ▼                 ▼
                     ┌──────────────────────────────────┐
                     │ 3. Context Formatter & Grounding │
                     │  • Formats evidence blocks       │
                     │  • Embeds page citations         │
                     │  • Injects anti-hallucination rules
                     └────────────────┬─────────────────┘
                                      │
                                      ▼
                     ┌──────────────────────────────────┐
                     │ 4. Local LLM (Ollama 3B on Metal)│
                     │  • Strict evidence synthesis     │
                     │  • Offline fallback degradation  │
                     │  • Medical disclaimer attachment │
                     └────────────────┬─────────────────┘
                                      │
                                      ▼
                            GROUNDED RESPONSE + SOURCES
```

---

## 📊 Phase-by-Phase Roadmap & Current Status

| Phase | Milestone | Status | Key Deliverables |
|---|---|---|---|
| **Phase 0** | Repository & Requirements Inspection | ✅ **COMPLETE** | Workspace initialization, environment validation, data safety protocols. |
| **Phase 1** | Architecture & Foundation | ✅ **COMPLETE** | Local path policy, loopback endpoint validation, safety filters, initial test scaffold. |
| **Phase 2** | Dataset Analysis & Preprocessing | ✅ **COMPLETE** | Profiled 100k raw rows, filtered 81 outliers, privacy stripping of `Patient_ID`, stratified 10k sampling, cohort aggregations. |
| **Phase 3** | Local Retrieval & Vector Indexing | ✅ **COMPLETE** | 384-d normalized dense embeddings, custom disk-persisted vector store ($<50$ MB), $<5$ ms cosine similarity search. |
| **Phase 4** | Local LLM Integration (Ollama 3B) | ✅ **COMPLETE** | Ollama adapter on Apple Silicon Metal, strict grounding prompts, graceful offline degradation, CLI query tool. |
| **Phase 5** | PDF & Document Ingestion | ✅ **COMPLETE** | Local PyMuPDF extractor, sentence-aware sliding window chunker, document vector index, page-level citations. |
| **Phase 6** | **Unified Complete Hybrid RAG Pipeline** | ✅ **COMPLETE** | Dataset, ChatDoctor, and PDF evidence are retrieved in one grounded query loop. |
| **Phase 7** | **Streamlit Web User Interface** | ✅ **COMPLETE** | Local chat UI with history, PDF upload, source inspector, status, and settings. |
| **Phase 8** | **Safety, Logging & System Robustness** | ✅ **COMPLETE** | Input validation, privacy-preserving logging, and safety triage are covered. |
| **Phase 9** | **Testing, Benchmarking & Evaluation** | ✅ **COMPLETE** | Unit/integration coverage and local benchmark tooling are included. |
| **Phase 10**| **Academic & Viva Defense Documentation**| ✅ **COMPLETE** | Architecture, evaluation, progress, and viva-defense documents are included. |

---

## 🛠️ Summary of Completed Work (Phases 0 to 10)

### 1. Dual Dataset Ingestion & Preprocessing (Phase 2 & Dataset Update)
- **`Indian_healthcare.csv`**: Analyzed 100,000 tabular hospital records, removed 81 non-physiological outliers (negative glucose), removed all `Patient_ID` fields for privacy, generated a 10,000-record stratified sample, and computed cohort statistical distributions (`data/processed/cohort_aggregates.json`).
- **`ChatDoctor-HealthCareMagic-100k.csv`**: Cleaned and indexed 10,000 real doctor–patient consultations (`data/processed/clean_chatdoctor_10000.jsonl`) for natural clinical Q&A and practical home care guidance.

### 2. Local Embedding Layer & Vector Store (Phase 3)
- **Local Embeddings**: 384-dimensional dense vectors with zero-dependency offline deterministic normalized vector engine + `sentence-transformers` compatibility.
- **Disk-Persisted Vector Store**: Custom NumPy/JSON local vector store in `vector_store/` using normalized cosine similarity dot-products and binary heap top-$k$ selection. Takes $<50$ MB RAM and searches 10,000 records in $<5$ ms.

### 3. Local LLM Integration & Medical Grounding (Phase 4)
- **Ollama Adapter**: Connects strictly to loopback (`http://127.0.0.1:11434`) using `qwen2.5:3b` with Apple Silicon GPU/Metal acceleration.
- **Medical Grounding Prompt**: Instructs LLM to rely strictly on retrieved evidence, declare "insufficient evidence" for ungrounded queries, never fabricate medications/dosages, and append healthcare disclaimers.
- **Graceful Degradation**: If Ollama is offline, the system never crashes—it displays structured evidence directly in $<0.2$s.

### 4. Local PDF Ingestion & Document Retrieval (Phase 5)
- **PyMuPDF Document Ingestor**: Extracts text page-by-page from PDFs in `data/documents/` with error handling for corrupted/empty files.
- **Sentence-Aware Chunker**: Splits pages into 600-character chunks with 100-character overlap while keeping sentences intact.
- **Page-Level Citations**: Every retrieved document chunk carries exact page metadata (e.g. `Clinical_Guidelines.pdf (Page 2)`).

---

## 💻 Hardware Budget (Optimized for MacBook Air M1, 8GB RAM)

| Component | RAM Footprint | Execution Method |
|---|---|---|
| **macOS Base Baseline** | ~3.5 – 4.0 GB | System OS |
| **Local LLM (`qwen2.5:3b` Q4)** | ~2.0 – 2.2 GB | Apple Metal (GPU/Neural Engine) via Ollama |
| **Local Vector Stores (All 3 Indices)**| **~60 – 80 MB** | Disk-persisted in-memory arrays |
| **Embedding Engine & Python App** | ~150 – 200 MB | Local Python Process |
| **Total Memory Usage** | **~6.2 – 6.6 GB / 8 GB** | **Zero swap thrashing, ultra-smooth local execution** |

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- macOS (Apple Silicon M1/M2/M3 or Intel)
- Python 3.9+
- [Ollama](https://ollama.com) (for local LLM inference)

### 2. Installation
Clone the repository and enter the directory:
```bash
cd "local privacy-based health care intelligence system"
```

Create a virtual environment (optional but recommended):
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run Automated Tests
Verify all unit and integration tests pass:
```bash
python3 -m unittest discover -v
```

### 4. Start Local Ollama (Optional for Natural Language AI Synthesis)
In one terminal tab, start the local Ollama server:
```bash
ollama serve
```

In a second terminal tab, download the 3B model (done once):
```bash
ollama pull qwen2.5:3b
```

### 5. Ask a Healthcare Question (CLI Tool)
```bash
python3 scripts/ask_question.py "What conditions and supportive care are associated with fever and cough?"
```

### 6. Ingest Your Own Medical PDFs
Place any medical report or guideline PDF into `data/documents/`, then run:
```bash
python3 scripts/ingest_documents.py
```

### 7. Launch the Web Interface
```bash
streamlit run app/main.py
```

The included Streamlit configuration binds the interface to `127.0.0.1` only.

---

## 📁 Repository Structure

```text
local privacy-based health care intelligence system/
├── app/
│   ├── config/          # Validated runtime settings & local path policies
│   ├── embeddings/      # Local 384-d dense embedding adapters
│   ├── ingestion/       # PDF chunker & dataset preprocessing pipelines
│   ├── llm/             # Ollama client, grounding prompts, & RAG pipeline
│   ├── retrieval/       # Local vector store & hybrid search engines
│   ├── safety/          # Triage, emergency filters, & disclaimers
│   └── ui/              # Streamlit local web interface
├── data/
│   ├── raw/             # Original datasets (read-only, git-ignored)
│   ├── processed/       # Cleaned JSONL samples & cohort aggregations
│   └── documents/       # Local user-uploaded PDF medical documents
├── vector_store/        # Local disk-persisted vector indices
├── scripts/
│   ├── ask_question.py          # Interactive CLI query tool
│   ├── build_index.py           # Dataset index builder
│   ├── build_chatdoctor_index.py # ChatDoctor index builder
│   ├── ingest_documents.py      # PDF document batch indexer
│   ├── preprocess_dataset.py    # Dataset cleaning & sampling CLI
│   ├── preprocess_chatdoctor.py # ChatDoctor cleaning CLI
│   └── profile_dataset.py       # Zero-dependency dataset profiler
├── tests/               # Automated unit & integration tests
├── docs/                # Architecture, profiling, and progress reports
├── requirements.txt     # Lightweight non-CUDA dependencies
└── README.md            # Master project documentation
```

---

## ⚖️ Ethical & Healthcare Disclaimers

This system is an **educational and academic research project** and is **not a certified diagnostic device**. 
- It does not replace consultation with a qualified medical professional.
- It intentionally restricts patient record lookups to safeguard privacy.
- For emergency or acute symptoms, users must seek immediate emergency medical care.
