Historical document written during the refactor. See README.md for the current state.

# Phrasia ΓÇö Step 1 Plan: Plan and Cleanup

Status: the deletion work below was executed in commit `bf8d291`. This plan records exactly what was removed, what survived, and the target tree. Step 1 finishes the remaining items: this plan file, `run.py`, the `backend/core/` rename, import fixes, and the leftover grep.

## (a) Files and folders to DELETE

All were deleted outright with file deletion / `git rm` ΓÇö none were merely ignored or commented out.

**Reflex / old UI**
- `rxconfig.py`
- `app/` ΓÇö `components.py`, `pages/history.py`, `pages/settings.py`, `pages/workspace.py`, `ui_tokens.py`
- `.web/`, `.states/`, `reflex.lock`, `phrasia.egg-info/`
- Reflex dependencies (`pyproject.toml` and its dependency set)

**Supabase / cloud data**
- `infrastructure/supabase/client.py`
- `supabase/migrations/001_initial_schema.sql`
- `supabase/migrations/002_rls_policies.sql`
- `supabase/migrations/003_grant_privileges.sql`
- All Supabase environment variables and their documentation

**Deployment / unused worker**
- `vercel.json` and all edge-function / route-handler configuration
- `api/routes.py` (the old in-process request handler)
- `infrastructure/jobs/worker_tick.py` and the surrounding unused job/queue code

**Dead code / duplication / mocks**
- `humanizer_layer.py`, `phrasia_domain.py`
- `core/` ΓÇö `ai_detector.py`, `chunking_service.py`, `humanizer_postprocess.py`, `humanizer_service.py`, `output_validator.py`, `prompt_builder.py`
- `providers/` ΓÇö `base.py`, `credentials.py`, `errors.py`, `model_catalog.py`, `router.py`, and `generation/` (`anthropic.py`, `custom.py`, `freellmapi.py`, `gemini.py`, `groq.py`, `openai.py`, `openai_compatible.py`, `openrouter.py`) ΓÇö the duplicate catalogs and plaintext credential store included
- `tests/unit/` ΓÇö all nine tests of the deleted code, including the mocked History sample
- Hardcoded sample document in the old History page

**Redundant docs / stray files**
- `PROJECT_PROGRESS.md`, `AGENT_HANDOFF.md`, `IMPLEMENTATION_LOG.md`
- `Phrasia_Project_Documents/` (architecture, master build prompt, PRD)
- Caches, build output and editor leftovers

## (b) Files to KEEP / MOVE

| Old item | Outcome |
|---|---|
| `core/chunking_service.py` | Rewritten as `backend/core/chunking.py` (lossless paragraph chunking) |
| `core/prompt_builder.py` | Rewritten as `backend/core/prompt.py` (modes, intensity, prompt) |
| `core/humanizer_service.py` | Rewritten as `backend/core/humanizer.py` (checkpointed, resumable jobs) |
| `core/ai_detector.py` | Rewritten as `backend/core/detector.py` (categorical local style signal) |
| `humanizer_layer.py`, `core/humanizer_postprocess.py` | Deliberately dropped; merged into the prompt, not re-implemented as a rewrite stage |
| `providers/*` | Rewritten as `backend/providers/` ΓÇö one catalog, adapters, registry, shared HTTP retry |
| `infrastructure/supabase/client.py` | Replaced by `backend/db/repository.py` (local SQLite, all SQL in one module) |
| `api/routes.py` | Replaced by thin routers in `backend/api/` |
| `app/pages/*` | Replaced by `frontend/src/pages/*.ts` (one module per page) |
| `README.md`, `DECISIONS.md` | Rewritten to match the shipped code |
| `docs/APIS.md` | New ΓÇö external API inventory with liveness checks |
| `.env.example` | Rewritten and un-ignored so it is committed |
| `requirements.txt`, `.gitignore` | Rewritten for the new stack |
| `tests/` | Replaced with 49 tests covering the kept logic |
| `backend/services/` | Renamed to `backend/core/` in this step to match the target tree |
| New in this step | `PLAN.md`, `run.py` |

## (c) New folder tree

```
phrasia/
Γö£ΓöÇΓöÇ backend/
Γöé   Γö£ΓöÇΓöÇ __init__.py
Γöé   Γö£ΓöÇΓöÇ main.py                 # FastAPI app, serves frontend/dist
Γöé   Γö£ΓöÇΓöÇ config.py
Γöé   Γö£ΓöÇΓöÇ api/                    # thin routers + deps/errors/schemas
Γöé   Γö£ΓöÇΓöÇ core/                   # chunking, prompts, humanizer, detector, similarity, documents
Γöé   Γö£ΓöÇΓöÇ providers/              # catalog, registry, base, adapters/
Γöé   ΓööΓöÇΓöÇ db/                     # repository.py ΓÇö the only SQL in the repo
Γö£ΓöÇΓöÇ frontend/
Γöé   Γö£ΓöÇΓöÇ index.html
Γöé   Γö£ΓöÇΓöÇ package.json
Γöé   Γö£ΓöÇΓöÇ tsconfig.json
Γöé   Γö£ΓöÇΓöÇ vite.config.ts
Γöé   ΓööΓöÇΓöÇ src/                    # main.ts, api.ts, types.ts, ui.ts, style.css, pages/
Γö£ΓöÇΓöÇ tests/
Γö£ΓöÇΓöÇ data/                       # local SQLite file, created at runtime, gitignored
Γö£ΓöÇΓöÇ docs/
Γöé   ΓööΓöÇΓöÇ APIS.md
Γö£ΓöÇΓöÇ .env.example                # committed
Γö£ΓöÇΓöÇ requirements.txt
Γö£ΓöÇΓöÇ run.py                      # python run.py ΓåÆ uvicorn on 127.0.0.1
Γö£ΓöÇΓöÇ PLAN.md
Γö£ΓöÇΓöÇ README.md
ΓööΓöÇΓöÇ DECISIONS.md
```
