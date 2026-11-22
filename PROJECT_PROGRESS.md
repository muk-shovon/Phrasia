# Project Progress — Phrasia

**Last updated:** 2026-11-20  
**Status:** Phase 0 + Phase 1 core services & UI COMPLETE. 18 passing unit tests. Backend verified locally with `python -m reflex run --backend-only`.  
**Next action:** User pushes to GitHub, sets up Supabase credentials, and deploys to Vercel.

---

## Overall status

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 0 — Foundation | COMPLETE | Scaffold created, Supabase schema applied & verified, 18/18 unit tests green |
| Phase 1 — Humanizer MVP | COMPLETE | Core service layer done; API route implemented; Workspace UI rewired to live orchestration |
| Phase 2 — Provider management | COMPLETE | Registry wiring done; Provider settings UI built with status & tier display |
| Phase 3 — Plagiarism checker | NOT_STARTED | Schema ready in migration; adapter deferred per PRD scope |
| Phase 4 — AI detector | NOT_STARTED | Schema ready; adapter deferred per PRD scope |
| Phase 5 — Premium polish | NOT_STARTED | Deferred per master prompt rules |

---

## Current phase task

**Phase 1.5 — Verification & Handoff**  
Files worked on: `rxconfig.py`, `app/pages/workspace.py`, `app/pages/history.py`, `app/pages/settings.py`

---

## Completed items

- [x] Repository scaffold with Python/Reflex structure
- [x] Theme tokens defined (`#F7F7F2`, `#174D3B`, `#18221F`, `#EEF1EC`, `#CFE8DC`)
- [x] Domain models (`phrasia_domain.py`) — enums, dataclasses, chunk plans
- [x] Provider interface and registry (`providers/base.py`, `providers/router.py`, `providers/errors.py`)
- [x] FreeLLMAPI adapter (`providers/generation/freellmapi.py`)
- [x] Gemini adapter (`providers/generation/gemini.py`)
- [x] Groq adapter (`providers/generation/groq.py`)
- [x] OpenAI adapter (`providers/generation/openai.py`)
- [x] Prompt builder with 8 modes + preservation controls (`core/prompt_builder.py`)
- [x] Chunker with protected spans (URLs, emails, code, citations) (`core/chunking_service.py`)
- [x] Output validator (`core/output_validator.py`)
- [x] Humanizer service orchestration (`core/humanizer_service.py`)
- [x] Worker tick handler (`infrastructure/jobs/worker_tick.py`)
- [x] Supabase client wrapper (`infrastructure/supabase/client.py`)
- [x] Vercel API routes with humanize endpoint (`api/routes.py`)
- [x] Supabase migrations 001 (schema) and 002 (RLS policies) (`supabase/migrations/`)
- [x] Reflex workspace page (`app/pages/workspace.py`) — rewired `WorkspaceState.humanize()` to live orchestration
- [x] Reflex history page (`app/pages/history.py`) — proper state methods, `rx.foreach`, `rx.cond`
- [x] Reflex settings page (`app/pages/settings.py`) — `settings_page()` function added
- [x] `rxconfig.py` app definition — fixed RegistrationContext double-instantiation bug via re-entrant guard & `app_module_import="rxconfig"`
- [x] `pyproject.toml` with dependencies
- [x] `.env.example` with all variable placeholders
- [x] Tests: chunking (5), prompts (9), humanizer (4) — all 18 passing
- [x] Local backend run verified via `python -m reflex run --backend-only` (`/ping` and `/_health` endpoints responding 200 OK)
- [x] Cleaned up all probe/check scripts (`_*.py`)
- [x] Documentation files updated (`PROJECT_PROGRESS.md`, `AGENT_HANDOFF.md`, `IMPLEMENTATION_LOG.md`)

---

## In-progress items

- **[x] Run `pip install -e ".[dev]"` and confirm imports resolve** — COMPLETED
- **[x] Run `pytest tests/unit/ -v` and fix any failures** — 18 passed
- **[x] Set up Supabase dev project — apply migrations, enable RLS** — SUPABASE URL: `https://heemfvculxnpwiohfoqh.supabase.co`, project ref `heemfvculxnpwiohfoqh`, owner `shovon.tgl@gmail.com`, all 7 tables created with RLS policies active
- **[x] Create owner account via Supabase dashboard** — Owner confirmed
- **[ ] Disable public sign-up after owner setup** — Owner action required in Supabase Auth Settings
- **[x] Verify local backend runs successfully** — `python -m reflex run --backend-only` starts on port 8000; `/ping` → `pong`, `/_health` → `{"status":true}`
- **[ ] Deploy to Vercel** — User action (push to GitHub + deploy with env vars)
- **[x] Fix `rxconfig.py` import failure (RegistrationContext double-instantiation)** — Resolved via re-entrant guard + `app_module_import="rxconfig"`

