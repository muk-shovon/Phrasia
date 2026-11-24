# External APIs

Phrasia is a directory consumer of third-party LLM APIs. Every endpoint below was probed with real requests on 2026-11-24 (see "Verified" dates). Errors were captured verbatim where noted.

| Provider | Endpoint used | Auth | Free tier | Rate limit | Liveness check |
|---|---|---|---|---|---|
| Pollinations (text.pollinations.ai) | `POST https://text.pollinations.ai/openai/chat/completions`, `GET https://text.pollinations.ai/models` | None (anonymous) | Yes | Not documented; briefly rate-limited (429) | `GET models` → 200; "Say OK" → 200 (0.51s); ~300-word rewrite → 200 (8.45s), complete |
| OVHcloud AI Endpoints (anonymous lane) | `POST https://oai.endpoints.kepler.ai.cloud.ovh.net/v1/chat/completions`, `GET .../v1/models` | None (anonymous; token per docs) | Free | Anonymous lane: "Say OK" → 429 `{"message":"API rate limit exceeded"}` during probe; rewrite via `gpt-oss-20b` → 200 | `GET models` → 200 (33 models); rewrite → 200, complete |

Other providers used by Phrasia (`backend/providers/catalog.py`): Google Gemini (`POST {base}/models/{model}:generateContent`, key via `x-goog-api-key` — probed `GET .../v1beta/models` → 403, key required), Groq (`POST {base}/chat/completions`, `GET /models` → 401 probed), OpenRouter (`POST /chat/completions`, `GET https://openrouter.ai/api/v1/models` → 200 probed), and custom OpenAI-compatible endpoints.

**No local models are downloaded or run** — everything is cloud HTTP.
