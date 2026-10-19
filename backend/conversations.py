"""Authenticated CRUD endpoints for persistent conversations."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from backend.auth import _current_user, _require_csrf
from backend.database import database_connection, initialize_database

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class CreateConversationRequest(BaseModel):
    title: str = Field(default="New chat", min_length=1, max_length=120)


def _owned_conversation(connection, conversation_id: str, user_id: int):
    row = connection.execute(
        "SELECT id, user_id, title, created_at, updated_at FROM conversations WHERE id = ? AND user_id = ?",
        (conversation_id, user_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return row


@router.get("")
def list_conversations(request: Request) -> dict:
    user = _current_user(request)
    initialize_database()
    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT c.id, c.title, c.created_at, c.updated_at,
                   (SELECT m.content FROM messages m
                    WHERE m.conversation_id = c.id AND m.role IN ('user', 'assistant')
                    ORDER BY m.id DESC LIMIT 1) AS last_message,
                   (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count
            FROM conversations c
            WHERE c.user_id = ?
            ORDER BY c.updated_at DESC, c.created_at DESC
            """,
            (user["id"],),
        ).fetchall()
    return {"conversations": [dict(row) for row in rows]}


@router.post("", status_code=201)
def create_conversation(
    payload: CreateConversationRequest,
    request: Request,
    csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> dict:
    _require_csrf(request, csrf_token)
    user = _current_user(request)
    initialize_database()
    conversation_id = str(uuid.uuid4())
    title = payload.title.strip() or "New chat"
    with database_connection() as connection:
        connection.execute(
            "INSERT INTO conversations(id, user_id, title) VALUES (?, ?, ?)",
            (conversation_id, user["id"], title),
        )
        row = connection.execute(
            "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
    return {"conversation": dict(row)}


@router.get("/{conversation_id}")
def get_conversation(conversation_id: str, request: Request) -> dict:
    user = _current_user(request)
    initialize_database()
    with database_connection() as connection:
        conversation = _owned_conversation(connection, conversation_id, user["id"])
        messages = connection.execute(
            """
            SELECT id, role, content, metadata_json, created_at
            FROM messages WHERE conversation_id = ? ORDER BY id ASC
            """,
            (conversation_id,),
        ).fetchall()
        documents = connection.execute(
            """
            SELECT id, original_filename, sha256, created_at
            FROM documents WHERE conversation_id = ? AND user_id = ?
            ORDER BY created_at ASC
            """,
            (conversation_id, user["id"]),
        ).fetchall()
    return {
        "conversation": dict(conversation),
        "messages": [dict(row) for row in messages],
        "documents": [dict(row) for row in documents],
    }


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    request: Request,
    csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> dict:
    _require_csrf(request, csrf_token)
    user = _current_user(request)
    initialize_database()
    with database_connection() as connection:
        _owned_conversation(connection, conversation_id, user["id"])
        connection.execute(
            "DELETE FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user["id"]),
        )
    return {"deleted": True, "conversation_id": conversation_id}
