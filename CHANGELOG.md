# Changelog

All notable changes to Phrasia are recorded here. This file follows the categories from [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Online-first Humanizer: hosted rewriting through Groq, Cerebras, Gemini, Mistral, OpenRouter, or Together, with a provider fallback chain, local timeout/retry, and an offline rule-engine fallback.
- Settings page for provider keys, models, connection tests, temperature, timeout, early-stop density, and cache clearing.
- Intensity levels (`light`, `medium`, `heavy`, `ninja`), live per-pass progress through a job API, and re-humanize for a single flagged passage.
- Local learning tables: example pairs, feedback, and an LLM response cache, with seed examples and feedback controls in the UI.
- Hosted prompts stored as editable Markdown in `backend/engine/llm/prompts/`.
- Deterministic humanizer skill pass with a shared 26-section catalog, tiered edits, review signals, and fixture coverage.
- First-run Python bootstrap, public contribution guide, GitHub templates, cross-platform CI, and MIT license.
- Committed frontend bundle so end users need only Python.

### Changed

- Online-first rewriting is now sentence-by-sentence. One provider call rewrites one sentence or adjacent pair; never the whole write-up. Planner uses only word/phrase swap, clause reorder, split, merge, new opening, punchy short, or nearly unchanged; never active↔passive voice. Limited concurrency (~4), cache keyed by `(sentence, operation, tone, strength)`, meaning check, stricter retry then keep original, rescore and re-humanize only flagged sentences for `light=1`/`medium=2`/`heavy=3`/`ninja=4` rounds.
- Local rule engine stays for pre/post-processing, validation, and offline fallback. No local ML model.
- Studied `rudra496/StealthHumanizer` (MIT); summary in `docs/NOTES.md`, credit in `docs/THIRD_PARTY.md`.
- `example_pairs` gains `operation`; retrieval filters by tone, strength, operation; accepted/edited per-sentence rewrites are saved. Feedback gains `operation`.
- Frontend adds sentence-level diff with operation labels, per-sentence re-humanize/revert, per-sentence thumbs up/down, progress bar, intensity, and Settings provider/model/key + Test Key + offline toggle. UI note: writing aid, no guarantee on third-party detectors.
- Docs updated to online-first with offline fallback; state only rewritten sentences leave the machine. `SUMMARY.md` restored. `docs/NOTES.md` rewritten.
- Backend is now online-first with a deterministic safety pass and offline fallback; the rule engine no longer runs alone by default when a key is configured.
- Humanizer, Settings, and docs now describe what is sent to a provider and what stays local.
- Humanize responses include a `meta` block with mode, provider, model, rounds, density and cache information.
- Reworked the backend around the Python-only rule engine, validators, ranker, local style scanner, and local SQLite repository.
- Updated the Humanizer report and review interface, launcher, dependency ranges, and public documentation.
- Separated runtime and development Python dependencies.

### Removed

- The voice/style-profile feature was removed for now; it can be re-added later, restore from `pre-voice-removal`. The app no longer claims to match an author's voice. Removed the `style_profiles` table (with a backup-then-drop migration), `repository.list_style_profiles`/`get_style_profile`/`create_style_profile`/`delete_style_profile`, `GET/POST/DELETE /api/style-profiles`, `samples_for()` in `backend/engine/llm/retrieval.py`, `samples_block()` in `backend/engine/llm/prompts.py`, `style_profile_id` on requests and settings, and the "Your voice" card in `frontend/src/pages/settings.ts`. Removed files: no standalone voice module was present; removals were edits inside the files above plus deleted style-profile routes.
- The "no network access" and "no API key" product claims, which no longer describe the app.
- Duplicate style matching and obsolete provider-era launcher behavior.
- Generated environments, caches, local databases, and machine-specific files from the current Git index.

## 2026-11-24 — Local app and frontend refactor

### Added

- FastAPI backend with a Vite and TypeScript frontend.
- Local plagiarism reference workflow, document history, style-signal page, and text/DOCX export.
- Two-column Humanizer interface, diff review, accessibility improvements, and the current visual design.

### Changed

- Replaced the earlier UI and cloud-oriented storage structure with local browser pages and SQLite persistence.
- Consolidated API routes and page modules around the local application.

## 2026-11-23 — Initial repository

### Added

- Initial Phrasia application and repository structure.
