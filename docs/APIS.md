# External APIs

Phrasia is a directory consumer of LLM APIs (anonymous lanes, verified 2026-11-24 with real requests) plus a real web search via `ddgs` (verified live).

| Provider | Endpoint used | Auth | Free tier | Rate limit | Liveness check |
|---|---|---|---|---|---|
| Pollinations | `POST https://text.pollinations.ai/openai/chat/completions` | None (anonymous) | Yes | ~60 req/min per lane | "Say OK" → 200 (0.51s) |
| OVHcloud AI Endpoints (anonymous) | `POST https://oai.endpoints.kepler.ai.cloud.ovh.net/v1/chat/completions` | None | Yes | Anonymous lane rate-limited at times (429 `API rate limit exceeded`); ~2 req/min effectively | models → 200, chat → 200 |

`GET /models` for OVHcloud → 200 (33 models), verified.

Plagiarism web check: ddgs (see above).

No other third-party APIs are used: no local models, no internet-wide plagiarism, no auth gate.
