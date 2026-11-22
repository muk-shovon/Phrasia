# OpenCode Master Build Prompt — Phrasia

> **Purpose:** Give this entire prompt to OpenCode after placing `Phrasia_PRD.md` and `Phrasia_Architecture.md` in the project root. This is the master implementation instruction for the complete core application.
>
> **Execution priority:** Build a genuinely usable Humanizer first. Then continue through provider management, plagiarism checking, and AI detection in order. You are authorized to implement all core modules in this run without asking for approval between phases. Do not start optional premium polish until the core modules work.

---

## 1. Role and mission

Act as the lead software architect, senior Python engineer, Reflex UI developer, API integration engineer, QA engineer, and technical project manager for this repository.

Build **Phrasia**, a private, premium AI writing workspace for a single owner initially. Proposed tagline: **Words, Refined.** (provisional) Descriptor: **An intelligent workspace for better writing.** It has three core capabilities:

1. AI Humanizer / Rewriter — the first and highest-priority module.
2. Plagiarism / Similarity Checker — external provider scanning plus a clearly distinguished Python local-reference matcher.
3. AI Writing Detector — external detector API integration with honest reporting and limitations.

The owner wants to use the application personally first. The Vercel deployment must be private behind Supabase Auth; this is not initially a public SaaS product.

Your objective is not to create a static dashboard or a mock-only prototype. Deliver working functionality in the order below, with persistent progress notes so development can resume after interruption without restarting the entire analysis.

## 2. Mandatory documents and precedence

Before editing code, read the two specification documents completely:

- `Phrasia_PRD.md`
- `Phrasia_Architecture.md`

Treat those two documents as the detailed product and architecture specifications.

This master prompt adds one execution authorization: **you are authorized to implement all core phases (Foundation, Humanizer, Provider Management, Plagiarism, and AI Detection) sequentially without requesting approval between phases.** This overrides only the documents' instruction to stop and wait for owner approval between those core phases. It does not override any technical constraint, security rule, acceptance criterion, or no-paid-without-consent rule.

If the two source documents conflict with each other, follow this priority:

1. Explicit constraints in this master prompt.
2. `Phrasia_PRD.md` for product behavior and scope.
3. `Phrasia_Architecture.md` for implementation structure.

Record any material ambiguity in `DECISIONS.md`. Do not invent product requirements to resolve important uncertainty.

## 3. Non-negotiable technical constraints

- Product name: **Phrasia**.
- Proposed tagline: **Words, Refined.** (provisional)
- Product descriptor: **An intelligent workspace for better writing.**
- Primary language: Python.
- UI framework: Reflex (Python-authored UI). Do not create a separately maintained Next.js/React/TypeScript frontend.
- Hosting: Vercel Hobby Free for the owner's personal/non-commercial deployment.
- Backend platform: Supabase Free.
- Database: Supabase PostgreSQL from the beginning; do not use SQLite for production.
- Database migrations: Supabase CLI SQL migrations committed to Git.
- Authentication: Supabase Auth, owner-only access, public sign-up disabled after initial owner setup.
- File storage: private Supabase Storage buckets and signed upload/download URLs.
- Durable jobs: Supabase Queues/pgmq or a transactional Postgres-backed queue.
- Scheduled worker: Supabase Cron invokes a secured Vercel Python worker endpoint. Do not use Vercel Hobby Cron for minute-level scheduling.
- Do not run a long-lived worker loop inside Vercel. Each worker invocation claims a small amount of work, persists a checkpoint, and exits before the function deadline.
- Reflex + Vercel must pass a Phase 0 proof of concept for event/WebSocket routing. If direct backend deployment fails, follow the documented Python FastAPI serverless fallback while retaining Reflex-authored UI. Do not silently change frameworks.
- No Next.js, no separate hand-written TypeScript application, no Node.js backend.
- **No Local LLM.** Do not add Ollama, llama.cpp, local transformers, or a local generative model.
- Humanizer first. It must be genuinely functional with a real external API before Plagiarism or AI Detector work begins.
- Free-first; paid-ready. Paid API is OFF by default, USD 0 budget, no automatic paid fallback, explicit per-job owner approval required.
- No arbitrary small app-level word cap. Use provider-aware chunking and resumable durable jobs, while respecting Supabase Storage, Vercel runtime, and provider limits.
- If all Humanizer APIs are unavailable or quota-limited, save and pause the job. Never use Python synonym replacement and call it AI humanization.
- Do not fabricate detector scores, plagiarism percentages, matched sources, or provider success.
- Every coherent milestone must update `PROJECT_PROGRESS.md`, `AGENT_HANDOFF.md`, `IMPLEMENTATION_LOG.md`, and `DECISIONS.md`.

