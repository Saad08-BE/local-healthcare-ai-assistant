# PROJECT_INSTRUCTIONS.md — Local Privacy-Based Healthcare Intelligence System

**Read this file first in every session.** This project is being developed in Antigravity (Google DeepMind agentic environment) running directly on the local macOS machine with full filesystem and terminal access.

You (Antigravity) are acting as lead software architect, senior Python engineer, AI/RAG engineer, testing engineer, and project mentor for a final-year Computer Engineering project:

**Local Privacy-Based Healthcare Intelligence System** — a modular, academically defensible, privacy-first healthcare RAG application.

---

## 0. HOW SESSIONS WORK IN ANTIGRAVITY

Antigravity operates directly in the project workspace on macOS (`/Users/saad/Documents/major-project/local privacy-based health care intelligence system`). Unlike web chat sandboxes:
- All file edits, logs, and artifacts persist directly on the local filesystem.
- Git commits are made directly in the local repository.
- Tests and Python scripts run locally in the macOS terminal environment.

**Workflow at the start of a session / task:**
1. Check `docs/PROGRESS.md` to see the current phase and next step.
2. Inspect `git status` and run tests (`python3 -m unittest discover -v`) to confirm working baseline.
3. Proceed phase by phase according to §27.

**Workflow after completing each phase / checkpoint:**
1. Ensure code is clean, modular, and error-handled.
2. Run automated test suite (`python3 -m unittest discover -v`).
3. Update `docs/PROGRESS.md` with exact status, decisions, and metrics.
4. Create a clean git commit with a meaningful message (`git commit -m "..."`).
5. Report to the user following the exact format in §30.

---

## 1. PROJECT OBJECTIVE

The system must allow a user to:
1. Enter healthcare questions or symptoms through a web interface.
2. Upload PDF healthcare reports/documents locally.
3. Search relevant information from the supplied dataset and locally indexed documents.
4. Retrieve relevant evidence.
5. Use a local LLM (via local Ollama) to generate a grounded response.
6. Display sources/evidence with the answer.
7. Keep all healthcare/user data and processing on the user's computer.

**Mandatory**: no OpenAI/cloud LLM API, no cloud embeddings, no external database, no patient-record-search feature, nothing leaves the machine.

---

## 2. HARDWARE CONSTRAINT

Target: **MacBook Air M1, 8 GB RAM.** Prefer lightweight, CPU/Metal-friendly, non-CUDA tooling. Never trade away privacy for model quality.

---

## 3. DATASET

`data/raw/Indian_healthcare.csv`, 100k rows, 19 columns: Patient_ID, Age, Gender, Region, Socioeconomic_Status, Occupation, Visit_Date, Symptoms, Primary_Diagnosis, Blood_Glucose_mg_dL, HbA1c_%, Total_Cholesterol_mg_dL, Treatment_Type, Treatment_Outcome, Imaging_Type, Imaging_Findings, Hospital_Type, Insurance_Covered, BMI.

**Rules for dataset handling:**
- Inspect actual schema/types, check missing values/duplicates/malformed data.
- Decide structured vs. semantic fields, build reproducible preprocessing.
- **Never modify the original CSV** (`data/raw/Indian_healthcare.csv`) — always write processed copies to `data/processed/`.
- Never assume a field exists or behaves a certain way without checking.

---

## 4. HEALTHCARE CAPABILITIES & BOUNDARIES

- **Symptoms → possible conditions**: evidence-based associations only, never a diagnosis, always disclaim.
- **Medicine/treatment info**: only if evidence-backed from dataset/documents, never invented, always disclaimed.
- **Hospital info**: only real dataset/document entries, never fabricated.
- **Insufficient evidence**: say so explicitly.
- **Patient Privacy**: Patient_ID is excluded from LLM prompts and search indices; no individual patient lookups.

---

## 5. CORE ARCHITECTURE

```
Web UI → Query Processing → Intent Analysis → Hybrid Retrieval
  (Structured Dataset / Semantic Vector / Local Uploaded-Doc)
  → Context Assembly/Reranking → Local LLM (Ollama)
  → Grounded Response + Sources + Safety Disclaimer
```

Structured metadata, clinical text, and uploaded-document content are stored and indexed separately.

---

## 6. LOCAL-ONLY PRIVACY (non-negotiable)

No OpenAI/Gemini/Anthropic APIs, no cloud LLM inference, no cloud embeddings/vector DB, no external patient-data APIs, no remote storage. Everything must validate loopback-only endpoints (`localhost` / `127.0.0.1`).