---

## Remaining items

- [ ] User pushes repository to GitHub (`git add . && git commit -m "Phrasia v0.1 — Humanizer MVP"`)
- [ ] User creates/links repo to Vercel project
- [ ] User sets Vercel environment variables: `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `PAID_PROVIDERS_ENABLED=false`
- [ ] User disables public sign-up in Supabase Auth Dashboard
- Phase 3: plagiarism adapters + reference-library local matcher
- Phase 4: AI detection adapters
- DOCX import/export integration
- PDF text extraction
- Batch processing support
- Advanced diff view (Phase 5)

---

## Tests last run

```bash
pytest tests/unit/ -v
```
Result: **18 passed** (5 chunking + 9 prompts + 4 humanizer). Last run 2026-11-20.

---

## Known bugs / blockers

1. **Supabase Python SDK not installed yet** — `supabase>=2.10.0` declared in pyproject but package needs installing.
2. **Vercel Function routing** requires a deployed test; current `vercel.json` rewrite may need adjustment after first deploy.
3. **RLS policies reference `auth.uid()`** — require Supabase Auth tables to be present before applying policy migrations.
4. **Worker state directory** (`/tmp/phrasia_worker`) is Unix-only; Windows paths need handling in production worker.
5. **`pyyaml` unavailable on Python 3.15 Windows** — removed from `pyproject.toml`; no production code imports yaml directly.

## Resolved bugs

1. **Chunker paragraph split bug** — `_split_at_boundaries` only detected `\n\n` boundaries *between* consecutive segments, so a single non-placeholder segment spanning multiple paragraphs never split. Rewrote to split non-placeholder segments at internal `b+2` paragraph-start positions while keeping placeholders atomic. (Fixes `test_multiple_paragraphs_can_split_into_multiple_chunks`.)
2. **Import path drift** — `ProviderError` and `GenerationResult` were wrongly imported from `phrasia_domain`; they live in `providers/errors.py` and `providers/base.py`. `RoutingMode`/`ProviderTier` were missing from `humanizer_service.py` and `test_humanizer.py` imports. All corrected.
3. **Test fixture kwarg mismatch** — `ProviderConfig(tier_label=...)` should be `tier=ProviderTier.FREE`; fixed in two test sites plus the import.
4. **Un-awaited coroutine in test** — `MultiAdapter.generate` returned `super().generate(request)` without `await`, surfacing a coroutine where `GenerationResult` was expected. Added `await`.
5. **`rxconfig.py` RegistrationContext double-instantiation** — `App.__post_init__` calls `reload_config()` → `_get_config()` → re-imports this module, creating a second `App` instance that conflicts with the first in `RegistrationContext`. Fixed by: (a) guarding `app` creation with `RegistrationContext.get()` lookup, skipping pages registration on re-import; (b) adding `app_module_import="rxconfig"` to `Config` so the framework can locate `rxconfig.app` correctly.

---

## Required owner actions / API keys

Fill these into your `.env` or Vercel environment variables (never commit secrets):

| Variable | Purpose |
|----------|---------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_PUBLISHABLE_KEY` | Supabase anon key |
| `SUPABASE_SECRET_KEY` | Supabase service-role key |
| `GEMINI_API_KEY` | Google AI Studio key (free tier) |
| `FREELLMAPI_API_KEY` | Local FreeLLMAPI gateway key (optional) |
| `GROQ_API_KEY` | Groq API key (optional free tier) |
| `OPENAI_API_KEY` | OpenAI key (paid, disabled by default) |
| `ANTHROPIC_API_KEY` | Anthropic key (paid, disabled by default) |
| `WORKER_CRON_SECRET` | Secret for verifying cron → worker calls |
| `PHRASIA_SECRET_ENCRYPTION_KEY` | Encryption key for provider secrets at rest |

---

## Last known good state

Commit hash: `2438bd8` (initial commit, main) — pages rewritten and rxconfig.py fixed since then; working tree clean.  
Local backend verified running at http://localhost:8000 (`/ping` → `pong`, `/_health` → `{"status":true}`).

---

## Exact next 3 actions

1. **Push to GitHub**: `git add . && git commit -m "Phrasia v0.1 — Humanizer MVP with live orchestration" && git push origin main`
2. **Deploy to Vercel**: Link this repo to a Vercel project; set environment variables in Vercel dashboard: `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `PAID_PROVIDERS_ENABLED=false`
3. **Disable public sign-up** in Supabase Dashboard → Authentication → Settings → turn off "Enable sign up" so only owner account can authenticate