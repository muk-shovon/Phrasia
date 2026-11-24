"""All SQLite access for Phrasia lives here."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from backend.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'pasted',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_type TEXT NOT NULL,
    content TEXT NOT NULL,
    word_count INTEGER NOT NULL,
    char_count INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reference_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    word_count INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    input_excerpt TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def _db() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _one(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def init_db() -> None:
    with _db() as conn:
        conn.executescript(SCHEMA)


def reset_db_for_tests() -> None:
    with _db() as conn:
        conn.executescript(
            "DROP TABLE IF EXISTS analyses;"
            "DROP TABLE IF EXISTS reference_documents;"
            "DROP TABLE IF EXISTS versions;"
            "DROP TABLE IF EXISTS documents;"
        )
    init_db()


def create_document(title: str, source_type: str = "pasted") -> int:
    now = utcnow()
    with _db() as conn:
        cur = conn.execute(
            "INSERT INTO documents (title, source_type, created_at, updated_at)"
            " VALUES (?, ?, ?, ?)",
            (title, source_type, now, now),
        )
        return int(cur.lastrowid)


def update_document_title(document_id: int, title: str) -> None:
    with _db() as conn:
        conn.execute(
            "UPDATE documents SET title = ?, updated_at = ? WHERE id = ?",
            (title, utcnow(), document_id),
        )


def get_document(document_id: int) -> dict[str, Any] | None:
    with _db() as conn:
        return _one(
            conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        )


def list_documents(limit: int = 100) -> list[dict[str, Any]]:
    with _db() as conn:
        rows = conn.execute(
            "SELECT d.id, d.title, d.source_type, d.created_at, d.updated_at,"
            " (SELECT COUNT(*) FROM versions v WHERE v.document_id = d.id) AS version_count,"
            " (SELECT substr(v.content, 1, 240) FROM versions v"
            "   WHERE v.document_id = d.id ORDER BY v.id DESC LIMIT 1) AS latest_excerpt"
            " FROM documents d ORDER BY d.updated_at DESC, d.id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def add_version(document_id: int, version_type: str, content: str) -> int:
    with _db() as conn:
        cur = conn.execute(
            "INSERT INTO versions (document_id, version_type, content, word_count,"
            " char_count, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (document_id, version_type, content, len(content.split()), len(content), utcnow()),
        )
        return int(cur.lastrowid)


def list_versions(document_id: int) -> list[dict[str, Any]]:
    with _db() as conn:
        rows = conn.execute(
            "SELECT id, document_id, version_type, word_count, char_count, created_at"
            " FROM versions WHERE document_id = ? ORDER BY id DESC",
            (document_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def versions_with_content(document_id: int) -> list[dict[str, Any]]:
    with _db() as conn:
        rows = conn.execute(
            "SELECT id, version_type, content, word_count, char_count, created_at"
            " FROM versions WHERE document_id = ? ORDER BY id",
            (document_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_version(version_id: int) -> dict[str, Any] | None:
    with _db() as conn:
        return _one(
            conn.execute("SELECT * FROM versions WHERE id = ?", (version_id,)).fetchone()
        )


def latest_version(document_id: int, version_type: str) -> str | None:
    with _db() as conn:
        row = conn.execute(
            "SELECT content FROM versions WHERE document_id = ? AND version_type = ?"
            " ORDER BY id DESC LIMIT 1",
            (document_id, version_type),
        ).fetchone()
        return str(row["content"]) if row is not None else None


def delete_document(document_id: int) -> bool:
    with _db() as conn:
        cur = conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        return cur.rowcount > 0


def add_reference_document(title: str, content: str, word_count: int) -> int:
    with _db() as conn:
        cur = conn.execute(
            "INSERT INTO reference_documents (title, content, word_count, created_at)"
            " VALUES (?, ?, ?, ?)",
            (title, content, word_count, utcnow()),
        )
        return int(cur.lastrowid)


def list_reference_documents() -> list[dict[str, Any]]:
    with _db() as conn:
        rows = conn.execute(
            "SELECT id, title, word_count, created_at FROM reference_documents ORDER BY id DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def reference_documents_with_content() -> list[dict[str, Any]]:
    with _db() as conn:
        rows = conn.execute(
            "SELECT id, title, content, word_count FROM reference_documents ORDER BY id"
        ).fetchall()
        return [dict(row) for row in rows]


def delete_reference_document(document_id: int) -> bool:
    with _db() as conn:
        cur = conn.execute("DELETE FROM reference_documents WHERE id = ?", (document_id,))
        return cur.rowcount > 0


def add_analysis(kind: str, input_excerpt: str, result_json: str) -> int:
    with _db() as conn:
        cur = conn.execute(
            "INSERT INTO analyses (kind, input_excerpt, result_json, created_at)"
            " VALUES (?, ?, ?, ?)",
            (kind, input_excerpt, result_json, utcnow()),
        )
        return int(cur.lastrowid)


def list_analyses(kind: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    with _db() as conn:
        if kind is None:
            rows = conn.execute("SELECT * FROM analyses ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM analyses WHERE kind = ? ORDER BY id DESC LIMIT ?",
                (kind, limit),
            ).fetchall()
        return [dict(row) for row in rows]
