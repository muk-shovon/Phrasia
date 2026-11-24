# Phrasia - Words, Refined.

A private, single-user writing workspace: paste text, humanize it through anonymous free LLM endpoints, browse history, run a local similarity check against your own reference library, and read a local style signal.

## What actually works today

- Humanizer: 8 modes, 3 intensities, compact original/rewritten panels, per-chunk progress, cancel, retry, export to .txt/.docx, highlight changes (on by default), optional original wording, Clean invisible characters toggle, 1500-word request limit.
- Style check: local pattern-list report after humanize (before/after tells, remaining patterns, changes to review, words changed %). Not an AI-detector result and not proof of authorship.
- History: documents + versions, reopen, delete
- Settings: toggle providers on/off, edit model/base URL, test connection, list models
- Plagiarism: local word-shingle + difflib check against the reference library, plus a real web search via `ddgs`
- Style signal: local pattern highlights from `backend/core/ai_patterns.json` - no verdict, no percentage

Default providers (all anonymous, verified 2026-11-24):
- Pollinations: `https://text.pollinations.ai/openai/chat/completions` (~8s for a 300-word rewrite)
- OVHcloud AI Endpoints: `https://oai.endpoints.kepler.ai.cloud.ovh.net/v1` (mild rate limiting)

## Requirements

- Windows 10+ (PowerShell), Python 3.11+
- Optional: Node/npm to build the frontend; `python run.py` builds it automatically

## Setup (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate-Venv.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python run.py
```

Open <http://127.0.0.1:8000/>.

Dev mode (no build required): `npm run dev` in `frontend/`, and run `python run.py` in the repo root (it proxies `/api`).

## Configuration

Providers can be re-ordered, enabled/disabled, or given a custom base URL/model in Settings. Optional keys can be stored per provider. `.env` sets optional defaults.

## Testing

```powershell
.\.venv\Scripts\python.exe -m pytest
cd frontend
npm run typecheck   # tsc --noEmit
npm run build       # vite build -> frontend/dist
```

## API docs

`http://127.0.0.1:8000/api/docs`. External API status: `docs/APIS.md`.

## Privacy

App binds to `127.0.0.1` only. Keys are stored in your local SQLite DB (`data/phrasia.db`). Full keys are never returned by the API.
