"""Authenticated PDF endpoints scoped to a single user's conversation.

These files and indexes are kept separate from the legacy Streamlit PDF library.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
import uuid
from dataclasses import replace
from pathlib import Path

from fastapi import APIRouter, File, Header, HTTPException, Request, UploadFile

from app.config.settings import AppSettings
from app.embeddings.local_embedding import get_embedding_model
from app.ingestion.pdf_ingestor import PDFIngestor, PDFExtractionError
from app.retrieval.document_retriever import DocumentRetriever
from app.retrieval.vector_store import LocalVectorStore
from backend.auth import _current_user, _require_csrf
from backend.database import database_connection, initialize_database, resolve_database_path

logger = logging.getLogger("healthai.api.documents")
router = APIRouter(prefix="/api/conversations", tags=["conversation documents"])
MAX_PDF_BYTES = 20 * 1024 * 1024


def _storage_root() -> Path:
    # Keep test databases and their files isolated, and never use Streamlit's
    # shared data/documents directory for authenticated React conversations.
    return resolve_database_path().parent / "conversation_documents"


def _ensure_private_dir(path: Path) -> None:
    """Create a local storage directory and restrict it to the current OS user."""
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        path.chmod(0o700)
    except OSError:
        # Keep the app usable on filesystems without POSIX permissions.
        pass


def _conversation_row(conversation_id: str, user_id: int) -> dict:
    initialize_database()
    with database_connection() as connection:
        row = connection.execute(
            "SELECT id, user_id FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return dict(row)


def _conversation_index_dir(user_id: int, conversation_id: str) -> Path:
    return _storage_root() / str(user_id) / conversation_id / "index"


def delete_conversation_storage(user_id: int, conversation_id: str) -> None:
    """Remove the report files and vector index when their conversation is deleted."""
    conversation_dir = _storage_root() / str(user_id) / conversation_id
    shutil.rmtree(conversation_dir, ignore_errors=True)


def _rebuild_index(
    user_id: int,
    conversation_id: str,
    *,
    exclude_document_id: str | None = None,
) -> None:
    """Build a conversation-only vector index and replace it after a successful build."""
    initialize_database()
    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, original_filename, storage_path
            FROM documents
            WHERE user_id = ? AND conversation_id = ?
            ORDER BY created_at, id
            """,
            (user_id, conversation_id),
        ).fetchall()

    rows = [row for row in rows if row["id"] != exclude_document_id]
    settings = AppSettings.from_environment()
    ingestor = PDFIngestor(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    chunks = []
    for row in rows:
        path = Path(row["storage_path"]).resolve()
        root = _storage_root().resolve()
        if root not in path.parents or not path.is_file():
            logger.warning("Skipping unavailable conversation document %s.", row["id"])
            continue
        for chunk in ingestor.process_file(path):
            # Unique document IDs avoid collisions when two reports share a filename.
            chunks.append(
                replace(
                    chunk,
                    doc_id=row["id"],
                    chunk_id=f"{row['id']}_p{chunk.page_number}_c{chunk.chunk_index}",
                    filename=row["original_filename"],
                )
            )

    index_dir = _conversation_index_dir(user_id, conversation_id)
    _ensure_private_dir(index_dir.parent)
    if not chunks:
        shutil.rmtree(index_dir, ignore_errors=True)
        return

    with tempfile.TemporaryDirectory(prefix=".index-build-", dir=index_dir.parent) as temp_name:
        temp_dir = Path(temp_name)
        retriever = DocumentRetriever(embedding_model=None)
        retriever.index_chunks(chunks, temp_dir)
        _ensure_private_dir(index_dir)
        for name in ("document_index_vectors.json", "document_index_metadata.jsonl"):
            (temp_dir / name).replace(index_dir / name)


def conversation_document_retriever(user_id: int, conversation_id: str) -> DocumentRetriever:
    """Load only the private vector index for the requested owned conversation."""
    index_dir = _conversation_index_dir(user_id, conversation_id)
    if not (index_dir / "document_index_vectors.json").is_file():
        return DocumentRetriever(
            vector_store=LocalVectorStore(),
            embedding_model=get_embedding_model(),
        )
    return DocumentRetriever.from_local_files(index_dir)


@router.get("/{conversation_id}/documents")
def list_conversation_documents(conversation_id: str, request: Request) -> dict:
    user = _current_user(request)
    _conversation_row(conversation_id, user["id"])
    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, original_filename, sha256, created_at, storage_path
            FROM documents WHERE user_id = ? AND conversation_id = ?
            ORDER BY created_at, id
            """,
            (user["id"], conversation_id),
        ).fetchall()
    documents = []
    for row in rows:
        path = Path(row["storage_path"])
        documents.append({
            "id": row["id"],
            "filename": row["original_filename"],
            "size_bytes": path.stat().st_size if path.is_file() else 0,
            "sha256": row["sha256"],
            "created_at": row["created_at"],
        })
    return {"documents": documents}


@router.post("/{conversation_id}/documents", status_code=201)
def upload_conversation_document(
    conversation_id: str,
    request: Request,
    file: UploadFile = File(...),
    csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> dict:
    _require_csrf(request, csrf_token)
    user = _current_user(request)
    _conversation_row(conversation_id, user["id"])

    filename = Path(file.filename or "").name
    if not filename or filename in {".", ".."} or not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF files are supported.")
    contents = file.file.read(MAX_PDF_BYTES + 1)
    file.file.close()
    if len(contents) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF must be 20 MB or smaller.")
    if not contents.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="The selected file does not look like a valid PDF.")

    document_id = str(uuid.uuid4())
    destination_dir = _storage_root() / str(user["id"]) / conversation_id / document_id
    _ensure_private_dir(destination_dir)
    destination = destination_dir / filename
    try:
        destination.write_bytes(contents)
        destination.chmod(0o600)
        # Validate/extract before recording the document as available.
        settings = AppSettings.from_environment()
        PDFIngestor(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap).process_file(destination)
        import hashlib
        digest = hashlib.sha256(contents).hexdigest()
        initialize_database()
        with database_connection() as connection:
            connection.execute(
                """
                INSERT INTO documents(id, user_id, conversation_id, original_filename, storage_path, sha256)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (document_id, user["id"], conversation_id, filename, str(destination), digest),
            )
        _rebuild_index(user["id"], conversation_id)
    except (OSError, ValueError, RuntimeError, PDFExtractionError) as exc:
        with database_connection() as connection:
            connection.execute("DELETE FROM documents WHERE id = ? AND user_id = ?", (document_id, user["id"]))
        shutil.rmtree(destination_dir, ignore_errors=True)
        logger.warning("Private PDF ingestion failed (%s).", type(exc).__name__)
        raise HTTPException(status_code=400, detail="The PDF could not be processed. Check that it is readable and try again.") from exc

    return {
        "document": {
            "id": document_id,
            "filename": filename,
            "size_bytes": len(contents),
            "sha256": digest,
        },
        "stored_locally": True,
        "conversation_id": conversation_id,
    }


@router.delete("/{conversation_id}/documents/{document_id}")
def delete_conversation_document(
    conversation_id: str,
    document_id: str,
    request: Request,
    csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> dict:
    _require_csrf(request, csrf_token)
    user = _current_user(request)
    _conversation_row(conversation_id, user["id"])
    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT id, storage_path FROM documents
            WHERE id = ? AND user_id = ? AND conversation_id = ?
            """,
            (document_id, user["id"], conversation_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found in this conversation.")

    try:
        _rebuild_index(user["id"], conversation_id, exclude_document_id=document_id)
    except (OSError, ValueError, RuntimeError, PDFExtractionError) as exc:
        logger.warning("Private PDF index rebuild failed (%s).", type(exc).__name__)
        raise HTTPException(status_code=500, detail="The report could not be removed safely. Please try again.") from exc

    with database_connection() as connection:
        connection.execute(
            "DELETE FROM documents WHERE id = ? AND user_id = ? AND conversation_id = ?",
            (document_id, user["id"], conversation_id),
        )
    shutil.rmtree(Path(row["storage_path"]).parent, ignore_errors=True)
    return {"deleted": True, "document_id": document_id, "conversation_id": conversation_id}