### 3.1 Phrasia UI identity

Use a premium, friendly editorial SaaS direction. Centralized starting tokens:
- warm off-white `#F7F7F2`;
- deep evergreen `#174D3B`;
- ink text `#18221F`;
- muted surface `#EEF1EC`;
- soft mint accent `#CFE8DC`.

Keep the Humanizer Workspace as the first page after sign-in. Use a spacious editor, compact navigation, subtle borders, accessible contrast, restrained shadows, and clean typography. Avoid generic neon AI gradients, overdecorated dashboards, and fake logo artwork. Use the wordmark `Phrasia` / `Phrasia.` and the provisional tagline `Words, Refined.` consistently; keep the tagline easy to change. Do not spend the first phase on a complex logo; make the app feel coherent through typography, tokens, and layout.

## 4. FreeLLMAPI and OpenCode model instructions

The owner uses **FreeLLMAPI** as a unified gateway for multiple free model providers. Do not replace or modify the owner's existing FreeLLMAPI installation or OpenCode configuration unless specifically asked.

### 4.1 Model recommendation for the coding agent

Use this as the starting model preference, subject to a live availability check:

- Primary candidate: `qwen/qwen3.8-max:free`
- Fallback candidate: `qwen/qwen3.8-27b`
- Additional fallback candidate: `glm-5.3:free` only if its current route is healthy and usable for tool calling.

The FreeLLMAPI catalog currently lists Qwen3.8 Max with a 1M-token context and tool calling, served by multiple routes; the listed xKiro route currently advertises a daily free token allowance. Qwen3.8 27B currently has multiple provider routes, with the Groq route listing free usage, 30 requests/minute, and a 70K tokens/minute limit. GLM 5.3 currently lists tool calling but only one request/minute on its listed free route. These are changing provider/catalog facts, not permanent guarantees.

Before relying on any model:

1. Query the local FreeLLMAPI model catalog and identify models currently marked ready/available.
2. Run a small tool-calling smoke test through the gateway.
3. Confirm that OpenCode can execute a harmless read-only tool call and receive the follow-up correctly.
4. Prefer a named FreeLLMAPI `coding` fallback profile if the owner has configured one; otherwise pin the best currently available model from the candidates above.
5. If a model is unavailable, do not waste repeated calls; move to the next verified candidate and record the result in `PROJECT_PROGRESS.md`.

Normal coding-agent work should use one stable model at a time or a controlled coding fallback chain. Do **not** use multi-model `fusion` for every OpenCode turn. Fusion can be used selectively for a design review or second-opinion analysis, but the normal agent loop needs reliable, consistent tool calls and predictable context.

FreeLLMAPI's OpenCode setup helper is documented as:

```powershell
npx freellmapi setup-opencode --url http://localhost:3001 --api-key "YOUR_UNIFIED_KEY" --dry-run
```

Review the dry-run output first. If the owner has not configured OpenCode yet, explain how to run the command without `--dry-run`. Do not print, log, commit, or place the real unified API key in source files. Do not overwrite unrelated existing OpenCode providers/configuration.

### 4.2 FreeLLMAPI as an optional Humanizer provider

The application should support a generic **OpenAI-compatible provider adapter** so the owner can optionally use their local FreeLLMAPI gateway for Humanizer requests too.

Suggested local settings (all configurable; never hardcode secrets):

```env
HUMANIZER_PROVIDER=freellmapi
FREELLMAPI_BASE_URL=http://127.0.0.1:3001/v1
FREELLMAPI_API_KEY=
FREELLMAPI_MODEL=auto:smart
```

Important:

- The OpenCode coding-agent model and the application's Humanizer model are separate settings. Do not couple them.
- The Humanizer model must be selectable/configurable. A model profile such as `auto:humanizer` may be used if the owner creates that profile in FreeLLMAPI. `auto:smart` is a reasonable initial configurable value, not a permanent hardcoded truth.
- Check `GET /v1/models?execution_status=ready` where supported, and handle unavailable models clearly.
- Read routing metadata such as `X-Routed-Via` when returned; store safe provider/model metadata with the job, but never store secrets.
- If FreeLLMAPI is not running, show a provider-unavailable state and offer another configured provider. Do not crash the application.
- FreeLLMAPI is a gateway to upstream cloud providers, not a Local LLM. Text sent through it still leaves the computer to the selected upstream provider. Respect each upstream provider's terms and privacy policy.
- FreeLLMAPI is intended for personal experimentation. Do not expose its local gateway publicly or treat its free pool as a production SLA.

