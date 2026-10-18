# React + FastAPI local migration

This migration adds a new React/TypeScript frontend and a FastAPI adapter while retaining the existing Streamlit entry point. It is a development foundation, not a claim of production certification. Run the checks below before relying on the new interface.

## Architecture

- `frontend/`: React, TypeScript, Vite, Tailwind CSS v4, React Markdown, and Lucide icons.
- `backend/main.py`: FastAPI endpoints bound to the local machine when started with the command below.
- `app/llm/rag_pipeline.py`: existing safety triage, retrieval, grounding, Ollama call, and evidence fallback; reused rather than reimplemented.
- `app/ui/input_controls.py`: existing local PDF ingestion, listing, and deletion helpers; reused by the API.
- `data/`, `vector_store/`, `logs/`: existing project-local runtime data; do not commit these folders or medical PDFs.

The API allows CORS only from the local Vite development origins and should be started on `127.0.0.1`, not `0.0.0.0`. Do not expose this development API to a LAN or the public internet.

## Requirements

- macOS with the existing project Python virtual environment and dataset/vector indexes prepared as before.
- Node.js 20.19+ or 22.12+ recommended for Vite 6.
- Ollama installed locally; the configured default model is `qwen2.5:3b`.
- First-time dependency installation needs package access. Model inference and the API calls remain local after dependencies/models are installed.

## Run the API

Open Terminal in the repository root:

```bash
source .venv/bin/activate
python -m pip install -r requirements-api.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Keep this terminal open. API health: http://127.0.0.1:8000/api/health. Local API docs: http://127.0.0.1:8000/api/docs.

The first successful chat request may take time while the local embedding model and vector indexes initialize. Ensure Ollama is running locally. If required, open another terminal and run `ollama serve`; if Ollama is already running, do not start a second copy.

## Run the React frontend

Open a second Terminal window:

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173. Keep both API and Vite terminals running. Copy `frontend/.env.example` to `frontend/.env.local` only if you need to override the API address; the default already points to localhost.

## Run tests and checks

API contract tests (after installing `requirements-api.txt`):

```bash
source .venv/bin/activate
python -m unittest backend.test_api -v
```

Frontend component smoke test and production build (from `frontend/`):

```bash
npm test
npm run build
npm run lint
```

These commands are instructions, not evidence that tests have already passed. Record any errors and resolve them before merging the migration.

## Important behavior and current boundaries

- Streamlit remains available via `streamlit run app/main.py` and should not be removed during this migration.
- PDF upload is capped at 20 MiB and only accepts files whose name and header indicate a PDF; extraction and indexing still use the existing local code.
- The React conversation list currently lives in browser memory and is cleared on refresh. This avoids silently persisting sensitive health questions in browser storage. Persistent encrypted/local conversation storage can be designed as a separate opt-in feature.
- The existing RAG pipeline uses non-streaming Ollama generation. The UI shows a loading state, but true token-by-token streaming and cancellation require a separate backend/LLM change.
- This is an academic healthcare information tool, not a medical device. Local-only operation does not itself guarantee security certification, regulatory compliance, or clinical correctness.
- Do not add patient-identifying data or uploaded medical PDFs to Git.
