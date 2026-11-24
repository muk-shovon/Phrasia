# Phrasia — Words, Refined.

A private, single-user writing workspace that runs on your own machine: paste text, humanize it through an external LLM, browse history, run a local similarity check against your own reference library, and read a local style signal.

**What actually works today**
- Humanizer: rewrite in 8 modes × 3 intensity levels, original vs. output panels, per-chunk progress, cancel, retry, export to .txt/.docx
- History: documents + versions, reopen, delete
- Settings: provider keys/models/base URLs (masked), test connection
- Similarity: local word-shingle + difflib check against your reference library
- Style signal: local heuristic report — no verdict, no percentage

**What is not implemented** (PRD phases 3–5): plagiarism web search, AI-detector provider integration, diff view, batch jobs. The humanizer needs a provider key: Gemini, Groq or OpenRouter (free tiers).

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

Without a provider key: Settings page loads, analysis tools work, and the humanizer shows a "no provider configured" error.

## Configuration
Provider keys/models/base URLs are stored in your local SQLite DB (`data/phrasia.db`). `.env` sets defaults; saved keys override. Set a key in `.env` or in Settings, e.g. `GEMINI_API_KEY` (or `GROQ_API_KEY`, `OPENROUTER_API_KEY`).

## Testing
```powershell
.\.venv\Scripts\python.exe -m pytest
cd frontend
npm run typecheck   # tsc --noEmit
npm run build       # vite build → frontend/dist
```

## API docs
`http://127.0.0.1:8000/api/docs`. External API status: `docs/APIS.md`.

## Privacy
App binds to `127.0.0.1` only. Keys are stored locally. Full keys are never returned by the API.