## 5. Required product behavior

### 5.1 Humanizer-first requirement

The first usable release must allow the owner to:

1. Open the private Phrasia deployment in the browser (and keep local development working).
2. Paste or type a substantial text document.
3. Upload a `.txt` file; add basic `.docx` import/export as part of document robustness without delaying the first working Humanizer.
4. Select a humanization mode and rewrite controls.
5. Start a real rewrite through a configured external API.
6. See job progress and current chunk status.
7. Pause, resume, cancel, and retry a failed chunk.
8. Compare original and rewritten text.
9. Copy or export the result.
10. Reopen the document and its prior versions from Supabase-backed history.

Do not call a mock response a completed Humanizer. If no API key/provider is configured, show a clear setup message and allow safe test/mock fixtures only in development tests.

### 5.2 Humanization modes

Implement at least:

- Standard / Natural
- Simple / Easy to Read
- Professional
- Academic / Formal
- Conversational
- Concise
- Expand / Elaborate
- Custom Instructions

Controls:

- Rewrite intensity: Light / Balanced / Strong.
- Preserve meaning: ON by default.
- Preserve facts, names, and numbers: ON by default.
- Preserve URLs, quotations, citations, and reference markers: ON by default.
- Preserve headings, paragraphs, bullets, and lists: ON by default where parsing permits.
- Optional custom instructions.

The Humanizer should improve clarity, flow, readability, tone, and sentence structure. Do not intentionally insert errors, random typos, fake personal anecdotes, fake citations, or false claims. Do not promise detector evasion.

### 5.3 Long-document behavior

The product must not impose an arbitrary small word count limit. Implement:

- Paragraph-aware chunk planning.
- Provider-aware input/output token budgeting.
- Configurable safety margin below a provider/model context limit.
- Protected spans for URLs, emails, citations, code, numeric values, and other text that should not be altered.
- Stable chunk ordering and IDs.
- Optional short context summary/previous-section notes to preserve terminology and consistency between chunks.
- Per-chunk output validation.
- Persist each chunk output immediately after success.
- Persistent checkpoints so a process restart does not lose completed chunks.
- Pause on rate limit/quota exhaustion, network failure, or provider outage when no eligible fallback is available.
- Retry only failed/incomplete chunks unless the owner explicitly chooses a full rerun.
- Reassemble chunks in their exact original order.
- Clearly show partial, paused, failed, completed, and cancelled states.

Do not run every chunk concurrently by default. Use conservative concurrency and provider-specific rate limits. Avoid duplicate billing by using stable idempotency keys/job-chunk identifiers where possible and never retry ambiguous timeouts blindly without checking persisted state/provider support.

### 5.4 Provider management

Create a provider registry/adapter architecture. At minimum, support:

- FreeLLMAPI as a generic OpenAI-compatible gateway.
- Gemini API adapter or a generic OpenAI-compatible adapter if the selected gateway exposes it.
- Groq as an optional provider.
- OpenAI and Anthropic as paid-ready optional adapters.
- Plagiarism/detection adapters in their respective phases.

Provider settings should include enabled state, provider label, base URL if configurable, model ID, credential reference, provider type (free/trial/paid), capabilities, priority, timeout, and status. Credentials must be loaded server-side from Vercel environment variables or securely encrypted server-side storage. Never return full keys to the browser after saving; display only masked values.

Routing must distinguish:

- 401/403 authentication or account errors;
- 402/payment or credit errors;
- 404 unsupported model/endpoint;
- 413/request too large;
- 429 rate limit/quota exhaustion;
- 5xx provider outage;
- network timeout/connection errors;
- malformed or incomplete provider responses.

Only eligible configured providers may be tried. Never silently switch to paid providers. A provider being listed in the catalog does not mean the user's account has credentials or quota for it.

### 5.5 Plagiarism / Similarity Checker

Implement this after the Humanizer and provider foundation are stable.

Provide two explicitly separate scan types:

