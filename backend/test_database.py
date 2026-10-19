"""Tests for the SQLite foundation; all files are temporary and local to tests."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.database import database_connection, initialize_database


class DatabaseFoundationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "test-healthai.sqlite3"
        initialize_database(self.database_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_initialization_creates_expected_tables(self) -> None:
        with database_connection(self.database_path) as connection:
            names = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }

        self.assertTrue(
            {
                "users",
                "sessions",
                "conversations",
                "messages",
                "documents",
                "document_chunks",
            }.issubset(names)
        )

    def test_foreign_keys_are_enabled(self) -> None:
        with database_connection(self.database_path) as connection:
            enabled = connection.execute("PRAGMA foreign_keys").fetchone()[0]
        self.assertEqual(enabled, 1)

    def test_document_must_belong_to_its_conversation_owner(self) -> None:
        with database_connection(self.database_path) as connection:
            user_id = connection.execute(
                "INSERT INTO users(email, password_hash) VALUES (?, ?)",
                ("person@example.com", "test-hash-not-a-real-password"),
            ).lastrowid
            other_user_id = connection.execute(
                "INSERT INTO users(email, password_hash) VALUES (?, ?)",
                ("other@example.com", "another-test-hash"),
            ).lastrowid
            connection.execute(
                "INSERT INTO conversations(id, user_id, title) VALUES (?, ?, ?)",
                ("conversation-a", user_id, "Private chat"),
            )

            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO documents(
                        id, user_id, conversation_id, original_filename, storage_path
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        "document-a",
                        other_user_id,
                        "conversation-a",
                        "report.pdf",
                        "/private/test/report.pdf",
                    ),
                )

    def test_deleting_conversation_cascades_to_messages_documents_and_chunks(self) -> None:
        with database_connection(self.database_path) as connection:
            user_id = connection.execute(
                "INSERT INTO users(email, password_hash) VALUES (?, ?)",
                ("person@example.com", "test-hash"),
            ).lastrowid
            connection.execute(
                "INSERT INTO conversations(id, user_id) VALUES (?, ?)",
                ("conversation-a", user_id),
            )
            connection.execute(
                """
                INSERT INTO messages(conversation_id, role, content)
                VALUES (?, ?, ?)
                """,
                ("conversation-a", "user", "What does this report mean?"),
            )
            connection.execute(
                """
                INSERT INTO documents(
                    id, user_id, conversation_id, original_filename, storage_path
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "document-a",
                    user_id,
                    "conversation-a",
                    "report.pdf",
                    "/private/test/report.pdf",
                ),
            )
            connection.execute(
                """
                INSERT INTO document_chunks(document_id, chunk_index, chunk_text)
                VALUES (?, ?, ?)
                """,
                ("document-a", 0, "Example extracted text"),
            )
            connection.execute(
                "DELETE FROM conversations WHERE id = ?", ("conversation-a",)
            )

            for table in ("messages", "documents", "document_chunks"):
                count = connection.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]
                self.assertEqual(count, 0, f"{table} should cascade on chat deletion")

    def test_email_is_unique_without_case_sensitivity(self) -> None:
        with database_connection(self.database_path) as connection:
            connection.execute(
                "INSERT INTO users(email, password_hash) VALUES (?, ?)",
                ("person@example.com", "test-hash"),
            )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO users(email, password_hash) VALUES (?, ?)",
                    ("PERSON@example.com", "different-test-hash"),
                )


if __name__ == "__main__":
    unittest.main()
