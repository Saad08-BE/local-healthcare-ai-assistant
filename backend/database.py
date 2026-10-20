"""SQLite foundation for private React/FastAPI conversations.

This module deliberately does not connect to the shared Streamlit document index.
It only defines the database and connection helpers; API routes are added in later
implementation phases.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "react_api" / "healthai.sqlite3"
DATABASE_PATH_ENV = "HEALTHAI_DATABASE_PATH"
SCHEMA_VERSION = 2


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL COLLATE NOCASE UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL DEFAULT 'New chat',
    is_pinned INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (id, user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    conversation_id TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    storage_path TEXT NOT NULL UNIQUE,
    sha256 TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (id, user_id, conversation_id),
    FOREIGN KEY (conversation_id, user_id)
        REFERENCES conversations(id, user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    page_number INTEGER,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (document_id, chunk_index),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_conversations_user_updated
    ON conversations(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_user_pinned_updated
    ON conversations(user_id, is_pinned DESC, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
    ON messages(conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_documents_user_conversation
    ON documents(user_id, conversation_id);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON document_chunks(document_id);
"""


def resolve_database_path(path: str | Path | None = None) -> Path:
    """Resolve an explicit path, environment override, or private local default."""
    if path is not None:
        return Path(path).expanduser().resolve()

    configured_path = os.environ.get(DATABASE_PATH_ENV)
    if configured_path:
        return Path(configured_path).expanduser().resolve()

    return DEFAULT_DATABASE_PATH.resolve()


def get_connection(path: str | Path | None = None) -> sqlite3.Connection:
    """Open a connection with row objects and foreign-key checks enabled."""
    db_path = resolve_database_path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    connection = sqlite3.connect(str(db_path), timeout=5.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


@contextmanager
def database_connection(
    path: str | Path | None = None,
) -> Iterator[sqlite3.Connection]:
    """Yield a connection, commit on success, roll back on error, and close it."""
    connection = get_connection(path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(path: str | Path | None = None) -> Path:
    """Create the schema if needed and return the database file path."""
    db_path = resolve_database_path(path)
    with database_connection(db_path) as connection:
        connection.executescript(SCHEMA)
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(conversations)").fetchall()}
        if "is_pinned" not in columns:
            connection.execute("ALTER TABLE conversations ADD COLUMN is_pinned INTEGER NOT NULL DEFAULT 0")
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    # Keep this local database private to the current operating-system user where
    # the platform supports POSIX file permissions.
    try:
        db_path.chmod(0o600)
    except OSError:
        # Windows and some mounted filesystems do not support POSIX permissions.
        pass

    return db_path
