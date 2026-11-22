# Product Requirements Document (PRD)

## Phrasia — Product Requirements Document

**Document type:** Product Requirements Document  
**Version:** 2.0  
**Status:** Approved product direction; implementation-ready draft  
**Prepared:** 19 November 2026  
**Primary audience:** OpenCode, Claude Code, or another coding agent  
**Companion documents:** `Phrasia_Architecture.md`, `Phrasia_OpenCode_Master_Build_Prompt.md`

---

## 0. Instructions for the coding agent

Read this PRD and `Phrasia_Architecture.md` completely before changing or creating project files.

The most important delivery rule is:

> **Build a usable AI Humanizer first. Do not start by implementing every planned module.**

Implement the project phase by phase. Phase 1 must result in an hosted application that the owner can open through its private Vercel URL, paste or upload a document, humanize it using a configured external API, review the result, and copy/export it. Plagiarism checking and AI detection are later phases.

Before each phase:

1. Summarize the phase scope and acceptance criteria.
2. Inspect the repository and preserve working code.
3. Propose a short implementation plan.
4. Implement only that phase unless the owner explicitly approves expanding scope.
5. Run relevant tests, type/static checks where available, and a local launch/build check.
6. Report completed items, known limitations, configuration required, deployment status, and the next phase.
7. Update `PROJECT_PROGRESS.md`, `AGENT_HANDOFF.md`, `IMPLEMENTATION_LOG.md`, and `DECISIONS.md` after every coherent milestone.

Do not silently change the approved technology stack. Do not add Local LLM functionality. Do not enable paid API usage by default.

---

## 1. Product overview

### 1.1 Product name and identity

**Phrasia** is the official product name. Proposed tagline: **“Words, Refined.”** (provisional; the approved brand name is Phrasia) Product descriptor: **“An intelligent workspace for better writing.”**

### 1.2 Product summary

A private, Python-first web application for improving written content, with three planned core capabilities:

1. **AI Humanizer / Rewriter** — the first and highest-priority capability. It rewrites text into a clearer, more natural, and more suitable style while attempting to preserve the original meaning, facts, names, numbers, citations, URLs, and structure.
2. **Plagiarism / Similarity Checker** — checks text against a provider's source corpus and, separately, against documents indexed in the user's own Supabase-backed reference library.
3. **AI Writing Detector** — requests an estimate from a specialist third-party detection API and presents the provider's score and any supported sentence-level details.

The system will be built with Python as the primary development language. Reflex will be used for the Python-authored web interface and application framework. External APIs will provide generative AI, hosted plagiarism checking, and hosted AI detection.

### 1.3 The product's key operating principle

**Free-first, paid-ready, Python-orchestrated, and no Local LLM.**

- Use free/trial API access when the configured provider and account actually offer it.
- Keep paid providers supportable through provider adapters, but do not call a paid provider unless the owner explicitly enables and authorizes it.
- Use Python for application logic, document parsing, chunking, queues, persistence, local reference matching, reports, and API orchestration.
- Do not run a Local LLM. Do not add Ollama, llama.cpp, local transformer inference, or another local generative model.
- When an API is unavailable, do not pretend that Python can reproduce the same AI generation or Internet-wide analysis. Save the job, offer another configured provider, or pause it.

### 1.4 Intended initial user

One owner using the private hosted application deployed to Vercel and backed by Supabase. The first release is a private, single-owner application. Supabase Auth is required because the deployed URL is publicly reachable; public sign-up must be disabled after the owner account is created. Subscriptions, billing pages, teams, and multi-tenant administration are out of scope.

The architecture should avoid decisions that would make future expansion impossible, but public SaaS functionality must not delay the personal MVP.

---

## 2. Product goals and non-goals

### 2.1 Goals

- Deliver a working Humanizer before the other two main tools.
- Let the owner paste text or import a document and humanize it through a configured external API.
- Avoid an arbitrary product-level word cap. Support long documents by splitting them into provider-compatible chunks and processing them sequentially or with controlled concurrency.
- Preserve completed work and resume after rate limits, network failures, application restarts, or user pauses.
- Keep API providers replaceable. Provider-specific request/response logic must not leak into UI code or core business logic.
- Support free and paid providers in the same architecture.
- Make paid usage impossible by default and require explicit approval.
- Keep API keys and document content out of frontend code, browser storage, source control, and normal application logs.
- Add Python-based local similarity matching against a user-controlled Supabase reference library in a later phase.
- Add specialist API-based AI detection in a later phase.
- Keep the interface polished and responsive, while prioritizing functionality over visual perfection in the first release.

### 2.2 Non-goals for the initial release

- No Local LLM or local generative model.
- No promise that humanization will make text pass any AI detector.
- No guarantee that an AI detector can prove authorship.
- No claim of Internet-wide plagiarism detection from a local Python corpus.
- No public user registration, payment checkout, subscriptions, team workspaces, or multi-tenant SaaS administration.
- No browser extension, Word add-in, Google Docs add-on, or mobile app.
- No OCR requirement in the first release.
- No full preservation of complex PDF/DOCX layouts, tracked changes, embedded objects, or every document-specific feature in the first release.
- No hardcoded assumption that a provider's free tier, pricing, model name, quota, or terms will remain unchanged.

---

## 3. Product principles and constraints

### 3.1 Humanizer-first delivery

The initial application must be useful even if Plagiarism Checker and AI Detector do not yet exist. The first development milestone is not a static dashboard or a mockup: it must perform a real rewrite through a configured API.

### 3.2 No arbitrary application word limit

