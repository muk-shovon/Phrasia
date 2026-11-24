# External APIs

Phrasia is a directory consumer, not an API vendor. Only the endpoints below are used. The [public-apis directory](https://github.com/public-apis/public-apis) was treated as a discovery aid; every endpoint listed here was checked directly.

Checked on **2026-11-24** with unauthenticated requests from the development machine. No provider API key was available in this environment, so only endpoint liveness — not generation — was exercised.

| Provider | Endpoint used | Auth | Free tier | Rate limit | Liveness check |
|---|---|---|---|---|---|
| Google Gemini | `POST {base}/models/{model}:generateContent`, `GET {base}/models` | `x-goog-api-key` header (or `GEMINI_API_KEY` in `.env`) | Yes, account-dependent quota | Account-dependent; see provider docs | `GET .../v1beta/models` → **403** (key required, endpoint alive) |
| Groq | `POST {base}/chat/completions`, `GET {base}/models` | `Authorization: Bearer` (or `GROQ_API_KEY`) | Yes, account-dependent RPM/RPD | Account-dependent; see console | `GET .../openai/v1/models` → **401** (key required, endpoint alive) |
| OpenRouter | `POST {base}/chat/completions`, `GET {base}/models` | `Authorization: Bearer` (or `OPENROUTER_API_KEY`) | `:free` models | Account-dependent; see provider docs | `GET .../api/v1/models` → **200** (public model list) |
| Custom OpenAI-compatible | `POST {base}/chat/completions` | Optional bearer key | Depends on endpoint | Depends on endpoint | Configured by owner; no default endpoint |

Default base URLs and model IDs live in `backend/providers/catalog.py` — that file is the single source of truth. The catalog is filtered before a job starts: a model marked `paid` is unavailable unless `PAID_MODELS_ENABLED=true`. Custom base URLs must be public `http(s)` endpoints; loopback and private ranges are rejected.

No additional third-party API is used:

- Similarity checking is local n-gram comparison against the owner's reference library (`backend/core/plagiarism.py`). There is no internet-wide plagiarism provider, and the UI says so.
- The style signal is a local keyword/rhythm heuristic (`backend/core/detector.py`). It is labelled "Local style signal", returns no percentage verdict, and makes no authorship claim.

Every provider call has a timeout and bounded exponential backoff. Error messages returned to the UI never include response bodies or keys.

Reference documentation: [Gemini API](https://ai.google.dev/gemini-api/docs), [Groq API](https://console.groq.com/docs/quickstart), [OpenRouter API](https://openrouter.ai/docs).
