"""All SQLite access for Phrasia lives here."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from backend.config import DATA_DIR, DB_PATH

_SEED_PATH = Path(__file__).resolve().parent.parent / "engine" / "llm" / "seed_examples.json"

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

CREATE TABLE IF NOT EXISTS example_pairs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tone TEXT NOT NULL,
    strength TEXT NOT NULL,
    operation TEXT NOT NULL DEFAULT '',
    source_text TEXT NOT NULL,
    rewritten_text TEXT NOT NULL,
    score_before REAL NOT NULL DEFAULT 0,
    score_after REAL NOT NULL DEFAULT 0,
    rating INTEGER NOT NULL DEFAULT 1,
    embedding TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_example_pairs_lookup
    ON example_pairs (tone, strength, operation, rating);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id INTEGER,
    sentence_idx INTEGER,
    operation TEXT NOT NULL DEFAULT '',
    action TEXT NOT NULL,
    source_text TEXT NOT NULL DEFAULT '',
    final_text TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS llm_cache (
    hash TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    output TEXT NOT NULL,
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
        _ensure_column(conn, "example_pairs", "operation", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "feedback", "operation", "TEXT NOT NULL DEFAULT ''")
        _retire_voice_tables(conn)
    seed_example_pairs()


def _ensure_column(
    conn: sqlite3.Connection, table: str, column: str, ddl: str
) -> None:
    """Add a column to a database created by an older release."""
    columns = {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def _retire_voice_tables(conn: sqlite3.Connection) -> None:
    """Back up then drop the retired style-profile (voice) table."""
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'style_profiles'"
    ).fetchone()
    if row is None:
        return
    rows = [dict(item) for item in conn.execute("SELECT * FROM style_profiles").fetchall()]
    if rows:
        backup_dir = DATA_DIR / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = backup_dir / f"style_profiles_{stamp}.json"
        backup.write_text(
            json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    conn.execute("DROP TABLE style_profiles")


def reset_db_for_tests() -> None:
    with _db() as conn:
        conn.executescript(
            "DROP TABLE IF EXISTS feedback;"
            "DROP TABLE IF EXISTS llm_cache;"
            "DROP TABLE IF EXISTS example_pairs;"
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


# ---------------------------------------------------------------------------
# Learning tables: example pairs, feedback and the LLM cache
# ---------------------------------------------------------------------------

def example_pair_count() -> int:
    with _db() as conn:
        row = conn.execute("SELECT COUNT(*) AS total FROM example_pairs").fetchone()
        return int(row["total"]) if row is not None else 0


def seed_example_pairs() -> int:
    """Insert the bundled starter pairs once, when the table is empty."""
    if example_pair_count() or not _SEED_PATH.is_file():
        return 0
    try:
        data = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    if not isinstance(data, list):
        return 0
    count = 0
    for item in data:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source_text", "")).strip()
        rewritten = str(item.get("rewritten_text", "")).strip()
        if not source or not rewritten:
            continue
        add_example_pair(
            tone=str(item.get("tone", "casual")),
            strength=str(item.get("strength", "medium")),
            operation=str(item.get("operation", "keep")),
            source_text=source,
            rewritten_text=rewritten,
            rating=1,
        )
        count += 1
    return count


def add_example_pair(
    *,
    tone: str,
    strength: str,
    operation: str = "keep",
    source_text: str,
    rewritten_text: str,
    score_before: float = 0.0,
    score_after: float = 0.0,
    rating: int = 1,
) -> int:
    with _db() as conn:
        cur = conn.execute(
            "INSERT INTO example_pairs (tone, strength, operation, source_text,"
            " rewritten_text, score_before, score_after, rating, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                tone[:40], strength[:20], operation[:40], source_text, rewritten_text,
                float(score_before), float(score_after), int(rating), utcnow(),
            ),
        )
        return int(cur.lastrowid)


def list_example_pairs(
    *,
    tone: str | None = None,
    strength: str | None = None,
    operation: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    query = (
        "SELECT id, tone, strength, operation, source_text, rewritten_text,"
        " score_before, score_after, rating, created_at FROM example_pairs"
        " WHERE rating >= 0"
    )
    params: list[Any] = []
    if tone:
        query += " AND (tone = ? OR tone = 'any')"
        params.append(tone)
    if strength:
        query += " AND (strength = ? OR strength = 'any')"
        params.append(strength)
    if operation:
        query += " AND (operation = ? OR operation = '')"
        params.append(operation)
    query += " ORDER BY rating DESC, id DESC LIMIT ?"
    params.append(max(1, min(500, limit)))
    with _db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def add_feedback(
    *,
    version_id: int | None,
    sentence_idx: int | None,
    action: str,
    source_text: str = "",
    final_text: str = "",
    operation: str = "",
) -> int:
    with _db() as conn:
        cur = conn.execute(
            "INSERT INTO feedback (version_id, sentence_idx, operation, action,"
            " source_text, final_text, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                version_id, sentence_idx, operation[:40], action[:20],
                source_text, final_text, utcnow(),
            ),
        )
        return int(cur.lastrowid)


def list_feedback(limit: int = 50) -> list[dict[str, Any]]:
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM feedback ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]


def cache_get(key: str) -> str | None:
    with _db() as conn:
        row = conn.execute(
            "SELECT output FROM llm_cache WHERE hash = ?", (key,)
        ).fetchone()
        return str(row["output"]) if row is not None else None


def cache_put(key: str, provider: str, output: str) -> None:
    with _db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO llm_cache (hash, provider, output, created_at)"
            " VALUES (?, ?, ?, ?)",
            (key, provider[:120], output, utcnow()),
        )
        row = conn.execute("SELECT COUNT(*) AS total FROM llm_cache").fetchone()
        if row is not None and int(row["total"]) > 4000:
            conn.execute(
                "DELETE FROM llm_cache WHERE hash IN"
                " (SELECT hash FROM llm_cache ORDER BY created_at ASC LIMIT 1000)"
            )


def cache_clear() -> int:
    with _db() as conn:
        cur = conn.execute("DELETE FROM llm_cache")
        return int(cur.rowcount)