The UI must not impose an arbitrary small limit such as 500, 1,000, or 2,000 words. However, the system must be honest about external constraints:

- Providers impose request, context, output-token, rate, and quota limits.
- Free quotas can be exhausted.
- A long document can take a long time and may require multiple requests.
- Provider/model capability may change.

Therefore, the application will use **document chunking and resumable processing**, not claim mathematically unlimited processing.

### 3.3 No Local LLM

There is no local generative fallback. If all configured Humanizer APIs are unavailable or their quotas are exhausted, the app must save the job and pause it. It must not silently switch to a low-quality Python synonym replacement routine and label that result as AI humanization.

Python algorithms may still be used for:

- parsing and reconstructing documents;
- text normalization and exact/near-exact matching against the owner's Supabase-backed reference library;
- counting words and characters;
- detecting duplicate input;
- sentence/paragraph segmentation;
- formatting, validation, and report assembly.

### 3.4 Free-first and paid-ready

- Free or trial providers can be configured as primary providers.
- Paid providers may be configured but must be disabled by default.
- Paid calls require an explicit action/authorization, a configured spending ceiling, and a per-job cost estimate or warning where a credible estimate is available.
- The default paid budget is **USD 0** and paid provider access is **OFF**.
- A free quota exhaustion event must never automatically trigger a paid request unless the owner has deliberately enabled a clearly defined paid-authorization policy.
- The UI must always identify which provider and model processed a job.

### 3.5 Content integrity

The Humanizer should improve readability, flow, clarity, tone, and structure. It must not invent sources, facts, citations, data, names, or quotations. It must not claim to guarantee detector evasion or a specific AI detector score.

---

## 4. Main product modules

### Module 1 — Writing Workspace (Phase 1)

The primary work area for pasting, importing, editing, rewriting, reviewing, and exporting text.

**Required capabilities:**

- Large text input area with paste support.
- Input word count, character count, and paragraph count.
- Clear input and sample text controls.
- Upload `.txt` in the first usable release. Basic `.docx` import/export is the first document-format enhancement (Phase 1.1 / Phase 2) and must not delay the first working Humanizer.
- Export rewritten text as `.txt` in Phase 1; add `.docx` export with the document-format enhancement.
- Responsive layout for desktop first, usable on tablet/mobile widths.
- Original and rewritten text views.
- Copy rewritten output.
- Save document metadata, job state, original/output versions, and history in Supabase Postgres; store uploaded files and larger text artefacts in a private Supabase Storage bucket.
- Clear validation and error messages.

**Later enhancements:** PDF text extraction, richer DOCX formatting preservation, document outline, find/replace, keyboard shortcuts, split-screen diff, and batch upload.

### Module 2 — AI Humanizer (Phase 1; highest priority)

This module is the first functional release and the core purpose of the initial project.

#### 2.1 Input and output

- Accept pasted text and imported `.txt` text in Phase 1; basic `.docx` import is the next document-format increment.
- Preserve paragraph order.
- Preserve headings, lists, URLs, citations, quotations, names, numbers, and formatting markers as far as the selected format and provider allow.
- Clearly warn the user when an import format contains elements that cannot be fully preserved.
- Show original and rewritten versions separately.
- Provide copy, save-version, regenerate, and download actions.

#### 2.2 Humanization modes

The initial set should be small and useful. Implement these modes first:

1. **Natural / Standard** — improve natural flow and readability without changing meaning.
2. **Professional** — polished professional/business language.
3. **Academic** — formal, precise, restrained language; preserve citations and avoid inventing references.
4. **Simple** — simpler vocabulary and clearer sentences.
5. **Conversational** — approachable, natural tone.
6. **Concise** — remove unnecessary wording while preserving key information.

Add an **Advanced Custom Instruction** field. Do not add dozens of modes before the initial modes work well.

#### 2.3 Rewrite controls

- Tone/mode selector.
- Rewrite intensity: Light, Balanced, Strong. Default: Balanced.
- Preserve original meaning: ON by default.
- Preserve facts, numbers, dates, and proper nouns: ON by default.
- Preserve citations, quotations, and URLs: ON by default.
- Preserve headings/lists/paragraph structure: ON by default.
- Optional custom instruction.
- Target language: default to the input language / do not translate unless requested.

#### 2.4 Quality requirements

- Do not intentionally change factual claims.
- Do not fabricate citations or source links.
- Do not remove a citation just to improve sentence flow.
- Do not rewrite text inside explicitly protected quotation blocks unless the user turns that protection off.
- Do not alter code blocks, URLs, email addresses, numeric identifiers, or reference strings unless explicitly requested.
- Avoid repetitive phrases and unnecessary length inflation.
- Avoid changing the user's argument or conclusion.
- When a provider response appears truncated or malformed, do not silently accept it as a complete document.
- A rewritten result must be labelled as AI-assisted rewriting, not as verified human-authored text.

#### 2.5 Long-document processing

The application must not rely on sending the entire document in one request. It must:

1. Estimate input size for the selected provider/model.
2. Split the document at natural boundaries (document sections, headings, paragraphs, and sentences).
3. Build chunks within a configurable token/character budget derived from the provider/model's limits, with a safety margin.
4. Keep chunk order and stable IDs.
5. Carry document-wide instructions and a small amount of relevant context into each chunk.
6. Preserve boundary text and avoid duplicated or missing sentences.
7. Process chunks through a persistent job queue.
8. Save each completed chunk immediately.
9. Resume from the first incomplete chunk after a failure or restart.
10. Assemble output in original order.
11. Run structural/length checks and flag suspicious missing or duplicate sections.

