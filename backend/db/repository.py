"""All SQLite access for Phrasia lives here.

The rest of the application never writes SQL. A future online database can be
swapped in by re-implementing this module.
"""
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
    provider_id TEXT,
    model_id TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    source_version_id INTEGER NOT NULL REFERENCES versions(id),
    result_version_id INTEGER REFERENCES versions(id),
    status TEXT NOT NULL,
    mode TEXT NOT NULL,
    intensity TEXT NOT NULL,
    options_json TEXT NOT NULL,
    total_chunks INTEGER NOT NULL DEFAULT 0,
    completed_chunks INTEGER NOT NULL DEFAULT 0,
    provider_id TEXT,
    model_id TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    seq INTEGER NOT NULL,
    source_text TEXT NOT NULL,
    separator TEXT NOT NULL DEFAULT '',
    output_text TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    UNIQUE(job_id, seq)
);

CREATE TABLE IF NOT EXISTS provider_settings (
    provider_id TEXT PRIMARY KEY,
    api_key TEXT,
    model TEXT,
    base_url TEXT,
    enabled INTEGER,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
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

CREATE TABLE IF NOT EXISTS usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id TEXT NOT NULL,
    model_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    input_chars INTEGER NOT NULL DEFAULT 0,
    output_chars INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
"""

_JOB_FIELDS = {
    "status",
    "result_version_id",
    "completed_chunks",
    "provider_id",
    "model_id",
    "error",
}


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
    """Drop every table and recreate the schema. Used by the test suite only."""
    with _db() as conn:
        conn.executescript(
            "DROP TABLE IF EXISTS analyses;"
            "DROP TABLE IF EXISTS reference_documents;"
            "DROP TABLE IF EXISTS preferences;"
            "DROP TABLE IF EXISTS provider_settings;"
            "DROP TABLE IF EXISTS chunks;"
            "DROP TABLE IF EXISTS jobs;"
            "DROP TABLE IF EXISTS versions;"
            "DROP TABLE IF EXISTS documents;"
        )
    init_db()


# ── documents and versions ────────────────────────────────────────────────────

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
            " (SELECT j.id FROM jobs j WHERE j.document_id = d.id"
            "   ORDER BY j.id DESC LIMIT 1) AS latest_job_id,"
            " (SELECT j.status FROM jobs j WHERE j.document_id = d.id"
            "   ORDER BY j.id DESC LIMIT 1) AS latest_job_status,"
            " (SELECT substr(v.content, 1, 240) FROM versions v"
            "   WHERE v.document_id = d.id ORDER BY v.id DESC LIMIT 1) AS latest_excerpt"
            " FROM documents d ORDER BY d.updated_at DESC, d.id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def list_versions(document_id: int) -> list[dict[str, Any]]:
    with _db() as conn:
        rows = conn.execute(
            "SELECT id, document_id, version_type, word_count, char_count,"
            " provider_id, model_id, created_at FROM versions"
            " WHERE document_id = ? ORDER BY id DESC",
            (document_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def add_version(
    document_id: int,
    version_type: str,
    content: str,
    *,
    provider_id: str | None = None,
    model_id: str | None = None,
) -> int:
    with _db() as conn:
        cur = conn.execute(
            "INSERT INTO versions"
            " (document_id, version_type, content, word_count, char_count,"
            "  provider_id, model_id, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                document_id,
                version_type,
                content,
                len(content.split()),
                len(content),
                provider_id,
                model_id,
                utcnow(),
            ),
        )
        return int(cur.lastrowid)


def get_version(version_id: int) -> dict[str, Any] | None:
    with _db() as conn:
        return _one(
            conn.execute("SELECT * FROM versions WHERE id = ?", (version_id,)).fetchone()
        )


def delete_document(document_id: int) -> bool:
    with _db() as conn:
        cur = conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        return cur.rowcount > 0


# ── jobs and chunks ───────────────────────────────────────────────────────────

def create_job(
    *,
    document_id: int,
    source_version_id: int,
    status: str,
    mode: str,
    intensity: str,
    options_json: str,
    total_chunks: int,
    provider_id: str | None = None,
) -> int:
    now = utcnow()
    with _db() as conn:
        cur = conn.execute(
            "INSERT INTO jobs"
            " (document_id, source_version_id, status, mode, intensity, options_json,"
            "  total_chunks, completed_chunks, provider_id, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)",
            (
                document_id,
                source_version_id,
                status,
                mode,
                intensity,
                options_json,
                total_chunks,
                provider_id,
                now,
                now,
            ),
        )
        return int(cur.lastrowid)


def update_job(job_id: int, **fields: Any) -> None:
    updates = {key: value for key, value in fields.items() if key in _JOB_FIELDS}
    updates["updated_at"] = utcnow()
    assignments = ", ".join(f"{key} = ?" for key in updates)
    values = [*updates.values(), job_id]
    with _db() as conn:
        conn.execute(f"UPDATE jobs SET {assignments} WHERE id = ?", values)


def get_job(job_id: int) -> dict[str, Any] | None:
    with _db() as conn:
        return _one(
            conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        )


def get_job_detail(job_id: int) -> dict[str, Any] | None:
    with _db() as conn:
        row = conn.execute(
            "SELECT j.*, d.title AS title, sv.content AS input_text,"
            " rv.content AS output_text"
            " FROM jobs j"
            " JOIN documents d ON d.id = j.document_id"
            " JOIN versions sv ON sv.id = j.source_version_id"
            " LEFT JOIN versions rv ON rv.id = j.result_version_id"
            " WHERE j.id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            return None
        detail = dict(row)
        detail["chunks"] = [
            dict(chunk)
            for chunk in conn.execute(
                "SELECT id, seq, status, attempt_count, error, length(source_text)"
                " AS source_length, length(output_text) AS output_length"
                " FROM chunks WHERE job_id = ? ORDER BY seq",
                (job_id,),
            )
        ]
        return detail


def list_jobs(limit: int = 50) -> list[dict[str, Any]]:
    with _db() as conn:
        rows = conn.execute(
            "SELECT j.id, j.status, j.mode, j.intensity, j.total_chunks,"
            " j.completed_chunks, j.provider_id, j.model_id, j.error,"
            " j.created_at, j.updated_at, j.document_id, d.title AS title,"
            " substr(sv.content, 1, 240) AS input_excerpt,"
            " substr(rv.content, 1, 240) AS output_excerpt"
            " FROM jobs j"
            " JOIN documents d ON d.id = j.document_id"
            " JOIN versions sv ON sv.id = j.source_version_id"
            " LEFT JOIN versions rv ON rv.id = j.result_version_id"
            " ORDER BY j.id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def list_jobs_for_document(document_id: int) -> list[dict[str, Any]]:
    with _db() as conn:
        rows = conn.execute(
            "SELECT id, status, mode, intensity, total_chunks, completed_chunks,"
            " provider_id, model_id, error, created_at, updated_at"
            " FROM jobs WHERE document_id = ? ORDER BY id DESC",
            (document_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def delete_job(job_id: int) -> bool:
    with _db() as conn:
        cur = conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        return cur.rowcount > 0


def mark_interrupted_jobs_paused() -> int:
    """A restart cannot keep in-flight work; make those jobs resumable instead."""
    with _db() as conn:
        cur = conn.execute(
            "UPDATE jobs SET status = 'paused', updated_at = ?"
            " WHERE status IN ('queued', 'running')",
            (utcnow(),),
        )
        return int(cur.rowcount)


def create_chunks(job_id: int, chunks: list[dict[str, Any]]) -> None:
    with _db() as conn:
        conn.executemany(
            "INSERT INTO chunks (job_id, seq, source_text, separator, status)"
            " VALUES (?, ?, ?, ?, 'pending')",
            [
                (job_id, index, chunk["text"], chunk["separator"])
                for index, chunk in enumerate(chunks)
            ],
        )


def list_chunks(job_id: int) -> list[dict[str, Any]]:
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM chunks WHERE job_id = ? ORDER BY seq", (job_id,)
        ).fetchall()
        return [dict(row) for row in rows]


def update_chunk(
    chunk_id: int,
    *,
    status: str,
    output_text: str | None = None,
    attempt_count: int | None = None,
    error: str | None = None,
) -> None:
    with _db() as conn:
        conn.execute(
            "UPDATE chunks SET status = ?, output_text = COALESCE(?, output_text),"
            " attempt_count = COALESCE(?, attempt_count), error = ? WHERE id = ?",
            (status, output_text, attempt_count, error, chunk_id),
        )


# ── provider settings and preferences ─────────────────────────────────────────

def provider_setting(provider_id: str) -> dict[str, Any] | None:
    with _db() as conn:
        return _one(
            conn.execute(
                "SELECT * FROM provider_settings WHERE provider_id = ?", (provider_id,)
            ).fetchone()
        )


def provider_settings() -> dict[str, dict[str, Any]]:
    with _db() as conn:
        rows = conn.execute("SELECT * FROM provider_settings").fetchall()
        return {str(row["provider_id"]): dict(row) for row in rows}


def upsert_provider_setting(
    provider_id: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    enabled: bool | None = None,
) -> None:
    current = provider_setting(provider_id) or {
        "api_key": None,
        "model": None,
        "base_url": None,
        "enabled": None,
    }
    next_key = api_key if api_key else current["api_key"]
    next_model = None if model == "" else (model if model is not None else current["model"])
    next_base = None if base_url == "" else (
        base_url if base_url is not None else current["base_url"]
    )
    next_enabled = int(enabled) if enabled is not None else current["enabled"]
    with _db() as conn:
        conn.execute(
            "INSERT INTO provider_settings"
            " (provider_id, api_key, model, base_url, enabled, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(provider_id) DO UPDATE SET"
            "  api_key = excluded.api_key, model = excluded.model,"
            "  base_url = excluded.base_url, enabled = excluded.enabled,"
            "  updated_at = excluded.updated_at",
            (
                provider_id,
                next_key,
                next_model,
                next_base,
                next_enabled,
                utcnow(),
            ),
        )


def delete_provider_key(provider_id: str) -> None:
    with _db() as conn:
        conn.execute(
            "UPDATE provider_settings SET api_key = NULL, updated_at = ?"
            " WHERE provider_id = ?",
            (utcnow(), provider_id),
        )


def get_preference(key: str, default: str | None = None) -> str | None:
    with _db() as conn:
        row = conn.execute(
            "SELECT value FROM preferences WHERE key = ?", (key,)
        ).fetchone()
        return str(row["value"]) if row is not None else default


def get_preferences() -> dict[str, str]:
    with _db() as conn:
        rows = conn.execute("SELECT key, value FROM preferences").fetchall()
        return {str(row["key"]): str(row["value"]) for row in rows}


def set_preference(key: str, value: str) -> None:
    with _db() as conn:
        conn.execute(
            "INSERT INTO preferences (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


# ── reference library ─────────────────────────────────────────────────────────

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
            "SELECT id, title, word_count, created_at FROM reference_documents"
            " ORDER BY id DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def reference_documents_with_content() -> list[dict[str, Any]]:
    with _db() as conn:
        rows = conn.execute(
            "SELECT id, title, content, word_count FROM reference_documents"
            " ORDER BY id"
        ).fetchall()
        return [dict(row) for row in rows]


def delete_reference_document(document_id: int) -> bool:
    with _db() as conn:
        cur = conn.execute(
            "DELETE FROM reference_documents WHERE id = ?", (document_id,)
        )
        return cur.rowcount > 0


# ── analyses ──────────────────────────────────────────────────────────────────

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
            rows = conn.execute(
                "SELECT * FROM analyses ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM analyses WHERE kind = ? ORDER BY id DESC LIMIT ?",
                (kind, limit),
            ).fetchall()
        return [dict(row) for row in rows]


def record_usage(
    provider_id: str,
    model_id: str,
    operation: str,
    input_chars: int = 0,
    output_chars: int = 0,
) -> None:
    with _db() as conn:
        conn.execute(
            "INSERT INTO usage (provider_id, model_id, operation, input_chars,"
            " output_chars, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (provider_id, model_id, operation, input_chars, output_chars, utcnow()),
        )


def list_usage(limit: int = 50) -> list[dict[str, Any]]:
    with _db() as conn:
        rows = conn.execute("SELECT * FROM usage ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]


def retry_failed_chunks(job_id: int) -> int:
    """Reset error chunks of a job back to pending so run_job retries them.

    Completed chunks are left untouched, so retrying is cheap. Returns the
    number of chunks reset.
    """
    with _db() as conn:
        cur = conn.execute(
            "UPDATE chunks SET status = 'pending', error = NULL, attempt_count = 0"
            " WHERE job_id = ? AND status = 'error'",
            (job_id,),
        )
        return int(cur.rowcount)
