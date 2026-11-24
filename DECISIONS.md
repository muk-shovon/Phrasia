# Decision Log — Phrasia

Short, honest decisions. Overengineering without value was removed.

## D-001: FastAPI + SQLite + Vite/TS, no framework, no auth yet
- **Stack:** Python 3.11+ (FastAPI, uvicorn, SQLite via stdlib sqlite3, httpx, python-docx), Vite + TypeScript (strict) + Tailwind v4 for the frontend.
- **No auth:** `require_owner()` in `backend/api/deps.py` is a no-op with a TODO. The app binds to `127.0.0.1` only.
- **No ML models:** rewriting goes through external LLM APIs (Gemini, Groq, OpenRouter, custom). No local models are downloaded or run.

## D-002: Local SQLite at data/phrasia.db
- All SQL lives in `backend/db/repository.py` (+ `schema.sql`). Nothing else writes SQL.
- Created automatically on first run; gitignored.

## D-003: No dead code, one source of truth
- Single provider catalog (`backend/providers/catalog.py`) and single style-signal module (`backend/core/detector.py`).
- Unused TS exports and dead functions were deleted.

## D-004: The style signal stays honest
- Returns `label` + `label_description: "Local style signal"` and signals; no verdict, no percentage, disclaimer: "style signal, not proof of authorship".
- A `humanize → scan → repeat` loop is NOT a feature here.

## D-005: Web plagiarism check not added
- Verified on 2026-11-24: Winston AI (POST /api/v1/plagiarism) → 401 `authentication_error` without a key; plagiarism.free (POST /api/v1/check/) → 401 `missing_bearer_token`.
- No free, verified API found → similarity stays local (word shingles + difflib). No invented endpoints.

## D-006: run.py is the one command
- `python run.py`: auto-runs `npm install` + `npm run build` if `frontend/dist` is missing (npm.cmd for Windows), starts uvicorn on 127.0.0.1:8000.