**Important:** A chunk size is a technical provider setting, not a user-facing document word limit. The owner should be able to process a long document over multiple calls while quotas and provider limits permit.

#### 2.6 Job controls

- Start processing.
- Pause job.
- Resume job.
- Cancel job.
- Retry failed chunk.
- Retry remaining chunks.
- View progress: completed chunks, total chunks, current status.
- View provider/model currently being used.
- Show a meaningful message if paused because of a rate limit or exhausted quota.

Supported job statuses:

`DRAFT`, `QUEUED`, `RUNNING`, `PAUSE_REQUESTED`, `PAUSED_USER`, `PAUSED_RATE_LIMIT`, `PAUSED_QUOTA`, `PAUSED_PROVIDER_ERROR`, `FAILED`, `CANCELLED`, `COMPLETED`.

### Module 3 — API Provider Management (Phase 1 basic; Phase 2 expanded)

The application must be provider-independent from the beginning.

**Phase 1 minimum:**

- One working Humanizer provider adapter (Gemini API is the proposed initial provider).
- Provider name and model displayed in the UI.
- API key configured via backend environment variable, never hardcoded.
- Provider connection/test action or a safe test request.
- Clear setup instructions in README.
- No paid provider call by default.

**Phase 2 expansion:**

- Add Groq as another potential free-tier provider (subject to current account/model quotas).
- Add OpenAI and Anthropic adapters as paid-capable providers.
- Add provider enable/disable controls.
- Add preferred provider and fallback priority.
- Add a secure API settings interface if needed. Secrets must be encrypted at rest or remain in environment variables; never store plaintext API keys in ordinary application settings.
- Add usage and error history.
- Add manual provider selection per job.
- Add Free-only and Hybrid modes.

**Provider labels must be configurable.** Do not permanently hardcode a provider as “free”; free/trial status depends on account, model, region, quota, and current commercial terms.

### Module 4 — Document Library and History (Phase 1 basic; Phase 2 enhanced)

**Phase 1 minimum:**

- Save document title, original text, selected rewrite options, output text, provider/model, timestamps, and job status.
- Reopen a completed or interrupted rewrite.
- Maintain at least the latest successful output version.
- Delete a document and its related data.

**Phase 2 enhancements:**

- Multiple versions per document.
- Rename and search documents.
- Filter by status/date/provider.
- Compare versions.
- Export DOCX/PDF.
- Batch upload and batch job management.

### Module 5 — Plagiarism / Similarity Checker (Phase 3)

This is not part of the first Humanizer release.

The module must distinguish between two kinds of checks:

**A. External provider scan**

- Use a specialist plagiarism API such as Quetext or Copyleaks when configured.
- Display the provider's actual similarity score and matched sources.
- Preserve provider report IDs, source links, and any source-level percentages the provider returns.
- Respect provider request limits, billing terms, and retention policy.
- Do not fabricate missing source information.

**B. Local reference-library matching**

- Allow the owner to index documents they own or are allowed to use.
- Implement exact matching, n-gram overlap, and optional TF-IDF/semantic-style comparisons only against indexed documents.
- Label the result **Local reference-library similarity**, not Internet plagiarism.
- Explain which documents were searched and the size/scope of the local corpus.
- Use an appropriate, clearly defined denominator for any percentage.

**Do not** label a local-corpus match percentage as an Internet-wide plagiarism score. Do not scrape sites or index copyrighted sources without permission or a lawful basis.

### Module 6 — AI Writing Detector (Phase 4)

This is not part of the first Humanizer release.

- Integrate a specialist AI detection API (Sapling is a candidate; GPTZero and Copyleaks can be evaluated as alternatives).
- Display the provider's raw score, verdict, model/version if returned, low-confidence/insufficient-text warnings, and sentence-level details if supported.
- Preserve the provider's original scale and document its meaning. Normalize to a UI percentage only when the mapping is mathematically clear and documented.
- Do not assume `human_score = 100 - ai_score` unless the provider explicitly defines complementary scores.
- Warn users that AI detectors can produce false positives and false negatives and cannot conclusively establish authorship.
- Detect unsupported languages and show an explicit limitation. Do not imply that Bengali detection is reliable unless the selected provider explicitly supports it and testing confirms acceptable behavior.

### Module 7 — Reports and Export (Phase 3–5)

- Humanizer report: input name, date, mode, provider/model, processing status, output, warnings, and version history.
- Plagiarism report: provider, scope of search, score, sources, highlighted passages, and timestamp.
- AI detection report: provider, model/version, score, confidence warnings, sentence details, and timestamp.
- Export to TXT first; DOCX next; PDF report later.
- Reports must make the analysis provider and scan scope visible.

### Module 8 — Settings, Authentication, and Privacy (Phase 0/1 basic; Phase 2 expanded)

- Supabase Auth owner sign-in and sign-out.
- Protected routes and owner-only access; disable public sign-up after owner account creation.
- App theme and default Humanizer settings.
- Provider selection and connection status.
- Supabase-backed document retention settings.
- Delete all owner documents, jobs, versions, reports, and associated Supabase Storage objects.
- API usage display where data is available.
- Paid API disabled by default.
- Monthly paid-spend cap defaulting to USD 0.
- Show provider data handling notice before first use of a provider.

---

## 5. User experience and page structure

### 5.1 Initial navigation

Keep the first release small:

- **Workspace** — main Humanizer screen.
- **History** — saved documents and rewrite jobs.
- **Settings** — default mode and API configuration status.

