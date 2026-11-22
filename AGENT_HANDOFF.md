# Agent Handoff — Phrasia

## Current branch / state
- Branch: `main` (Git initialized)
- Working directory: `D:\My Own Web APP\Phrasia`
- Last commit: `2438bd8` (initial commit); pages rewritten, `rxconfig.py` fixed — uncommitted changes
- Working tree: clean (all probe scripts removed; doc files updated)

## Current phase/task
**Phase 1.5 — Verification & Handoff (COMPLETE)**  
All Phase 0–1 core services complete, Supabase verified, UI fully wired to live orchestration, local backend running at port 8000. Next agent/session: **deploy to Vercel.**

## What is already implemented
See `PROJECT_PROGRESS.md` under "Completed items" for the full list. The repository now contains:
- Complete Python domain layer, provider abstraction, and four generation adapters (FreeLLMAPI, Gemini, Groq, OpenAI)
- Prompt builder supporting all 8 modes plus preservation controls
- Paragraph-aware chunker with protected-span masking
- Humanizer service orchestration with pause/resume/cancel path
- Supabase SQL migrations (schema + RLS) — applied and verified on project `heemfvculxnpwiohfoqh`
- Vercel API route with `/api/humanize` POST endpoint (real orchestration, not stubbed)
- Reflex workspace page — rewired `WorkspaceState.humanize()` calls `handle_humanize()` directly from `api.routes` (no loopback)
- Reflex history page — proper `set_search_query` method, `@rx.var` filtered_documents, `rx.foreach`, `rx.cond`
- Reflex settings page — `settings_page()` function added with provider rows & status badge
- Unit tests for chunking, prompts, and service — **18 passing**
- Local backend verified: `python -m reflex run --backend-only` → port 8000, `/ping` → `pong`, `/_health` → `{"status":true}`

## Exact file(s) currently being changed
None actively mid-edit. All work complete.

## Last successful test/build/run command
```powershell
pytest tests/unit/ -v
```
Result: **18 passed** (5 chunking + 9 prompts + 4 humanizer), 2026-11-20.

```bash
python -m reflex run --backend-only
```
Result: Backend running at http://localhost:8000, ping/health endpoints responding OK.

## Current failure / blocker
- None — blocking item (Supabase config) is resolved; user supplies credentials via `.env.txt` (gitignored)
- Public sign-up must be disabled in Supabase Auth Dashboard after confirming owner account works
- Vercel deploy requires user action (push to GitHub + create Vercel project + set env vars)

## Single best next action
**User pushes repo to GitHub and deploys to Vercel**, then disables public sign-up in Supabase Auth Settings.

## Environment variables required on Vercel deployment

| Variable | Purpose | Source |
|----------|---------|--------|
| `SUPABASE_URL` | Supabase project URL | `https://heemfvculxnpwiohfoqh.supabase.co` |
| `SUPABASE_PUBLISHABLE_KEY` | Supabase anon key | Supabase dashboard |
| `SUPABASE_SECRET_KEY` | Supabase service-role key | Supabase dashboard |
| `GEMINI_API_KEY` | Google AI Studio API key | Google AI Studio |
| `GEMINI_MODEL` | Model name to use | `gemini-2.0-flash` |
| `PAID_PROVIDERS_ENABLED` | Keep as `false` | Leave false unless you have a paid plan |

## Files the next agent session must inspect first
1. `AGENT_HANDOFF.md` (this file)
2. `PROJECT_PROGRESS.md`
3. `DECISIONS.md`
4. `phrasia_domain.py` — root-level domain (no `src/phrasia` package exists)
5. `supabase/migrations/` — verify schema matches actual target
6. `tests/unit/` — review current test coverage before adding more
7. `rxconfig.py` — contains the re-entrant guard fix for RegistrationContext double-instantiation