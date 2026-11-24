# Decision Log - Phrasia

Short, honest decisions. Overengineering without value was removed.

## D-001: FastAPI + SQLite + Vite/TS, no auth yet
- **Stack:** Python 3.11+ (FastAPI, uvicorn, SQLite via stdlib sqlite3, httpx, python-docx), Vite + TypeScript (strict) + Tailwind v4 for the frontend.
- **No auth:** `require_owner()` in `backend/api/deps.py` is a no-op with a TODO. The app binds to `127.0.0.1` only.
- **No ML models:** rewriting goes through external LLM APIs (anonymous LLM lanes). No local models are downloaded or run.

## D-002: Local SQLite at data/phrasia.db
- All SQL lives in `backend/db/repository.py` (+ `schema.sql`). Nothing else writes SQL.
- Created automatically on first run; gitignored.

## D-003: No dead code, one source of truth
- Single provider catalog (`backend/providers/catalog.py`) and single style-signal module (`backend/core/detector.py`).
- Unused TS exports and dead functions were deleted.

## D-004: The style signal stays honest
- Returns `label` + `label_description: "Local style signal"` and signals; no verdict, no percentage, disclaimer: "style signal, not proof of authorship".
- A `humanize -> scan -> repeat` loop is NOT a feature here.

## D-005: Default providers are anonymous-first
- Catalog: Pollinations (priority 10) and OVHcloud AI Endpoints (priority 20). Both verified anonymous in 2026-11-24 with real requests.
- Per-provider rate limiter (`RateLimiter` in `backend/providers/base.py`) enforced using catalog `rate_limit_requests_per_minute`.
- Legacy adapters (gemini.py, groq.py, openrouter.py) and their env vars/settings fields were deleted.

## D-006: Plagiarism = local + real web search via ddgs
- Local shingles/difflib vs reference library; plus `ddgs==9.16.1` real search calls (verified working in 2026-11).

## D-007: Chunks are small (~800 tokens)
- `CHUNK_CHARS` default 2,560 (~800 tokens); configurable via `HUMANIZE_CHUNK_CHARS`.

## D-008: run.py is the one command
- `python run.py`: auto-runs `npm install` + `npm run build` if `frontend/dist` is missing (npm.cmd for Windows), starts uvicorn on 127.0.0.1:8000.

## UI redesign (2026)
- Implemented a full frontend redesign using the Olive Leaf / Black Forest / Cornsilk palette, a collapsible desktop sidebar, mobile off-canvas drawer, and a shared CSS/Tailwind design system in rontend/src/style.css and rontend/src/ui.ts. All five pages (Humanize, Similarity Check, Style Signal, History, Settings) use the shared components and preserve existing API behavior.