Do not create empty pages for future Plagiarism, AI Detector, Admin, or Billing features. They can be introduced when implemented.

### 5.2 Workspace layout

Desktop layout:

- Left: input editor and document controls.
- Right: output panel.
- Top: document title, status, word/character counts.
- Toolbar: mode, intensity, preservation toggles, custom instruction.
- Primary action: **Humanize Text**.
- During processing: progress, pause, resume, cancel controls.
- After completion: Copy, Download, Save Version, Regenerate.

On smaller screens, stack the panels vertically and keep controls accessible.

### 5.3 Phrasia brand and visual direction

**Brand personality:** Premium SaaS, friendly, memorable, calm, editorial, and trustworthy.

**Brand identity:**
- Product name: **Phrasia**.
- Wordmark treatment: `Phrasia` or `Phrasia.`; do not invent or finalize a logo without approval.
- Proposed tagline: **Words, Refined.** (provisional)
- Descriptor: **An intelligent workspace for better writing.**
- The brand should cover the complete writing platform, not only the Humanizer.

**Initial design tokens (starting proposal; keep centralized and easy to tune):**
- Main background: warm off-white `#F7F7F2`.
- Primary brand: deep evergreen `#174D3B`.
- Main text: ink `#18221F`.
- Muted surface: `#EEF1EC`.
- Soft mint accent: `#CFE8DC`.
- Secondary accent may be used sparingly for AI/analysis states; do not make the product look like a generic neon AI dashboard.
- Dark mode may be added later; light theme is the first implementation target.

**UI direction:** premium editorial writing workspace, spacious editor, restrained borders, subtle shadows, clear hierarchy, readable typography, concise labels, and minimal decorative charts. Use a clean sans-serif UI font with optional editorial serif headings only where it improves the brand. The Humanizer workspace should be the visual centre of the product.

Use consistent button, badge, card, focus, loading, progress, success, warning, and error states. Ensure WCAG-conscious contrast and keyboard usability. Do not use AI-generated pseudo-logos or unlicensed fonts/assets as production branding.

---

## 6. Functional requirements by priority

Priority meanings:

- **P0:** required for Phase 1 usable Humanizer.
- **P1:** required for the next usable expansion.
- **P2:** enhancement/future scope.

| ID | Requirement | Priority | Acceptance summary |
|---|---|---:|---|
| FR-001 | Paste/type long text | P0 | Text can be entered and counted without an arbitrary small product cap. |
| FR-002 | Humanizer modes | P0 | Six initial modes are selectable and affect the prompt. |
| FR-003 | Custom instructions | P0 | Optional user instruction reaches the server-side rewrite pipeline. |
| FR-004 | Meaning/fact preservation | P0 | Default instructions protect facts, numbers, names, URLs, and citations. |
| FR-005 | External API Humanizer | P0 | At least one real provider adapter returns rewritten text. |
| FR-006 | Provider-neutral interface | P0 | UI/business logic calls an interface, not vendor-specific SDK directly. |
| FR-007 | Smart chunking | P0 | Long content is split at natural boundaries using provider limits. |
| FR-008 | Persistent chunk checkpoints | P0 | Completed chunks survive application restart. |
| FR-009 | Progress and job controls | P0 | User can see progress and pause/resume/cancel. |
| FR-010 | Output comparison | P0 | Original and rewritten text are both visible. |
| FR-011 | Copy/export | P0 | User can copy output and download TXT. |
| FR-012 | Basic history | P0 | Document metadata, options, status, and output references are persisted in Supabase. |
| FR-013 | API key protection | P0 | Key remains server-side and is not logged or committed. |
| FR-014 | Paid calls blocked by default | P0 | Paid provider call is impossible unless explicitly authorized. |
| FR-015 | Provider/model attribution | P0 | Result records provider and model used. |
| FR-016 | DOCX import/export | P1 | Basic text and paragraph structure can be imported/exported; source files live in private Supabase Storage. |
| FR-017 | Secondary free provider | P1 | A second configured free/trial provider can be selected or used as fallback. |
| FR-018 | Paid provider adapters | P1 | OpenAI/Anthropic integration can be enabled intentionally. |
| FR-019 | Usage/cost tracking | P1 | Provider usage and estimated cost are recorded where returned/configured. |
| FR-020 | Secure API settings UI | P1 | Provider keys are managed server-side and encrypted at rest or kept in Vercel environment variables. |
| FR-021 | Local reference matching | P1 | Python compares a document against the owner's indexed Supabase corpus. |
| FR-022 | External plagiarism API | P1 | Provider result and source matches are shown without fabrication. |
| FR-023 | AI detector API | P1 | Provider score, warnings, and sentence details are displayed. |
| FR-024 | PDF extraction/export | P2 | Text-based PDF import and polished PDF export. |
| FR-025 | Batch document jobs | P2 | Multiple documents can be queued and tracked. |
| FR-026 | Advanced diff/track changes | P2 | Word/sentence-level changes can be reviewed. |

---

## 7. Non-functional requirements

### 7.1 Reliability

- A failed chunk must not erase completed chunks.
- API timeouts and rate limits must produce actionable messages.
- Retries must be bounded and use backoff where appropriate.
- Do not retry non-retryable errors indefinitely.
- The application must not mark a partial/truncated output as complete.
- A job must be resumable after a normal application restart.

### 7.2 Performance

- Keep the UI responsive while API calls run.
- Long rewrites run as background jobs, not as one blocking UI request.
- Use controlled concurrency; start sequentially for the single-user MVP to reduce rate-limit errors and output ordering risk.
- Show progress based on completed chunks, not an invented time estimate.
- Avoid loading every full document/version into the UI state if not needed.

