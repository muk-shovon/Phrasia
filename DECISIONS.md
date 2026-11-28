# Decisions

- Online-first rewriting: hosted providers do the style work, and the deterministic rule engine is the safety pass and offline fallback. No local ML model is downloaded or run.
- Providers are OpenAI-compatible (Groq, Cerebras, Mistral, OpenRouter, Together) or Gemini, called through stdlib `urllib.request`. No new runtime dependency.
- Keys come from environment variables or the Settings page. A saved key lives in `DATA_DIR/.env` (mode `0600` on POSIX); environment variables take precedence. The API returns only `configured` and `key_source`, never key material, and keys are never logged.
- Fallback chain: retry with backoff, move to the next ready provider on `429`/`5xx`/timeout, then run the local engine when the fallback is enabled. Strict mode raises instead.
- Pipeline: clean → parse → protect spans → segment sentences → analyze (length, opening, pattern hits, burstiness, opener repetition, hedge/quantifier density, pronoun mix) → per-sentence operation plan (only synonym/phrase swap, clause reorder, split, merge adjacent pair, new opening, punchy short, nearly unchanged; never active↔passive voice; natural short/medium/long mix) → one hosted call per sentence or adjacent pair → restore spans → validate + meaning check → retry once stricter else keep original → rescore whole text → re-humanize only flagged sentences up to N rounds (light=1, medium=2, heavy=3, ninja=4) → local skill pass → assemble.
- Intensity: total re-humanize rounds. `light=1`, `medium=2`, `heavy=3`, `ninja=4`. Round 1 rewrites planned sentences; later rounds rescan the whole text and re-humanize only flagged sentences. Stop early when no sentence is flagged or the pattern density is at or below the target.
- A hosted draft is rejected when it changes numbers, names, URLs, citations or quotes, drops a negation, breaks a placeholder, fails grammar, or drifts outside the length ratio. It is retried once with a stricter prompt; then the original sentence is kept.
- The validator uses a relaxed content-retention threshold (~0.55) for hosted drafts, because paraphrase lowers exact word overlap.
- Learning tables: `example_pairs`, `feedback`, and `llm_cache`. Retrieval ranks 3–5 examples by word overlap, length closeness and rating, filtered by tone, strength and operation. Accepted or edited rewrites become examples.
- The voice/style-profile feature was removed. Voice features removed for now; can be re-added later. No `style_profiles` table, no `/api/style-profiles` routes, no writing samples in prompts, and no "match my voice" claim. The old table is backed up to `data/backups/style_profiles_<timestamp>.json` and then dropped on startup. The `Voice` and `Passive voice` headings in `docs/reference/humanizer-SKILL.md` are writing-craft references and were kept. Removed files: no standalone voice module existed; style-profile code was removed inside `backend/api/routes_settings.py`, `backend/api/schemas.py`, `backend/db/repository.py`, `backend/engine/llm/settings.py`, `backend/engine/llm/retrieval.py`, `backend/engine/llm/prompts.py`, `backend/engine/humanize.py`, `backend/core/humanizer.py`, `frontend/src/pages/settings.ts`, `frontend/src/types.ts`, `frontend/src/api.ts`, `frontend/src/pages/humanize.ts`, `frontend/src/main.ts`, and `tests/test_llm.py`.
- The prompt templates live in `backend/engine/llm/prompts/*.md` and are loaded from disk, so wording can change without touching code.
- Cache keys include provider, model, temperature, max tokens, system prompt and user prompt.
- Online mode only runs when a provider key exists and online rewriting is enabled. Otherwise the deterministic path runs unchanged, which keeps tests offline and deterministic.
- `intensity` extends the existing `strength` with `ninja`; the offline fallback maps `ninja` to `heavy`.
- Progress is reported through an in-memory job API (`POST /api/humanize/jobs`, `GET /api/humanize/jobs/{id}`) that the UI polls. The synchronous `/api/humanize` stays for scripts.
- Only the sentences being rewritten are sent to the provider, each in its own call, plus read-only previous/next context, a few local example pairs, and the banned-phrase list. The whole write-up is never sent at once. Documents, references, history, keys and feedback stay local.
- Safety first: numbers, names, URLs, code, quotes, hedges and negations are preserved; unsafe candidates are rejected and the source sentence stays.
- SQLite in `data/phrasia.db` stores documents, versions, references and learning tables. `require_owner()` is a no-op; the server binds to 127.0.0.1.
- Style signals use our own pattern list only: no verdict, percentage or detector name.
- `ai_patterns.json` is the single catalog; the Humanizer, Style check and Style Signal page all call `skill.scan()`.
- Tier A is deterministic editing, tier B is validator-and-ranker editing, and tier C is review only. Section 26 is skipped because the app has no thread context.
- Sections 1–5 and 22 act on one sighting. A weak signal needs two other sections in its paragraph or three sightings in the document.
- With Replace dashes enabled, every prose em/en dash is replaced even when it is the only signal; code, links and paths stay protected.
- A deletion is recorded by rule and is rejected when its span contains a number, name, link, protected text, quote, hedge or negation.

## Public release defaults

- The simplest end-user path is `python run.py`. When dependencies are unavailable, the launcher creates `.venv`, installs `requirements.txt`, and restarts itself with that environment through a subprocess.
- `frontend/dist/` is committed deliberately. It is generated release output, but this exception lets users run the app with Python alone; Node.js remains a contributor requirement.
- Runtime and development dependencies use compatible ranges. The installed local versions set the lower bounds, and the next major versions are excluded.
- MIT is the default project license.
- Generic generated and runtime files use `.gitignore`; project-specific local-only files use the private `.git/info/exclude` file.
- CI checks Windows and Linux with Python 3.11 and 3.13 plus Node.js 20, running the Python and frontend validation commands on pushes and pull requests.
