-- Phrasia SQLite schema. Also created by backend/db/repository.py automatically.
-- The app never executes this file directly.

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