### 7.3 Security and privacy

- Keep provider keys only on the backend.
- Do not put keys in Reflex client state, HTML, browser storage, URL parameters, or logs.
- Do not commit `.env`, downloaded Supabase files, uploaded documents, or generated reports.
- Validate upload extension, MIME type, file size, and parsed content.
- Store uploads in a private Supabase Storage bucket using generated object paths; never trust client-supplied paths.
- Use generated Storage object paths; keep the original filename as metadata.
- Add a delete-document operation that removes file and related DB rows.
- Explain that text is sent to the selected third-party provider for processing.
- Do not claim that data is private from a provider unless that provider's current contract/settings confirm it.
- Make provider data-retention/training terms visible in Settings or a provider info panel.

### 7.4 Maintainability

- Keep provider adapters isolated.
- Keep UI state separate from business logic and persistence.
- Use typed request/response schemas.
- Add tests for chunking, merging, routing, quota handling, and output validation.
- Pin dependencies and document setup.
- Do not write one giant page/module for the whole app.

### 7.5 Accessibility and usability

- Keyboard-operable controls.
- Clear focus indicators.
- Accessible labels for buttons and text fields.
- Readable status colors with text labels (not color alone).
- Responsive editor layout.

---

## 8. Provider strategy and operating modes

### 8.1 Initial Humanizer provider strategy

Recommended Phase 1 implementation:

1. Implement the provider interface.
2. Implement Gemini as the first actual adapter.
3. Optionally implement Groq as a second adapter once the first end-to-end workflow is stable.
4. Keep OpenAI and Anthropic on the planned paid-provider list for Phase 2.

The owner supplies API keys. Never embed developer-owned keys in source code.

Provider availability, free quota, allowed models, pricing, and data-use terms can change. At application setup time, the owner/agent must check the provider's current official documentation and account console. Do not hardcode quota numbers as permanent facts.

### 8.2 Operating modes

- **Free-only:** use only providers manually marked/configured as free or trial. Never call a paid provider.
- **Hybrid:** attempt configured free providers first; paid providers remain blocked unless separately authorized for a specific request or by a deliberate policy with a non-zero spending cap.
- **Manual:** owner selects a provider for the job.

Initial default: **Free-only**.

### 8.3 Provider failure behavior

- `429` / quota exhausted: read `Retry-After` or provider reset headers when present; try another eligible free provider; otherwise pause and save the job.
- `401` / `403`: mark credentials/permissions issue; do not repeatedly retry.
- `5xx` / transient network: bounded retry with exponential backoff; then alternative eligible provider or pause.
- Invalid model / request: surface the configuration error and do not blindly retry.
- Paid provider required: show the provider, estimated charge if available, and confirmation step. If not approved, pause.

---

## 9. Document and data handling

### 9.1 Initial supported formats

- Phase 1: pasted text and `.txt` import/export.
- Phase 2: basic/improved DOCX structure preservation and text-based PDF extraction.
- Phase 3+: advanced document export and batch handling.

Do not claim full layout preservation for complex documents until tested.

### 9.2 Source text and rewritten text

Keep the source immutable for each version. A rewrite creates a new version; it must not overwrite the source text.

### 9.3 Chunk metadata

Each chunk should track:

- document/job ID;
- stable chunk ID and sequence index;
- original character/token estimate;
- input text or a secure reference to it;
- provider and model used;
- status and attempt count;
- rewritten output;
- token usage/cost data when available;
- error category and safe error message;
- timestamps.

### 9.4 Deletion

The owner must be able to delete a document, its uploaded file, rewrite versions, jobs, and related Supabase reports/storage objects. Provider-side copies cannot be deleted by the app unless the provider exposes a deletion endpoint and the integration uses it; disclose this limitation.

---

## 10. Phased implementation roadmap

The order is intentional. **Humanizer comes first.** The project is not considered initially usable until Phase 1 passes its acceptance criteria.

### Phase 0 — Foundation, Supabase, Vercel, and private access

**Goal:** Create a working Phrasia project with the intended production hosting foundation before the Humanizer implementation begins.

Scope:

- Create the Python/Reflex project scaffold and Phrasia brand shell.
- Set up Python version, dependency management, formatting, linting, and tests.
- Create a Supabase project on the Free plan.
- Configure Supabase Postgres, Supabase Auth, private Storage buckets, and SQL migrations through the Supabase CLI.
- Add owner-only authentication and RLS policies for every application table and Storage path.
- Connect the application to Supabase using the official Python client and a backend-only data-access layer.
- Create the Vercel Hobby project and link the Git repository.
- Implement and document a Reflex-to-Vercel compatibility proof of concept before building complex UI state features. Verify static frontend hosting, backend/API routing, Reflex event transport/WebSocket behavior, authentication callbacks, and a reconnect after function restart.
- If the Reflex backend cannot be reliably hosted within Vercel Functions, do not fake compatibility. Use the documented fallback architecture in `Phrasia_Architecture.md` and record the decision.
- Configure Vercel environment variables and separate local-development `.env.example` placeholders.
- Add secure file upload to a private Supabase Storage bucket using signed upload URLs.
- Add Supabase-backed health/status checks, safe logging, and deployment smoke tests.
- Create persistent progress files: `PROJECT_PROGRESS.md`, `AGENT_HANDOFF.md`, `IMPLEMENTATION_LOG.md`, and `DECISIONS.md`.

Acceptance:

