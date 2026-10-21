# Local Privacy-Based Healthcare Intelligence System

A local-first healthcare assistant built as a final-year Computer Engineering project. It combines a **React + TypeScript web interface**, a **FastAPI backend**, a **SQLite database** for local accounts and conversations, and a **Retrieval-Augmented Generation (RAG)** pipeline that uses a locally running Ollama model.

The goal is to help users understand general health information and their own uploaded medical documents while keeping application processing on the user's machine. This is an educational prototype, not a replacement for a qualified healthcare professional.

## Contents

- [Highlights](#highlights)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Requirements](#requirements)
- [Setup](#setup)
- [Run the Application](#run-the-application)
- [Configuration](#configuration)
- [Privacy and Safety](#privacy-and-safety)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Limitations](#limitations)

## Highlights

- **Local AI inference:** connects to Ollama through the loopback address `127.0.0.1`; the default model is `qwen2.5:3b`.
- **Evidence-based answers:** retrieves relevant context from the healthcare RAG pipeline and can include information extracted from uploaded PDF documents.
- **PDF support:** upload and manage documents associated with a conversation; document retrieval and page-level source details help users trace document-based answers.
- **Accounts and saved conversations:** local registration/login, persistent chat history, and conversation actions such as renaming, pinning, and deleting.
- **Conversation-scoped documents:** documents are associated with a user's conversation rather than being treated as one shared chat context.
- **Medical safety cues:** input validation, urgent-symptom warnings, and a medical disclaimer are included in the response flow.
- **Local storage:** SQLite stores account and conversation data; application data and uploaded documents are stored locally.
- **Web interface:** responsive chat experience built with React, TypeScript, Vite, and Tailwind CSS.

## Architecture

```text
┌─────────────────────────────────────────────┐
│ Browser UI                                  │
│ React + TypeScript + Vite                   │
│ Login/register, chat, history, PDF controls │
└──────────────────────┬──────────────────────┘
                       │ HTTP (loopback)
                       ▼
┌─────────────────────────────────────────────┐
│ FastAPI backend                             │
│ Authentication, conversations, documents,  │
│ request validation and chat API             │
└──────────────┬─────────────────┬────────────┘
               │                 │
               ▼                 ▼
┌────────────────────────┐  ┌──────────────────┐
│ Local SQLite database  │  │ Healthcare RAG   │
│ Users, sessions, chats,│  │ retrieval, PDF   │
│ messages and metadata  │  │ evidence, safety │
└────────────────────────┘  └─────────┬────────┘
                                      │
                                      ▼
                           ┌────────────────────┐
                           │ Local Ollama model │
                           │ qwen2.5:3b default │
                           └────────────────────┘
```

### Request flow

1. The user signs in and opens or creates a conversation.
2. The React interface sends a request to the local FastAPI service.
3. The backend validates the request and obtains relevant evidence from the healthcare retrieval pipeline and, when selected or relevant, the conversation's uploaded documents.
4. The local Ollama model generates a response using the supplied context.
5. The interface displays the answer, safety notices, and available source information. Conversation data is persisted in the local SQLite database.

## Technology Stack

| Layer | Technology | Responsibility |
|---|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS | Chat interface, account screens, conversation history and document controls |
| Backend API | Python, FastAPI, Pydantic | API endpoints, validation, authentication and application orchestration |
| Database | SQLite | Local users, sessions, conversations, messages, documents and document chunks |
| LLM runtime | Ollama | Runs the language model locally; default model: `qwen2.5:3b` |
| Embeddings | Sentence Transformers | Text embeddings; configured model: `sentence-transformers/all-MiniLM-L6-v2` |
| Document processing | PyMuPDF | Extracts text and page information from PDF files |
| Data/retrieval utilities | NumPy, pandas and project RAG modules | Local data processing and evidence retrieval |
| Frontend testing | Vitest, Testing Library | Frontend unit/component tests |
| Python testing | unittest-based tests in the repository | Backend and retrieval behavior tests |

## Requirements

- Python 3.9 or newer.
- Node.js and npm (use a current LTS release).
- Ollama installed locally.
- Sufficient disk space and memory for the selected local model and embedding model.
- macOS, Linux, or another environment compatible with the dependencies. Apple Silicon acceleration may be available on supported Macs.

## Setup

Run commands from the repository root.

### 1. Clone the repository and select the project branch

```bash
git clone https://github.com/Saad08-BE/local-healthcare-ai-assistant.git
cd local-healthcare-ai-assistant
git checkout feat/conversation-actions-menu
```

### 2. Create a Python virtual environment

**macOS/Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Install the Python dependencies declared by the repository:

```bash
pip install -r requirements.txt
pip install fastapi uvicorn python-multipart
```

If your checkout includes additional backend dependency instructions, follow those as well. Keep the virtual environment activated when running the backend.

### 3. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 4. Install and prepare Ollama

Install Ollama using the instructions on [the official Ollama website](https://ollama.com/), start the local Ollama service, then download the default model:

```bash
ollama pull qwen2.5:3b
```

The configured embedding model is `sentence-transformers/all-MiniLM-L6-v2`. It may need to be downloaded the first time it is initialized; prepare model files before an offline demonstration if needed.

## Run the Application

Open **two terminal windows** from the repository root.

### Terminal 1 — Start the FastAPI backend

Activate the virtual environment if it is not already active, then run:

```bash
source .venv/bin/activate
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

The API is available locally at `http://127.0.0.1:8000`. Interactive API documentation is available at `http://127.0.0.1:8000/api/docs`.

### Terminal 2 — Start the React frontend

```bash
cd frontend
npm run dev
```

Open the local URL printed by Vite (normally `http://127.0.0.1:5173`). Register a local account or sign in, then create a conversation to begin.

To create a production frontend build:

```bash
cd frontend
npm run build
```

## Configuration

The repository includes an `.env.example` file documenting local model and retrieval settings. Copy it to `.env` if you want to maintain local overrides, and review the settings before starting the application.

| Setting | Default | Purpose |
|---|---|---|
| `HEALTHCARE_OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Local Ollama service address |
| `HEALTHCARE_LLM_MODEL` | `qwen2.5:3b` | Chat model used by the RAG pipeline |
| `HEALTHCARE_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Text embedding model |
| `HEALTHCARE_CHUNK_SIZE` | `600` | Target text chunk size for document retrieval |
| `HEALTHCARE_CHUNK_OVERLAP` | `100` | Overlap between adjacent text chunks |
| `HEALTHCARE_TOP_K` | `5` | Number of top retrieval results to consider |
| `HEALTHCARE_SIMILARITY_THRESHOLD` | `0.35` | Retrieval similarity threshold |
| `HEALTHCARE_HOST` | `127.0.0.1` | Configured local host |
| `HEALTHCARE_PORT` | `8501` | Legacy/configuration setting; the React/FastAPI development run commands above use ports 5173 and 8000 respectively |
| `HEALTHCARE_DEBUG` | `false` | Debug setting |

The frontend API base defaults to `http://127.0.0.1:8000`; it can be overridden with `VITE_API_BASE_URL` in the frontend environment.

## Privacy and Safety

- The intended application flow uses local services: the browser UI, FastAPI backend, SQLite database, Ollama inference and local document processing.
- The backend is configured for loopback access in the provided development commands. Do not expose it to a public network without a separate security review.
- Do not commit medical PDFs, real patient records, credentials, local databases, or secret environment files to Git.
- Local processing does not automatically mean every dependency is offline from the first run: package installation and model downloads may require internet access. For an offline demo, download and verify required packages and model files in advance.
- Generated answers can be incomplete or incorrect. Source retrieval and disclaimers reduce risk but do not guarantee medical accuracy.
- This project is an academic prototype, not a diagnostic device or a substitute for professional medical advice. For emergencies, contact local emergency services or seek urgent medical care.

## Testing

Run the checks available in the frontend:

```bash
cd frontend
npm test
npm run lint
npm run build
```

For Python tests, activate the virtual environment at the repository root and run:

```bash
python -m unittest discover -v
```

A test command can expose environment-dependent failures if optional models or services are unavailable. Start Ollama when running tests that explicitly require a live local model.

## Project Structure

```text
.
├── backend/
│   ├── main.py                  # FastAPI application and chat endpoint
│   ├── auth.py                  # Local registration and session handling
│   ├── database.py              # SQLite schema and connection helpers
│   ├── conversations.py         # Conversation API
│   └── conversation_documents.py # Conversation-specific document API
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main React application
│   │   ├── api.ts               # Frontend API client
│   │   └── types.ts             # Shared frontend types
│   ├── package.json
│   └── vite.config.ts
├── app/                         # Shared local RAG, model and configuration modules
├── data/                        # Local runtime data; do not commit private records
├── tests/                       # Automated tests
├── .env.example                 # Example local configuration
├── pyproject.toml
└── requirements.txt
```

## Limitations

- Response quality depends on the retrieved evidence, the selected model, and the quality of uploaded PDF text.
- Scanned/image-only PDFs may require OCR support, which may not be available in every setup.
- First-time setup can require internet access to install packages and retrieve model files.
- The application is intended for local development and academic evaluation. Review authentication, session handling, file validation, and deployment settings before any use beyond a trusted local machine.

## Academic Project

**Project:** Local Privacy-Based Healthcare Intelligence System  
**Repository:** [Saad08-BE/local-healthcare-ai-assistant](https://github.com/Saad08-BE/local-healthcare-ai-assistant)  
**Target branch for this version:** `feat/conversation-actions-menu`

