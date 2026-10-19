"""Loopback-only API adapter that reuses the existing healthcare RAG pipeline."""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config.settings import AppSettings
from app.llm.ollama_client import LocalServiceUnavailable, OllamaClient
from app.llm.rag_pipeline import HealthcareRAGPipeline
from app.ui.input_controls import delete_saved_pdf, list_saved_pdfs, save_and_index_pdf
from backend.auth import _current_user, _require_csrf, router as auth_router
from backend.database import database_connection, initialize_database
from backend.conversations import router as conversations_router

logger = logging.getLogger("healthai.api")
settings = AppSettings.from_environment()
settings.paths.create_runtime_directories()
app = FastAPI(title="HealthAI Local API", description="Loopback-only API for the local privacy-first healthcare assistant.", version="0.1.0", docs_url="/api/docs", redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)
_pipeline: HealthcareRAGPipeline | None = None
_pipeline_lock = threading.Lock()
app.include_router(auth_router)
app.include_router(conversations_router)
MAX_PDF_BYTES = 20 * 1024 * 1024
MAX_QUERY_CHARS = 4000


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_QUERY_CHARS)
    model: str | None = Field(default=None, max_length=160)
    document_filename: str | None = Field(default=None, max_length=255)
    conversation_id: str | None = Field(default=None, max_length=80)


class ChatResponse(BaseModel):
    question: str
    answer: str
    model: str | None
    offline_fallback: bool
    urgent_warning: bool
    latency_seconds: float
    disclaimer: str
    document_sources: list[dict]
    retrieved_cases: list[dict]
    cohort_statistics: dict


def get_pipeline() -> HealthcareRAGPipeline:
    """Initialize expensive RAG components only when a chat request arrives."""
    global _pipeline
    if _pipeline is None:
        with _pipeline_lock:
            if _pipeline is None:
                _pipeline = HealthcareRAGPipeline.initialize(settings)
    return _pipeline


def _ollama_client() -> OllamaClient:
    return OllamaClient(base_url=settings.ollama_base_url, timeout_seconds=3.0)


def _installed_models() -> list[str]:
    try:
        return _ollama_client().list_models()
    except LocalServiceUnavailable:
        return []


@app.get("/api/health")
def health() -> dict:
    """Return status without loading the embedding model or RAG indexes."""
    ollama_online = _ollama_client().is_online()
    return {"status": "ok", "app": "HealthAI", "ollama": "online" if ollama_online else "offline", "pipeline_loaded": _pipeline is not None, "privacy_mode": "local-only"}


@app.get("/api/models")
def models() -> dict:
    installed = _installed_models()
    available = sorted(set(installed + [settings.llm_model]))
    return {"models": available, "default_model": settings.llm_model, "ollama_online": bool(installed)}


@app.get("/api/documents")
def documents() -> dict:
    return {"documents": [{"filename": path.name, "size_bytes": path.stat().st_size} for path in list_saved_pdfs(settings) if path.is_file()]}


@app.post("/api/documents", status_code=201)
def upload_document(file: UploadFile = File(...)) -> dict:
    filename = Path(file.filename or "").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF files are supported.")
    try:
        contents = file.file.read(MAX_PDF_BYTES + 1)
        if len(contents) > MAX_PDF_BYTES:
            raise HTTPException(status_code=413, detail="PDF must be 20 MB or smaller.")
        if not contents.startswith(b"%PDF-"):
            raise HTTPException(status_code=400, detail="The selected file does not look like a valid PDF.")
        saved_path, chunk_count = save_and_index_pdf(filename, contents, settings)
        return {"filename": saved_path.name, "chunks_indexed": chunk_count, "stored_locally": True}
    except HTTPException:
        raise
    except (OSError, ValueError, RuntimeError) as exc:
        logger.warning("Local PDF ingestion failed (%s).", type(exc).__name__)
        raise HTTPException(status_code=400, detail="The PDF could not be processed. Check that it is readable and try again.") from exc
    finally:
        file.file.close()


@app.delete("/api/documents/{filename}")
def remove_document(filename: str) -> dict:
    if Path(filename).name != filename or not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid PDF filename.")
    if not any(path.name == filename for path in list_saved_pdfs(settings)):
        raise HTTPException(status_code=404, detail="That PDF is not in the local document library.")
    try:
        delete_saved_pdf(filename, settings)
        return {"deleted": True, "filename": filename}
    except (OSError, ValueError, RuntimeError) as exc:
        logger.warning("Local PDF deletion failed (%s).", type(exc).__name__)
        raise HTTPException(status_code=500, detail="The PDF could not be deleted or re-indexed.") from exc


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest, http_request: Request) -> ChatResponse:
    question = request.question.strip()
    user = None
    if request.conversation_id:
        _require_csrf(http_request, http_request.headers.get("x-csrf-token"))
        user = _current_user(http_request)
        initialize_database()
        with database_connection() as connection:
            owned = connection.execute(
                "SELECT id FROM conversations WHERE id = ? AND user_id = ?",
                (request.conversation_id, user["id"]),
            ).fetchone()
        if owned is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")
    if not question:
        raise HTTPException(status_code=422, detail="Enter a question before sending.")
    model = (request.model or settings.llm_model).strip()
    if not model or len(model) > 160:
        raise HTTPException(status_code=422, detail="Choose a valid local model.")
    installed = _installed_models()
    if installed and not any(name == model or name.startswith(model + "-") for name in installed):
        raise HTTPException(status_code=400, detail="Choose a model installed in local Ollama.")
    document_filename = request.document_filename
    if document_filename and document_filename not in {"__all__", "__most_relevant__"}:
        if Path(document_filename).name != document_filename or not document_filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Invalid PDF selection.")
        if not any(path.name == document_filename for path in list_saved_pdfs(settings)):
            raise HTTPException(status_code=404, detail="The selected PDF is not saved locally.")
    try:
        result = get_pipeline().answer_question(question, model_override=model, document_filename=document_filename or "__most_relevant__")
    except Exception as exc:
        logger.exception("Local RAG request failed (%s).", type(exc).__name__)
        raise HTTPException(status_code=500, detail="HealthAI could not complete this request. Check local services and application logs.") from exc
    response = ChatResponse(
        question=result.question, answer=result.answer, model=result.llm_model,
        offline_fallback=result.is_offline_fallback, urgent_warning=result.urgent_warning,
        latency_seconds=result.total_latency_seconds, disclaimer=result.disclaimer,
        document_sources=[{"citation": item.citation, "score": item.score, "text": item.text} for item in result.document_sources],
        retrieved_cases=[{"score": item.score, "text": item.text} for item in result.retrieved_cases],
        cohort_statistics=result.cohort_statistics,
    )
    if user is not None and request.conversation_id:
        metadata = json.dumps({
            "model": result.llm_model,
            "document_sources": [{"citation": item.citation, "score": item.score, "text": item.text} for item in result.document_sources],
            "urgent_warning": result.urgent_warning,
        })
        with database_connection() as connection:
            connection.execute(
                "INSERT INTO messages(conversation_id, role, content) VALUES (?, ?, ?)",
                (request.conversation_id, "user", question),
            )
            connection.execute(
                "INSERT INTO messages(conversation_id, role, content, metadata_json) VALUES (?, ?, ?, ?)",
                (request.conversation_id, "assistant", result.answer, metadata),
            )
            connection.execute(
                """UPDATE conversations SET updated_at = CURRENT_TIMESTAMP,
                   title = CASE WHEN title = 'New chat' THEN ? ELSE title END
                   WHERE id = ? AND user_id = ?""",
                (question[:80] or "New chat", request.conversation_id, user["id"]),
            )
    return response