- Local development starts successfully.
- A private Phrasia deployment is reachable on its Vercel Hobby URL.
- The owner can sign in with Supabase Auth.
- Unauthenticated visitors cannot access application pages, data, or private files.
- RLS tests prove one user cannot read another user's records or Storage objects.
- Supabase database migrations apply cleanly.
- A small Reflex event/UI action works end-to-end on the deployed environment.
- The deployment architecture and any Reflex/Vercel caveats are documented.
- No provider API key is required merely to open the app.
- `.env` and all secrets are ignored by Git.
- Basic tests pass.

### Phase 1 — Humanizer MVP (first usable release)

**Goal:** The owner can use Phrasia on its private Vercel URL to humanize long text using an external API, with all job/document data persisted in Supabase.

Scope:

- Writing Workspace UI.
- Text paste/input and counts.
- Humanization modes and preservation controls.
- One actual provider adapter (Gemini proposed first).
- Server-side API key configuration.
- Provider-neutral service interface.
- Smart chunking based on model limits.
- Persistent job/chunk records in Supabase Postgres.
- Durable job queue and checkpointing using Supabase Queues/Postgres; a Vercel Python worker invocation processes a bounded amount of work per request.
- Supabase Cron triggers the secured worker endpoint on a schedule; do not rely on Vercel Hobby Cron for frequent polling.
- Pause/resume/cancel and retry failed chunk.
- Output assembly and completeness checks.
- Original/output comparison.
- Copy and TXT export.
- Basic Supabase-backed History and reopen job/document from another browser/session.
- Provider/model attribution.
- Clear quota/error messages.
- Paid API calls blocked.

Required: pasted text and `.txt` import/export. Basic `.docx` import/export is the next incremental enhancement and must not delay the first usable Humanizer.

Acceptance:

- A configured API key can produce a real rewrite.
- User can select the modes and preservation settings.
- A document larger than one provider request is processed in chunks.
- Chunks are assembled in correct order without silent omissions/duplication in tests.
- Completed chunks remain saved after restart.
- If quota is exhausted, the job pauses or switches only to another eligible free provider; no paid provider is called without explicit approval.
- User can copy/download the completed output.
- Original text remains unchanged.

### Phase 2 — Provider management and document robustness

**Goal:** Make the Humanizer resilient and provider-flexible.

Scope:

