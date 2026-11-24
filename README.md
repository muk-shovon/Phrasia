# Phrasia — Words, Refined.

A private, single-user writing workspace that runs on your own computer. It rewrites text through an external model you choose, keeps your drafts in a local database, and offers two honest local analysis tools.

## What works today

| Tool | Status | How it works |
|---|---|---|
| **Humanizer / Rewriter** | Working, needs a provider key | Text is split into chunks, rewritten by an online model (Gemini, Groq, OpenRouter or a custom OpenAI-compatible endpoint), checkpointed after every chunk, and can be retried, cancelled, reopened and exported. |
| **Similarity check** | Working, local only | Compares a passage with your own reference library using word n-grams. It does **not** search the internet and does not claim originality. |
| **Local style signal** | Working, local only | Reports named writing patterns (stock phrases, inflated words, contractions, rhythm, repetition) with a plain-language label. No score, no percentage, no authorship verdict. |

There is no authentication yet. The app binds to `127.0.0.1` only and is intended for one person on one machine.

## Stack

- **Backend:** Python 3.11+, FastAPI, uvicorn, SQLite (`sqlite3`), httpx, python-docx
- **Frontend:** Vite, TypeScript (strict), Tailwind CSS v4 — no UI framework, no runtime npm packages
- **Intelligence:** external HTTP APIs only. No local models are downloaded or run.

## Quick start (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env

cd frontend
npm install
npm run build
cd ..

python run.py
```

Open <http://127.0.0.1:8000/#/humanize>. API docs are at <http://127.0.0.1:8000/api/docs>.

To actually humanize, add a free key either in `.env` (for example `GEMINI_API_KEY=…`) or in the **Settings** page. With no key, the UI loads and the analysis tools work, but a humanize job stops with a clear "no provider configured" error. See [docs/APIS.md](docs/APIS.md) for the endpoints and their verified status.

For frontend development with hot reload: run `npm run dev` in `frontend/` while the backend runs on port 8000 (Vite proxies `/api`).

## Configuration

All settings are optional except a provider key for humanizing.

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `CUSTOM_API_KEY` | empty | Provider credentials |
| `GEMINI_MODEL`, `GROQ_MODEL`, `OPENROUTER_MODEL`, `CUSTOM_MODEL` | catalog defaults | Model selection |
| `GEMINI_BASE_URL`, `GROQ_BASE_URL`, `OPENROUTER_BASE_URL`, `CUSTOM_BASE_URL` | catalog defaults | Endpoint overrides (public URLs only) |
| `PAID_MODELS_ENABLED` | `false` | Allows catalog models marked paid |
| `PROVIDER_TIMEOUT_SECONDS` | `60` | Per-request timeout |
| `HUMANIZE_CHUNK_CHARS` | `6000` | Chunk size |
| `MAX_INPUT_CHARS` | `200000` | Per-document input limit |
| `MAX_UPLOAD_BYTES` | `20971520` | File upload limit |
| `PHRASIA_DATA_DIR` / `PHRASIA_DB_PATH` | `data/phrasia.db` | Local database location |
| `PHRASIA_PORT` | `8000` | Backend port |

Keys saved in Settings override `.env` values for that provider.

## Tests and checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npx tsc --noEmit
npm run build
```

On 2026-11-24 these ran successfully: **49 Python tests passed**, TypeScript emitted no errors, and the production frontend build completed.

## Layout

```
backend/
  api/          thin HTTP routes; every router uses require_owner()
  db/           all SQL lives in repository.py
  providers/    catalog, adapters, credential resolution
  core/         chunking, prompts, orchestration, similarity, style signal
frontend/
  src/pages/    one TypeScript module per page
  src/api.ts    typed fetch wrapper
data/           local SQLite file (created on first run, never committed)
docs/APIS.md    external API inventory
DECISIONS.md    architecture decisions
```

## Security notes

- The server binds to `127.0.0.1`; there is no login page or owner check beyond the `require_owner()` placeholder in `backend/api/deps.py`. Do not expose it to a network.
- Keys typed in Settings are stored **in plain text** in the local SQLite database. Keys in `.env` stay in that file. Neither is committed. Keep both private.
- Custom base URLs must be public `http(s)` addresses; loopback and private ranges are rejected.
- Full keys are never returned by the API; Settings only receives a masked value.
- Only TXT, Markdown and DOCX uploads are read. PDF is not supported.

## Known limitations

- No account system, no multi-user support, no cloud sync.
- Similarity is limited to your reference library, and the style signal is a heuristic — neither is an authorship test.
- Very large documents are chunked but still limited by `MAX_INPUT_CHARS`.
- Concurrency is single-process; a server restart marks in-flight jobs as paused so they can be retried.
- Only TXT and DOCX export; no diff view, batch jobs or PDF reports.

Architecture choices and their reasons are recorded in [DECISIONS.md](DECISIONS.md).
