# Phrasia — Words, Refined.

An intelligent workspace for better writing. Private, premium, single-owner.

**Tagline:** Words, Refined.  
**Descriptor:** An intelligent workspace for better writing.

---

## Table of contents

1. [What this is](#what-this-is)
2. [Tech stack](#tech-stack)
3. [Prerequisites](#prerequisites)
4. [Local development](#local-development)
5. [Configuration](#configuration)
6. [Running tests](#running-tests)
7. [Deployment](#deployment)
8. [Security notes](#security-notes)
9. [Known limitations](#known-limitations)
10. [Troubleshooting](#troubleshooting)

---

## What this is

Phrasia lets you paste or upload a document, select a humanization mode, and send it through a real external AI API (Gemini, Groq, FreeLLMAPI, or OpenAI) to produce a clearer, more natural rewrite. Results are saved to Supabase, chunked for long documents, and resumable after interruptions.

**Three planned capabilities** (only the Humanizer is fully functional in this release):

1. ✅ **AI Humanizer / Rewriter** — working
2. 🚧 **Plagiarism / Similarity Checker** — phases 3, in progress
3. 🚧 **AI Writing Detector** — phases 4, in progress

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| UI framework | Reflex (Python-authored) |
| Backend runtime | Vercel Serverless Functions |
| Database | Supabase PostgreSQL |
| Auth | Supabase Auth |
| File storage | Supabase Storage (private buckets) |
| Job queue | Supabase Queues / Postgres-backed claim queue |
| Scheduler | Supabase Cron → Vercel worker tick |
| External APIs | Gemini, Groq, FreeLLMAPI, OpenAI (provider adapters) |
| Testing | pytest + pytest-asyncio |
| Linting/formatting | ruff |

---

## Prerequisites

- Python 3.11 or 3.12
- A Supabase Free project ([supabase.com/dashboard](https://supabase.com/dashboard))
- A Vercel Hobby account linked to this repository
- At least one external API key (Gemini free-tier recommended)

---

## Local development

```powershell
# Navigate to project root
cd "D:\My Own Web APP\Phrasia"

# Create virtual environment (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -e ".[dev]"

# Copy and fill environment variables
copy .env.example .env
# Edit .env and add your SUPABASE_URL, SUPABASE_SECRET_KEY, GEMINI_API_KEY, etc.

# Run tests
pytest tests/unit/ -v

# Start the Reflex dev server
reflex run --port 3000
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Configuration

Copy `.env.example` to `.env` and fill in the values below. **Never commit `.env`** — it is already in `.gitignore`.

| Variable | Required? | Source |
|----------|-----------|--------|
| `SUPABASE_URL` | ✅ Yes | Supabase Dashboard → Settings → API |
| `SUPABASE_PUBLISHABLE_KEY` | ✅ Yes | Same location |
| `SUPABASE_SECRET_KEY` | ✅ Yes | Same location (service-role key) |
| `GEMINI_API_KEY` | Recommended | [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| `GROQ_API_KEY` | Optional | [console.groq.com/keys](https://console.groq.com/keys) |
| `FREELLMAPI_API_KEY` | Optional | Your local FreeLLMAPI gateway |
| `WORKER_CRON_SECRET` | For production | Generate: `openssl rand -hex 32` |
| `PHRASIA_SECRET_ENCRYPTION_KEY` | For production | Generate: `openssl rand -hex 32` |
| `PAID_PROVIDERS_ENABLED` | `false` by default | Keep `false` unless you intend to pay |

After setting `SUPABASE_*` variables, apply migrations:

```powershell
npx supabase login
npx supabase link --project-ref YOUR_PROJECT_REF
npx supabase db push
```

To disable public sign-up (single-owner security), go to Supabase Dashboard → Authentication → Providers → Email → toggle **"Enable sign up"** off.

---

## Running tests

```powershell
pytest tests/unit/ -v
pytest tests/unit/ -k chunking -v       # only chunk tests
pytest tests/unit/ --tb=short           # concise tracebacks on failure
```

Mock-based tests do **not** call real APIs. To run a live smoke test against a configured provider, uncomment the `LIVE_API_TEST=1` guard in the relevant test file.

---

## Deployment

### Step 1 — Push to Git

```powershell
git init
git add .
git commit -m "Initial Phrasia scaffold"
git branch -M main
git remote add origin https://github.com/YOUR_USER/phrasia.git
git push -u origin main
```

### Step 2 — Connect to Vercel

```powershell
npx vercel login
npx vercel link
npx vercel env add SUPABASE_URL        # paste value
npx vercel env add SUPABASE_SECRET_KEY # paste value
npx vercel env add GEMINI_API_KEY      # paste value
# ... repeat for every variable in .env
npx vercel --prod
```

### Step 3 — Configure Reflex API URL

Add a Vercel environment variable:

```
REFLEX_API_URL=https://your-project.vercel.app
```

This tells the exported Reflex frontend where to send events.

### Step 4 — Verify deployment

Visit your Vercel URL. Sign in with Supabase Auth. Paste text in the workspace, click **Humanize Text**, and watch it process through the configured provider.

### Important notes

- The **first Vercel deploy** may take 2–3 minutes to build the Python runtime.
- Refl ex exports static assets to `.web/`; Vercel serves those plus the Python function at `.vercel/functions/api.func/`.
- After deployment, RLS policies ensure each user can only access their own documents.
- Public sign-up must be disabled in Supabase Dashboard after creating your owner account.

---

## Security notes

- Provider API keys and `SUPABASE_SECRET_KEY` are **server-side only**. They never reach the browser.
- RLS policies on every table enforce owner scoping. Unauthorized queries return empty sets.
- Large uploads go directly to Supabase Storage via signed URLs — they do not flow through Vercel Functions.
- `.env` is gitignored; secrets belong in Vercel Environment Variables, not source control.
- The application never claims rewritten text is human-authored or that any AI detector has been bypassed.

---

## Known limitations

| Limitation | Detail |
|------------|--------|
| No SQLite fallback | Production requires Supabase; local dev may use `supabase start` or skip DB features |
| Long documents need multiple requests | Chunked processing is resumable but takes time proportional to document length |
| Provider quotas change | Free tiers may be modified by providers without notice; the app handles 429/quota errors gracefully |
| DOCX import/export | Basic structure preserved; complex formatting may simplify |
| Vercel Hobby restrictions | Personal/non-commercial use only; 300 s function duration limit; daily cron only on Hobby plan (use Supabase Cron instead) |
| AI detector scores | Not implemented in this release (Phase 4) |
| Plagiarism scanning | Not implemented in this release (Phase 3) |

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `ModuleNotFoundError: reflex` | Virtual environment not activated | Activate `.venv`, reinstall with `pip install -e .` |
| Blank page on localhost | Reflex dev server failed to bind port | Try `reflex run --port 3001` or check another process holds port 3000 |
| "No eligible provider" error | No provider API key in `.env` | Add `GEMINI_API_KEY` or `FREELLMAPI_API_KEY` |
| 401 on API calls | Missing or wrong `SUPABASE_SECRET_KEY` | Regenerate from Supabase Dashboard → Settings → API |
| Stuck on "queued" status | Worker not invoked | Check Supabase Cron configuration; local dev skips worker ticks |
| Upload fails at >50 MB | Supabase Free plan object limit | Reduce file size or upgrade Supabase plan |
| "Public sign-up not disabled" warning | New Supabase projects allow registrations by default | Toggle off in Dashboard → Authentication → Providers |

---

## File structure

```
phrasia/
├── app/
│   └── pages/          Reflex pages (workspace, history, settings)
├── core/               Business logic (chunker, prompts, humanizer service)
├── infrastructure/     Supabase client, worker tick handler
├── providers/          Provider adapters and router
├── api/                Vercel API routes
├── supabase/migrations SQL migrations
├── tests/unit/         Unit tests
├── phrasia_domain.py   Domain models and enums
├── rxconfig.py         Reflex app definition
├── pyproject.toml      Python dependencies
├── vercel.json         Vercel configuration
├── .env.example        Configuration template
└── *.md                Documentation
```

---

**Phrasia — Words, Refined.**
Built with Python, Reflex, Supabase, and external AI APIs.