- Add Groq adapter (if the owner's current account/model supports suitable free usage).
- Add OpenAI and Anthropic paid adapters behind explicit authorization.
- Provider selection and fallback priorities.
- Free-only / Hybrid / Manual modes.
- Paid confirmation, spending cap, estimated cost, and cost ledger.
- Secure API settings interface or documented environment-based configuration.
- Improve DOCX fidelity.
- PDF text extraction.
- Version history and compare changes.
- Better usage dashboard and provider error log.

Acceptance:

- The owner can switch provider without changing Humanizer business logic.
- Paid providers cannot be called while disabled or unauthorized.
- Fallback respects provider eligibility and does not cause a paid call.
- API key changes do not require source code changes.

### Phase 3 — Plagiarism and reference-library matching

**Goal:** Add similarity analysis with a clear distinction between local matching and external web/database scanning.

Scope:

- Python reference-library index.
- Exact and n-gram matching.
- Optional TF-IDF-based matching after evaluation.
- Local similarity result with corpus scope displayed.
- External plagiarism provider adapter (Quetext or Copyleaks selected after current pricing/terms review).
- Source list, links, source percentages, matched passage highlighting if provider returns them.
- Provider report retrieval and export.

Acceptance:

- Local scan searches only indexed/authorized sources and labels its scope honestly.
- External score is taken from provider response, not invented by the app.
- Provider errors and billing limits are handled safely.

### Phase 4 — AI Writing Detector

**Goal:** Add AI-likelihood analysis through a specialist detector API.

Scope:

- Sapling adapter as a candidate initial provider.
- Evaluate GPTZero and Copyleaks as alternatives.
- Display overall score, verdict, model/version, confidence warnings, and sentence-level details when returned.
- Language support/unsupported-language warning.
- Provider usage tracking and report history.

Acceptance:

- AI-likelihood wording is used instead of certainty language.
- Detector provider and version are visible.
- Short/low-confidence/unsupported text is clearly flagged.
- The UI does not imply that AI score proves authorship.

### Phase 5 — Premium polish and advanced workflow

**Goal:** Improve usability after the core tools work.

Possible scope:

- Advanced side-by-side editor/diff.
- Batch document processing.
- PDF report export.
- Document outline and navigation.
- Search/filter/history enhancements.
- More Humanizer tone presets.
- Custom rewrite templates.
- Multi-provider comparison.
- Better analytics and cost breakdown.
- Additional authentication hardening and optional controlled account provisioning.
- Deployment hardening and quota monitoring for the Vercel Hobby + Supabase Free deployment.

Do not start Phase 5 until Phases 1–4 are usable and tested.

---

## 11. Phase 1 test plan

The coding agent must create automated tests for at least the following cases before declaring the Humanizer MVP complete:

1. Empty input is rejected with a clear message.
2. Normal paragraph is rewritten successfully using a mocked provider.
3. All initial modes map to different, explicit instruction settings.
4. Facts, names, numbers, dates, citations, URLs, and protected quotations are represented in the request/prompt policy.
5. A document requiring multiple chunks is split at boundaries and keeps ordering.
6. The final output does not contain duplicate chunk text due to assembly errors.
7. An incomplete/truncated provider response is not marked complete.
8. A failed chunk can be retried without repeating completed chunks.
9. A rate-limit response pauses or reroutes only to an eligible free provider.
10. A paid provider is never called when paid access is disabled.
11. A saved job can be loaded after deployment/function restart or browser refresh using Supabase persistence.
12. Original text is unchanged after a rewrite.
13. API keys do not appear in UI state, logs, error messages, or test snapshots.
14. TXT export contains the complete assembled output.
15. User can cancel a job and the status persists.

Use mocked API responses in automated tests. Real API smoke tests must be opt-in and must not burn credits during every test run.

---

## 12. Definition of done for the initial release

Phase 1 is complete only when all of the following are true:

- [ ] App can be developed locally and deployed to a private Vercel Hobby project with Supabase Free; the documented deployment smoke tests pass.
- [ ] Humanizer page is functional, not a static mockup.
- [ ] At least one real external Humanizer API is integrated.
- [ ] API key is read server-side from configuration.
- [ ] User can paste a long document and submit it.
- [ ] Chunking and resumable processing work for text longer than one request.
- [ ] Modes and preservation controls are wired to the request pipeline.
- [ ] Original and rewritten text are displayed.
- [ ] Output can be copied and downloaded.
- [ ] Job/document history is persisted in Supabase Postgres and Storage.
- [ ] Rate limits and failures do not lose completed chunks.
- [ ] Paid usage is disabled by default and tested as blocked.
- [ ] No Local LLM dependency or runtime has been added.
- [ ] Automated tests pass.
- [ ] README explains setup, API-key configuration, privacy implications, and limitations.

---

## 13. Assumptions and decisions currently made

| Area | Current decision |
|---|---|
| Product name | Phrasia |
| Proposed tagline | Words, Refined. (provisional) |
| Product descriptor | An intelligent workspace for better writing. |
| Initial audience | One private owner account; not public SaaS |
| Brand/UI | Premium SaaS, friendly, memorable, editorial writing workspace |
| Primary UI language | English initially; preserve input-language content |
| Primary development language | Python |
| Frontend framework | Reflex (Python-authored UI) |
| Backend | Python / Reflex with a Vercel-compatible deployment proof gate |
| Hosting | Vercel Hobby Free for personal/non-commercial use |
| Database | Supabase-managed PostgreSQL |
| Authentication | Supabase Auth; owner-only access; disable public sign-up |
| File storage | Private Supabase Storage buckets and signed URLs |
| Queue/checkpoints | Supabase Queues/Postgres + Supabase Cron + bounded Vercel Python worker invocations |
| Humanizer priority | First functional module |
| AI generation | External APIs only; no Local LLM |
| Free API | Supported; quota/eligibility checked at use time |
| Paid API | Supported architecturally; disabled by default; per-job approval required |
| Long documents | No arbitrary small product-level word cap; chunked and resumable; provider and hosting limits apply |
| Local plagiarism fallback | Python matching only against owner-controlled, indexed Supabase reference corpus |
| Internet-wide plagiarism | Requires a suitable external provider/search corpus |
| Public SaaS features | Deferred |

## 14. Open decisions for later (do not block Phase 1)

- Final logo artwork and typography refinements; Phrasia is the approved product name, the tagline remains provisional, and the initial palette is a starting proposal.
- Which plagiarism provider offers the best value and acceptable privacy terms at implementation time.
- Which AI detector provides suitable language coverage and acceptable false-positive behavior.
- Whether DOCX import/export should be in the first Phase 1 build or a Phase 1.1 increment.
- Whether to support Bengali detection, and which provider/model can do so reliably.

The coding agent should not stop Phase 1 to resolve these future decisions.

---

## 15. Official documentation and provider references

These are starting references, not permanent guarantees of free access, limits, pricing, or terms. Re-check the current official documentation and the owner's account dashboard before implementation and before enabling a provider.

### Framework

- [Reflex documentation](https://reflex.dev/docs/)
- [How Reflex works](https://reflex.dev/docs/advanced-onboarding/how-reflex-works/)
- [Reflex background events](https://reflex.dev/docs/) — locate the current Background Events guide in the docs navigation.
- [Reflex custom React component wrapping](https://reflex.dev/docs/wrapping-react/overview/)

### Humanizer / text generation providers

- [Google Gemini API documentation](https://ai.google.dev/gemini-api/docs)
- [Gemini API pricing and free/paid tiers](https://ai.google.dev/gemini-api/docs/pricing)
- [Gemini API rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Groq API documentation](https://console.groq.com/docs)
- [Groq rate limits](https://console.groq.com/docs/rate-limits)
- [OpenAI API documentation](https://platform.openai.com/docs/)
- [OpenAI API pricing](https://openai.com/api/pricing/)
- [Anthropic API documentation](https://docs.anthropic.com/)
- [Anthropic API pricing](https://www.anthropic.com/pricing#anthropic-api)

### Plagiarism and AI detection candidates

- [Quetext Developers API](https://www.quetext.com/developers-api)
- [Copyleaks API documentation](https://docs.copyleaks.com/)
- [Sapling AI Detector API](https://sapling.ai/docs/api/detector/)
- [GPTZero API reference](https://docs.gptzero.me/api-reference/)

**Provider evaluation note (checked 19 November 2026):** Gemini's published page distinguishes free and paid tiers and states different data-use treatment for those tiers; Groq documents account/model-specific request and token rate limits; Sapling documents an AI detector with document and sentence scores plus explicit false-positive/false-negative caveats; Quetext documents separate plagiarism and AI-detection API endpoints with provider-specific request limits and prepaid billing. Treat all quotas, model lists, prices, and terms as changeable. The app must read provider settings from configuration and handle live errors rather than relying on fixed assumptions.

---

**End of PRD**


## 16. Supabase Free + Vercel Hobby deployment requirements

This is the approved initial deployment target. It is intended for a private personal application, not a commercial public SaaS.

### 16.1 Supabase responsibilities

Use Supabase for:

- PostgreSQL database and application persistence;
- Supabase Auth for the owner login/session;
- private Storage buckets for uploads, original text artefacts, humanized outputs, exports, and reference-library files;
- Supabase Queues (pgmq) or a durable Postgres-backed job queue for background processing;
- Supabase Cron to trigger periodic worker ticks when needed;
- Realtime or bounded polling for job progress updates.

All user-owned tables must include `owner_id` (or an equivalent authenticated user foreign key) and RLS policies. Private buckets must use owner-scoped object paths and Storage RLS policies. Never make uploaded writing documents publicly readable.

### 16.2 Vercel responsibilities

Use Vercel Hobby for:

- hosting the Phrasia web application/static frontend assets;
- Python serverless backend/API functions where compatible;
- preview and production deployment from Git.

The Reflex + Vercel integration is a required technical proof gate, not an assumption. Reflex documents static frontend export with a separately reachable backend. Vercel documents Python/FastAPI serverless functions. The agent must prove that the selected Reflex backend/event transport can run correctly under the Vercel Python runtime and WebSocket/function lifecycle. If that exact approach fails, implement the documented fallback in the Architecture document without abandoning Python-authored UI or silently switching to Next.js.

### 16.3 Free-plan constraints to design around

The quotas below are a snapshot checked on 19 November 2026 and must be rechecked at setup time because provider limits can change.

- Supabase Free currently lists 500 MB database size, 1 GB file storage, 5 GB egress, 5 GB cached egress, 50 MB maximum upload size, and project pausing after one week of inactivity.
- Vercel Hobby is for personal/non-commercial use. Its Python Functions currently have a maximum duration of 300 seconds and 2 GB / 1 vCPU. Hobby Cron currently runs only once per day, so do not use it for minute-level job processing.
- Supabase Cron can invoke an HTTP endpoint. Use it for worker ticks, with each Vercel worker invocation deliberately bounded below the Vercel maximum and with durable checkpoints between chunks.
- No arbitrary application-level word limit does not mean infinite hosted resources. Storage size, request size, Vercel function duration, provider context limits, and free API quotas still apply.

### 16.4 Upload and long-document workflow

- Browser uploads must go directly to Supabase Storage using signed upload URLs where possible; do not route large file payloads through a Vercel Function.
- Store only metadata and processing checkpoints in Postgres; store large input/output text blobs and original files in private Storage objects where appropriate.
- The current Supabase Free max object upload size is 50 MB. Show a clear file-size message based on the current configured limit; do not invent an unlimited file-size promise.
- A text paste can be stored as a generated text object when too large for a normal request body.
- A worker claims a job/chunk, processes a small bounded amount, persists output and state, and exits before the function deadline. It must not depend on an always-running Python daemon on Vercel.

### 16.5 Owner account and privacy

- Supabase Auth is mandatory in the deployed environment.
- Disable public sign-up after setting up the owner account, or enforce a strict owner allow-list.
- Set redirect URLs for localhost development and the production Vercel domain.
- Never expose Supabase secret/service-role keys, provider API keys, or `WORKER_CRON_SECRET` to the browser.
- Enforce RLS and verify it with integration tests.
- The app must disclose that external AI/plagiarism/detector providers receive submitted text according to their own data policies.

### 16.6 Deployment acceptance checklist

- [ ] Supabase project created and schema migrations applied.
- [ ] Owner can sign in using Supabase Auth.
- [ ] Public unauthenticated access to protected pages/data/files is denied.
- [ ] RLS tests pass for database tables and Storage objects.
- [ ] Reflex compatibility proof passes on Vercel or an explicitly documented fallback has been implemented.
- [ ] Supabase private file upload/download works through signed URLs.
- [ ] Supabase queue can retain and re-deliver a test job safely.
- [ ] Supabase Cron can invoke a secured worker route.
- [ ] A worker invocation can process one test chunk, persist it, and exit under the Vercel duration limit.
- [ ] A job can resume after a function restart or redeployment.
- [ ] Vercel environment variables contain all production secrets; none are committed or exposed.
- [ ] Usage/limit warnings are visible in Settings.

### 16.7 Official hosting references

- Supabase pricing and Free plan: https://supabase.com/pricing
- Supabase Auth: https://supabase.com/docs/guides/auth
- Supabase Storage: https://supabase.com/docs/guides/storage
- Supabase Queues: https://supabase.com/docs/guides/queues
- Supabase Cron: https://supabase.com/docs/guides/cron
- Supabase Python client: https://supabase.com/docs/reference/python/introduction
- Vercel Python/FastAPI deployment: https://vercel.com/kb/guide/ship-a-fastapi-app-on-vercel
- Vercel Function limits: https://vercel.com/docs/limits
- Vercel Cron pricing/limits: https://vercel.com/docs/cron-jobs/usage-and-pricing
- Vercel Hobby terms: https://vercel.com/legal/terms
- Reflex static frontend/backend hosting: https://reflex.dev/docs/hosting/self-hosting/


---

**Revision note:** This 2.0 document supersedes the earlier `AI_Humanizer_PRD.md`. Phrasia branding and Supabase + Vercel deployment are now approved requirements.