---

## 7–10. STACK / LLM / EMBEDDINGS / DOCUMENT REPRESENTATION

- **UI**: Streamlit (local).
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions), local execution.
- **LLM**: Local Ollama running `qwen2.5:3b` or similar 3B-class quantized instruct model for M1 8GB.
- **Vector Index**: Lightweight local disk-persisted NumPy / FAISS cosine index.
- **PDF Extraction**: PyMuPDF (`fitz`), local extraction with page numbers.
- **Data processing**: Pandas / NumPy / SQLite.
- **Fail Gracefully**: If Ollama or models are offline, retrieval and source display must still function.

---

## 11. PDF/DOCUMENT INGESTION

`PDF → local extraction → cleaning → chunking → metadata → local embeddings → local index → retrieval`.
Metadata: filename, page, doc ID. Handle empty/corrupted/image-only/oversized PDFs gracefully.

---

## 12–14. RETRIEVAL / QUERY PROCESSING / CONTEXT

Modular retrieval (semantic, keyword, structured, hybrid). Context assembly: dedupe, rank, cap size, label sources clearly, separate dataset vs. document evidence, stay practical on 8GB RAM.

---

## 15–16. LLM PROMPTING & SAFETY

Instruct the local LLM to ground in evidence, flag uncertainty, never invent medications/treatments/hospitals, cite sources, recommend professional evaluation, recognize urgency, and say "insufficient evidence" rather than guess.

---

## 17–18. WEB UI

Clean, modern, demo-ready Streamlit interface with chat, document upload, sources panel, system status, and persistent healthcare disclaimers.

---

## 19. PROJECT STRUCTURE

```text
local privacy-based health care intelligence system/
├── app/
│   ├── config/       # Settings & path policies
│   ├── safety/       # Safety filters & triage
│   ├── llm/          # Local Ollama adapter
│   ├── retrieval/    # Hybrid search & indices
│   ├── ingestion/    # PDF & dataset ingestion
│   ├── ui/           # Streamlit UI
│   └── utils/        # Privacy logging & helpers
├── data/
│   ├── raw/          # Original dataset (read-only)
│   ├── processed/    # Processed datasets & summaries
│   └── documents/    # User-uploaded PDFs
├── vector_store/     # Local vector indexes
├── models/           # Local model weights / metadata
├── tests/            # Automated test suite
├── docs/             # Architecture, progress, and viva docs
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## 20–26. CONFIG, LOGGING, TESTING & EVALUATION

- Log operational events only; never log raw private medical content or patient details.
- Unit and integration tests for every module.
- Realistic benchmarks on M1 Mac (memory, latency, grounding). Never fabricate numbers.

---

## 27. DEVELOPMENT PHASES

| Phase | Focus | Status |
|---|---|---|
| 0 | Repository & dataset inspection | COMPLETE |
| 1 | Architecture & project foundation | COMPLETE |
| 2 | Dataset analysis & preprocessing | COMPLETE |
| 3 | Local retrieval & indexing | COMPLETE |
| 4 | Local LLM integration (Ollama) | COMPLETE |
| 5 | PDF/document ingestion | COMPLETE |
| 6 | Complete RAG pipeline | COMPLETE |
| 7 | Web UI (Streamlit) | COMPLETE |
| 8 | Safety, validation, logging, robustness | COMPLETE |
| 9 | Testing & evaluation | COMPLETE |
| 10 | Academic & viva documentation | COMPLETE |

One phase at a time. Conclude each phase with tests, git commit, and report (§30).

---

## 28. `docs/PROGRESS.md` STRUCTURE

Keep `docs/PROGRESS.md` updated with:
- Current Phase & Phase Status
- Completed Phases
- Current Work & Next Step
- Important Decisions
- Files Added / Modified
- Tests Run & Results
- Known Issues & Environment

---

## 29. GIT CHECKPOINTS

Commit after each phase with meaningful messages (`setup project structure`, `complete dataset preprocessing`, etc.).

---

## 30. COMMUNICATION PROTOCOL

After every phase/checkpoint, report:
```markdown
### Progress (Phase / Status)
### What was completed
### Files changed
### Architecture/technical decision
### Testing (what + result)
### Current limitations
### Next
```

---

## 31–35. CORE RULES & ETHICS

- Local-only execution.
- Educational / research project; not a certified diagnostic device.
- Never output dangerous self-treatment instructions or bypass emergency triage.
