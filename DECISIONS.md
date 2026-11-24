# Decision Log — Phrasia

Short, current decisions only. Older architecture notes were removed when the stack changed.

## D-001: Two languages, no UI framework
- **Date:** 2026-11-24
- Use Python for all logic and a plain TypeScript frontend (Vite + Tailwind, hash router). No component framework, no runtime npm dependencies.
- **Why:** enough interactivity for five small pages; much less tooling and a much smaller bundle than a framework.

## D-002: Local SQLite behind one repository module
- **Date:** 2026-11-24
- All SQL lives in `backend/db/repository.py`. Nothing else imports `sqlite3`.
- **Why:** a future online database can replace one module. For now the app needs no server, account or network database.

## D-003: No auth; bind to loopback only
- **Date:** 2026-11-24
- `require_owner()` exists in `backend/api/deps.py` and is used by every router. It is a no-op with a TODO.
- **Why:** the product is single-owner and local. Adding a login now would add surface without benefit. Do not expose the port.

## D-004: Similarity is local, not internet-wide
- **Date:** 2026-11-24
- Compare against the owner's reference library with word n-grams; label it "Local similarity signal only".
- **Why:** no free, dependable public plagiarism API was found that could be verified from this machine. Inventing one would be dishonest. This is the simplest useful implementation and it keeps text private.

## D-005: Style signal has no score or verdict
- **Date:** 2026-11-24
- Return a categorical label, named signals and a disclaimer. No percentage, no "AI Detected", and no humanize → scan → repeat loop in the UI.
- **Why:** keyword heuristics cannot establish authorship. A number would imply accuracy the code does not have.

## D-006: Raw-body uploads instead of multipart
- **Date:** 2026-11-24
- `POST /api/documents/extract` and `POST /api/plagiarism/references/upload` read raw bytes with the filename in the query string.
- **Why:** keeps `python-multipart` out of the dependency list. TXT/MD/DOCX cover the useful formats; PDF would need another parser.

## D-007: Durable jobs, in-process worker
- **Date:** 2026-11-24
- A job and one row per chunk are written before work starts. `BackgroundTasks` runs the worker; polling drives the UI. A restart marks active jobs `paused`, and retry only processes unfinished chunks.
- **Why:** gives resume/cancel/retry semantics without a queue server. Ambiguity resolved: a single uvicorn process is enough for one owner.

## D-008: Paid models off by default
- **Date:** 2026-11-24
- Catalog entries marked `paid` are filtered out unless `PAID_MODELS_ENABLED=true`.
- **Why:** prevents accidental billing.

## D-009: One provider catalog
- **Date:** 2026-11-24
- `backend/providers/catalog.py` defines provider specs, default models and the model list. Adapters only implement transport.
- **Why:** the previous duplicate catalogs drifted apart.

## D-010: No local models
- **Date:** 2026-11-24
- No model runtime is installed or invoked. All rewriting goes through external HTTP APIs.
- **Why:** machine constraints and the product requirement to stay light.

## D-011: Keys in local storage, plainly labelled
- **Date:** 2026-11-24
- Settings keys are stored in the local SQLite database as text; `.env` is the other supported source. The Settings page states this openly, and the API masks keys.
- **Why:** encryption would require a master secret that is just as local, giving little extra protection for a loopback-only app. Revisit if the app is ever hosted.

## D-012: Public base URLs only
- **Date:** 2026-11-24
- Custom endpoints must use `http(s)` and must not be loopback, private or link-local addresses.
- **Why:** the product calls online APIs only; blocking local addresses prevents accidental use of a local model server and narrows server-side request forgery risk.
