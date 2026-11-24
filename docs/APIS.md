# External APIs

Phrasia uses external HTTP APIs for the humanizer and (optionally) plagiarism/AI detection. All endpoints below were checked with real, unauthenticated requests on **2026-11-24** from the development machine. Where no free, verified API was found, nothing is invented.

| Provider | Endpoint used | Auth | Free tier | Rate limit | Liveness check |
|---|---|---|---|---|---|
| Google Gemini | `POST {base}/models/{model}:generateContent`, `GET {base}/models` | `x-goog-api-key` header | Yes, account-dependent quota | Account-dependent | `GET https://generativelanguage.googleapis.com/v1beta/models` → **403** (requires key; endpoint alive) |
| Groq | `POST {base}/chat/completions`, `GET {base}/models` | `Authorization: Bearer` | Yes, account-dependent RPM/RPD | Account-dependent | `GET https://api.groq.com/openai/v1/models` → **401** (requires key; endpoint alive) |
| OpenRouter | `POST {base}/chat/completions`, `GET {base}/models` | `Authorization: Bearer` | Free `:free` models | Account-dependent | `GET https://openrouter.ai/api/v1/models` → **200** (public) |
| Custom OpenAI-compatible | `POST {base}/chat/completions` | Optional bearer | Depends on endpoint | Depends on endpoint | Configured by the owner |

Default base URLs and model IDs live in `backend/providers/catalog.py`. Paid models are filtered out unless `PAID_MODELS_ENABLED=true`.

## Plagiarism web-check candidate (verified, not usable for free)

- **Winston AI** — documented at <https://winstonai.ai/api-docs> (`POST /api/v1/plagiarism`), openapi spec fetched → 200. But it requires a bearer token: `POST https://winstonai.ai/api/v1/plagiarism` without one → **401 `authentication_error` / `unauthorized`**. Credit-based; copyright message says "Included with Pro". No free key available, so **not added**.
- **plagiarism.free** — `POST https://plagiarism.free/api/v1/check/` → **401 `missing_bearer_token`** ("Sign in to get your API key"). Bearer key is also required, so **not added**.

**Result: Phrasia ships only the local similarity check (word shingles + difflib matched passages against your own reference library) — implementation (a) above; no verified free web API was found.**

Every provider call has a timeout and bounded exponential backoff. Error messages returned to the UI never include response bodies or keys.