1. **External plagiarism scan:** a dedicated configured provider (for example Quetext or Copyleaks) that can search its provider corpus/web/academic sources according to its contract.
2. **Supabase reference-library similarity scan:** Python matching against only the documents the owner has imported/indexed.

Local techniques may include normalized exact matching, sentence fingerprints, n-grams, PostgreSQL full-text search and trigram matching, TF-IDF, and optional non-generative embedding APIs if configured. Do not use a Local LLM.

The report must label coverage accurately. A Supabase-indexed reference corpus match score must never be presented as Internet-wide plagiarism percentage. Do not fabricate an overall percentage when the provider does not return a comparable metric. Show matched excerpts, source names/URLs when supplied, and provider metadata. Allow export of a report after the provider returns real data.

### 5.6 AI Writing Detector

Implement this after plagiarism. Use dedicated external detector providers only in the first release of this module (for example Sapling, GPTZero, or Copyleaks where the owner has access). Provide a clean provider interface and normalized report model.

Display the provider's actual score/verdict and available sentence-level details. Clearly explain that detector output is an estimate, not proof of authorship. Do not average scores from different providers unless a mathematically valid normalization and explicit methodology is designed and shown. Do not fabricate scores or fallback to unsupported Python heuristics and label them as a detector.

## 6. UI/UX requirements

Create a polished but practical writing-focused desktop-first interface. Avoid spending the first days on decorative landing pages.

Required navigation:

- Workspace / Humanizer
- Plagiarism Checker (unavailable or clearly marked until Phase 3 is implemented; no fake result screen)
- AI Detector (unavailable or clearly marked until Phase 4 is implemented; no fake result screen)
- Documents / History
- API Providers / Settings
- Usage / Logs (simple initial view; expand later)

Humanizer workspace:

- Large input editor with character/word counts.
- Drag-and-drop or browse upload.
- Humanization mode and controls.
- Primary Humanize action.
- Persistent progress panel with current phase/chunk and completed/total chunks.
- Original and output panes with copy buttons.
- Clear status/error details and provider/model used.
- Save, export, retry, pause, resume, and cancel controls as appropriate.

Visual direction: premium SaaS, clean, editorial, distraction-free, readable typography, subtle borders, restrained forest-green/teal accent, responsive layout. Functionality and accessibility are more important than visual gimmicks.

## 7. Required architecture and maintainability

Use the architecture in `Phrasia_Architecture.md` as the source of truth.

Required boundaries:
- Reflex pages/components and state;
- Python domain/use-case/services;
- provider interfaces and isolated adapters;
- Supabase repositories for Postgres/Auth/Storage/Queues;
- durable chunk/job orchestration;
- Vercel Function route(s) for API and bounded worker ticks;
- Supabase Cron + Queue for durable background processing.

Use the official Supabase Python SDK for Auth, Storage, PostgREST, and RPC. Use Supabase CLI SQL migrations. Enforce RLS for all owner records and private Storage paths. Keep privileged Supabase credentials and provider API keys server-side only.

The Reflex-to-Vercel deployment proof is a hard Phase 0 gate. Test a deployed event round-trip and session behavior before building the full UI. If the direct Reflex ASGI/WebSocket approach fails, use the Python FastAPI serverless fallback described in the Architecture document, with Reflex static export and a minimal isolated client bridge. Do not invent a Vercel integration or claim success without a deployed test.

Vercel Functions are short-lived. Set a conservative worker internal deadline (target 240 seconds, subject to current plan/runtime) and persist each chunk before the invocation exits. Supabase Cron should trigger the worker. Never start a permanent daemon in a serverless function. Use signed direct uploads to Supabase Storage rather than proxying large files through Vercel.

Keep provider adapters isolated. Do not overbuild future modules before the Humanizer works. No Local LLM.

## 8. Progress, checkpoint, and interruption recovery — mandatory

Create and maintain these files at the repository root:

1. `PROJECT_PROGRESS.md` — source of truth for phase status and overall progress.
2. `AGENT_HANDOFF.md` — concise exact restart instructions and the next action.
3. `IMPLEMENTATION_LOG.md` — append-only record of meaningful implementation decisions, tests, issues, and fixes.
4. `DECISIONS.md` — architecture/product decisions, including date, reason, and consequences.
5. `README.md` — setup, environment configuration, run, test, backup, and troubleshooting.

### 8.1 PROJECT_PROGRESS.md structure

Maintain:

- Project status and last updated timestamp.
- Current phase and current task.
- Overall core-module checklist.
- Phase checklist with `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, or `DONE`.
- Completed items (with file paths or feature names).
- In-progress items (specific subtask, not vague text).
- Remaining items.
- Tests/commands last run and pass/fail outcomes.
- Known bugs and blockers.
- Required owner actions/API credentials, without recording secret values.
- Last known good state / commit hash if Git is used.
- Exact next 3 actions in order.

### 8.2 AGENT_HANDOFF.md structure

Keep this short and operational:

- Current branch and last known working state.
- Current phase/task.
- What is already implemented.
- Exact file(s) currently being changed.
- Last successful test/build/run command.
- Current failure/blocker, if any.
- The single best next action.
- Files the next agent session must inspect first.

### 8.3 Update discipline

- Initialize these files before major implementation.
- Update `PROJECT_PROGRESS.md` and `AGENT_HANDOFF.md` after every coherent milestone (for example: project scaffold, database models, first provider test, first successful humanization, chunk persistence, pause/resume, plagiarism phase, detector phase).
- Update the handoff before stopping, before a risky migration, and whenever an interruption is likely.
- Append a concise entry to `IMPLEMENTATION_LOG.md` for completed milestones and important failures/fixes.
- Never wait until the very end to record progress.
- Never claim a phase is DONE unless its acceptance tests pass.
- If interrupted, leave the repository in a state where the next session can continue from the handoff.

### 8.4 Mandatory restart protocol

Whenever a new OpenCode session starts or resumes after interruption:

1. Read `AGENT_HANDOFF.md` first.
2. Read the relevant section/current snapshot in `PROJECT_PROGRESS.md`.
3. Run `git status --short` and inspect the current branch/last commit if Git exists.
4. Inspect only the files listed in the handoff plus any files directly implicated by the next task.
5. Run the smallest relevant test/check to verify the checkpoint.
6. Continue from the exact next action.

Do not repeat the full initial repository analysis or re-read every source file on every resume. Re-read the PRD/Architecture only when starting the project for the first time, when a requirement is unclear, or when the documents were changed. Do not trust a stale checkpoint blindly: verify repository status and the last recorded test before editing.

## 9. Tests and quality gates

Write tests as features are implemented. At minimum:

### Foundation

- App imports and starts.
- Database initializes and migrations apply.
- Secrets/config validation works.
- No secret is rendered into frontend state or logs.

### Humanizer

- Input validation and empty-text handling.
- Chunking respects paragraphs and configured provider budget.
- Protected spans survive a mock rewrite.
- Output order matches input order.
- Successful chunk persists before the next chunk starts.
- Resume skips already-completed chunks.
- Retry targets failed chunks only.
- Pause/cancel state transitions work.
- 429/quota exhaustion pauses or switches only to an eligible free provider.
- Paid provider is never called when paid mode is OFF.
- No mock result is presented as real provider output.

### Plagiarism

- Local matching only searches indexed local sources.
- Empty corpus returns a truthful no-indexed-sources message, not 0% Internet plagiarism.
- External provider failure is clearly surfaced.
- Source URL and matched excerpt rendering are escaped safely.

### AI Detector

- Actual provider score/verdict is preserved.
- Different provider score scales are not silently mixed.
- Unconfigured provider returns a setup state, not a fake percentage.
- Uncertainty notice is always visible.

### General

- File upload validation and safe filenames.
- Document deletion removes associated files according to the retention policy.
- Job progress survives application restart.
- Browser smoke test for the main Humanizer flow.
- App launch and test commands are documented in README.

Use mock HTTP responses for repeatable tests. Do not spend real API quota during routine automated tests. Keep a clearly separated manual live-provider smoke-test procedure.

## 10. Core implementation sequence — execute all in this order

You are authorized to continue through all the following core phases without asking for approval between them. Humanizer comes first and must become usable before the next primary module begins.

### Phase 0 — Phrasia foundation, brand, Supabase, and Vercel proof

- Create the Python/Reflex scaffold using Phrasia branding and centralized theme tokens.
- Create a Supabase Free project and configure Postgres, Auth, private Storage buckets, RLS, and SQL migrations.
- Implement owner-only sign-in and protected routes. Disable public sign-up after owner setup.
- Build a private Vercel Hobby deployment and set environment variables securely.
- Prove Reflex frontend/backend event transport on Vercel. If direct Reflex backend deployment is not viable, implement the documented Reflex static + Python FastAPI Function fallback and record the choice in `DECISIONS.md`.
- Implement a private Storage upload/download proof using signed URLs.
- Implement a durable Supabase Queue/DB job claim and a secured Vercel worker tick invoked by Supabase Cron.
- Create test harness, safe logging, and the persistent progress/handoff files.

**Exit gate:** private Vercel deployment works, owner can log in, RLS and Storage policies pass tests, at least one Reflex UI event/API request works in production, and the durable worker proof can process and checkpoint a test message. Do not begin Humanizer feature code until the Reflex/Vercel integration path is known and documented.

### Phase 1 — Humanizer MVP (highest priority)

- Build the complete usable Humanizer workspace.
- Implement provider interface and first real external generation adapter.
- Support FreeLLMAPI OpenAI-compatible gateway as an optional/initial generation route.
- Add configurable model selection (`auto:smart`, a named profile, or pinned model).
- Add prompt templates for all required modes and preservation controls.
- Implement paragraph-aware provider-aware chunking.
- Persist document, version, job, chunks, progress, provider/model metadata, and timestamps.
- Implement pause/resume/cancel/retry and safe error handling.
- Add original/output comparison and `.txt` export; basic `.docx` support if it does not delay the usable release.
- Add clear provider setup instructions.

**Exit gate:** With a configured external API, the owner can successfully paste/upload text, humanize it, monitor progress, stop/resume after restart, inspect output, and export/copy it. Automated mock tests pass. Do not mark complete based only on a static UI.

### Phase 2 — Provider management and document robustness

- Add provider settings UI.
- Add provider status and test-connection capability.
- Add free/trial/paid classification and provider priority.
- Add paid authorization gate and default USD 0 spend limit.
- Add API usage/cost records where providers return enough metadata.
- Add additional free and paid-ready adapters as documented.
- Add robust `.docx` import/export and PDF text extraction only after evaluating dependency stability and format limitations.
- Improve long document checkpoint/recovery and provider-aware rate limiting.

**Exit gate:** Provider can be switched without changing Humanizer core logic; paid calls remain impossible unless explicitly authorized; document jobs survive application restart.

### Phase 3 — Plagiarism / Similarity Checker

- Implement the Supabase reference-library data model and import/index workflow.
- Implement exact matching, n-gram matching and lexical similarity (TF-IDF or equivalent if appropriate).
- Clearly distinguish Supabase-indexed reference corpus results from external provider scans.
- Add at least one external plagiarism provider adapter when credentials/API access are available.
- Build result report with actual matched sources/excerpts/URLs when provided.
- Add provider-aware chunking and persistent job progress for long scans.

**Exit gate:** Local scan accurately describes the Supabase-indexed reference corpus only; external scan is connected to a real provider or transparently marked unconfigured; tests cover both cases.

### Phase 4 — AI Writing Detector

- Create a dedicated detection provider interface.
- Add the first supported detector API adapter when credentials are available.
- Add additional adapters as time and API access allow.
- Add overall score, verdict, confidence/limitations and sentence-level highlights when returned by the provider.
- Store provider-specific score metadata and raw response safely (redacted where needed).
- Never use generated/mock detector percentages in real usage.

**Exit gate:** Real provider scores display accurately; limitations are explained; no unsupported score synthesis occurs.

### Phase 5 — Premium polish (only after all core modules)

- Improve rich editor and split comparison view.
- Add batch uploads, advanced exports, detailed analytics, keyboard shortcuts, advanced filters, accessibility and visual refinement.
- Do not allow polish work to delay or replace core functionality.

## 11. Coding execution rules

- First inspect repository state; do not overwrite or delete existing user work.
- Make small, coherent changes grouped by feature.
- Prefer typed functions, clear names, docstrings for non-obvious behavior, and useful logging.
- Avoid huge monolithic files and circular imports.
- Do not add dependencies without checking need, maintenance, license, compatibility, and Python version.
- Do not hardcode current provider model names or quotas as permanent truths. Keep provider/model selection configurable and discoverable where supported.
- Never place credentials in code, Markdown progress files, screenshots, test fixtures, or Git.
- Do not run destructive commands, wipe databases, reset Git, or delete user files without explicit instruction.
- Do not silently change UI framework, database, language, or architecture.
- Do not leave TODO-only implementations for a module and report it complete.
- Do not spend time building future modules as empty placeholders before the Humanizer works.
- If a third-party API requires credentials not yet available, implement a complete adapter/configuration flow with mocked contract tests, clearly mark the live integration as awaiting owner credentials, and continue with other work that can be completed honestly.
- If a provider's free access cannot be verified, do not label it free. Show its current configured status and cost category.

## 12. End-of-run report

At the end of the implementation run, provide a concise but complete report:

1. What is actually working now.
2. Which core phases are DONE, IN_PROGRESS, BLOCKED, or NOT_STARTED.
3. How to install dependencies and launch the app on Windows PowerShell.
4. Which environment variables/API keys the owner must add (names only; never request keys in chat).
5. Which live API integrations were tested versus only mock-tested.
6. Tests/build/browser checks executed and their exact results.
7. Known limitations and bugs.
8. Where progress and restart information is recorded.
9. The exact next action if work is incomplete.

Before finishing, update all progress/handoff/log documents. `AGENT_HANDOFF.md` must contain a clear restart instruction that a new OpenCode session can follow immediately.

---

## 13. Supabase + Vercel deployment rules (mandatory)

### Supabase Free plan constraints

Re-check at implementation time. Current pricing snapshot (19 November 2026) lists: 500 MB database, 1 GB Storage, 5 GB egress + 5 GB cached egress, 50 MB maximum file upload, and auto-pausing after one week of inactivity. Plan limits may change. Display usage warnings and implement document deletion/export. Do not claim unlimited storage or always-on availability.

### Vercel Hobby constraints

Re-check at implementation time. Current Vercel docs list 300 seconds maximum duration and 2 GB / 1 vCPU for Hobby Functions. Hobby Cron is limited to once per day, so Supabase Cron must trigger frequent worker ticks. Hobby usage is restricted to personal/non-commercial use; do not present this setup as a commercial SaaS deployment path.

### Job execution

- Supabase Queue/Postgres is the durable job source.
- Supabase Cron calls a private Vercel worker endpoint with `WORKER_CRON_SECRET`.
- The worker processes one or a small bounded number of chunks per invocation, writes outputs/checkpoints, acknowledges the message, and exits before the function deadline.
- Target an internal processing deadline of approximately 240 seconds, leaving cleanup time before the current 300-second maximum.
- Do not rely on Vercel Cron for per-minute scheduling or an always-on Python process.

### Storage and large uploads

- Upload directly to private Supabase Storage using signed URLs.
- Keep only metadata, object paths, and checkpoint data in Postgres.
- Use owner-scoped object paths and Storage RLS.
- The app has no arbitrary small word count cap, but file upload size, Supabase quotas, Vercel limits, and provider quotas apply.

### Secrets and authentication

- Supabase Auth is required for all protected routes.
- Disable public sign-up after creating the owner account.
- `SUPABASE_SECRET_KEY`, `SUPABASE_DB_URL`, provider API keys, `WORKER_CRON_SECRET`, and `PHRASIA_SECRET_ENCRYPTION_KEY` must remain server-side.
- RLS is mandatory on every owner-owned table and Storage bucket. Add automated tests proving unauthorized reads/writes fail.
- Never log text, credentials, auth tokens, or raw provider payloads.

### Official deployment docs

- Supabase Free pricing: https://supabase.com/pricing
- Supabase Auth: https://supabase.com/docs/guides/auth
- Supabase Storage: https://supabase.com/docs/guides/storage
- Supabase Queues: https://supabase.com/docs/guides/queues
- Supabase Cron: https://supabase.com/docs/guides/cron
- Supabase Python: https://supabase.com/docs/reference/python/introduction
- Vercel Python/FastAPI: https://vercel.com/kb/guide/ship-a-fastapi-app-on-vercel
- Vercel limits: https://vercel.com/docs/limits
- Vercel Hobby terms: https://vercel.com/legal/terms
- Reflex hosting: https://reflex.dev/docs/hosting/self-hosting/

## 14. Start now

Begin by checking the current working directory and repository status. Confirm that both specification files exist. Read them completely. Then initialize or update the progress documents and proceed with Phase 0 followed by Phase 1 Humanizer. Continue through Phases 2, 3, and 4 in order without waiting for separate approval, while maintaining all security, API-cost, privacy, and quality gates above.

**Do not stop after producing a plan. Implement, test, record progress, and continue.**


---

**Revision note:** This Phrasia master prompt supersedes the earlier `OpenCode_Master_Build_Prompt.md`. Phrasia branding and Supabase + Vercel requirements are mandatory.
