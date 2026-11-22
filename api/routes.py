"""API route definitions — FastAPI-style for Vercel Python Functions."""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Any

from core.ai_detector import scan as scan_text
from core.humanizer_service import HumanizerService
from humanizer_layer import humanize_layer
from phrasia_domain import HumanizationMode, JobStatus, RewriteIntensity, RoutingMode
from providers import credentials
from providers.base import ProviderConfig, ProviderRegistry, ProviderTask, ProviderTier
from providers.generation.anthropic import AnthropicAdapter
from providers.generation.custom import CustomAdapter
from providers.generation.freellmapi import FreeLLMAPIAdapter
from providers.generation.gemini import GeminiAdapter
from providers.generation.groq import GroqAdapter
from providers.generation.openai import OpenAIAdapter
from providers.generation.openrouter import OpenRouterAdapter
from providers.model_catalog import fetch_models
from providers.router import ProviderRouter

logger = logging.getLogger(__name__)


def _local_layer_enabled() -> bool:
    return os.environ.get("ENABLE_LOCAL_LAYER", "true").strip().lower() not in {
        "0", "false", "no", "off",
    }


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value) if value is not None else default


# Declarative provider catalog. Values are resolved at request time so keys
# saved from Settings take effect without restarting the server.
PROVIDER_SPECS: list[dict] = [
    {
        "provider_id": "freellmapi",
        "display_name": "FreeLLMAPI (local gateway)",
        "key_env": "FREELLMAPI_API_KEY",
        "model_env": "FREELLMAPI_MODEL",
        "default_model": "auto",
        "base_url_env": "FREELLMAPI_BASE_URL",
        "default_base_url": "http://127.0.0.1:3001/v1",
        "tier": ProviderTier.FREE,
        "priority": 10,
    },
    {
        "provider_id": "gemini",
        "display_name": "Google Gemini",
        "key_env": "GEMINI_API_KEY",
        "model_env": "GEMINI_MODEL",
        "default_model": "gemini-2.0-flash",
        "base_url_env": "GEMINI_BASE_URL",
        "default_base_url": "https://generativelanguage.googleapis.com/v1beta",
        "tier": ProviderTier.TRIAL,
        "priority": 20,
    },
    {
        "provider_id": "groq",
        "display_name": "Groq",
        "key_env": "GROQ_API_KEY",
        "model_env": "GROQ_MODEL",
        "default_model": "llama-3.3-70b-specdec",
        "base_url_env": "GROQ_BASE_URL",
        "default_base_url": "https://api.groq.com/openai/v1",
        "tier": ProviderTier.FREE,
        "priority": 30,
    },
    {
        "provider_id": "openrouter",
        "display_name": "OpenRouter",
        "key_env": "OPENROUTER_API_KEY",
        "model_env": "OPENROUTER_MODEL",
        "default_model": "openrouter/auto",
        "base_url_env": "OPENROUTER_BASE_URL",
        "default_base_url": "https://openrouter.ai/api/v1",
        "tier": ProviderTier.TRIAL,
        "priority": 40,
    },
    {
        "provider_id": "custom",
        "display_name": "Custom endpoint",
        "key_env": "CUSTOM_API_KEY",
        "model_env": "CUSTOM_MODEL",
        "default_model": "",
        "base_url_env": "CUSTOM_BASE_URL",
        "default_base_url": "",
        "tier": ProviderTier.TRIAL,
        "priority": 50,
        "requires_base_url": True,
        "requires_model": True,
        "key_optional": True,
    },
    {
        "provider_id": "openai",
        "display_name": "OpenAI",
        "key_env": "OPENAI_API_KEY",
        "model_env": "OPENAI_MODEL",
        "default_model": "gpt-4o-mini",
        "base_url_env": "OPENAI_BASE_URL",
        "default_base_url": "https://api.openai.com/v1",
        "tier": ProviderTier.PAID,
        "priority": 90,
    },
    {
        "provider_id": "anthropic",
        "display_name": "Anthropic",
        "key_env": "ANTHROPIC_API_KEY",
        "model_env": "ANTHROPIC_MODEL",
        "default_model": "claude-3-5-haiku-20241022",
        "base_url_env": "ANTHROPIC_BASE_URL",
        "default_base_url": "https://api.anthropic.com/v1",
        "tier": ProviderTier.PAID,
        "priority": 95,
    },
]


def spec_for(provider_id: str) -> dict | None:
    return next(
        (s for s in PROVIDER_SPECS if s["provider_id"] == provider_id),
        None,
    )


def _effective(provider_id: str, spec: dict) -> dict:
    """Resolve saved-vs-env configuration for one provider."""
    base_url = credentials.resolve_setting(
        provider_id, "base_url", spec.get("base_url_env"), spec["default_base_url"]
    )
    model = credentials.resolve_setting(
        provider_id, "model", spec.get("model_env"), spec["default_model"]
    )
    api_key = credentials.resolve_secret(provider_id, spec["key_env"])
    record = credentials.get_provider(provider_id)

    if record.get("enabled") is False:
        enabled = False
    elif record.get("enabled") is True:
        enabled = True
    elif spec.get("requires_base_url") and not base_url:
        enabled = False
    elif spec.get("requires_model") and not model:
        enabled = False
    elif spec.get("key_optional"):
        enabled = bool(api_key) or bool(base_url)
    else:
        enabled = bool(api_key)

    return {"api_key": api_key, "base_url": base_url, "model": model, "enabled": enabled}


def _make_registry() -> ProviderRegistry:
    reg = ProviderRegistry()
    for spec in PROVIDER_SPECS:
        effective = _effective(spec["provider_id"], spec)
        display_name = (
            credentials.get_provider(spec["provider_id"]).get("display_name")
            or spec["display_name"]
        )
        reg.register(
            ProviderConfig(
                provider_id=spec["provider_id"],
                display_name=display_name,
                task_type=ProviderTask.GENERATION,
                tier=spec["tier"],
                enabled=effective["enabled"],
                priority=spec["priority"],
                default_model=effective["model"] or spec["default_model"],
                base_url=effective["base_url"] or spec["default_base_url"],
            )
        )
    return reg


def refresh_registry() -> tuple[ProviderRegistry, ProviderRouter]:
    """Rebuild the registry so Settings changes apply immediately."""
    registry = _make_registry()
    return registry, ProviderRouter(registry)


_FACTORIES: dict[str, type] = {
    "freellmapi": FreeLLMAPIAdapter,
    "gemini": GeminiAdapter,
    "groq": GroqAdapter,
    "openrouter": OpenRouterAdapter,
    "custom": CustomAdapter,
    "openai": OpenAIAdapter,
    "anthropic": AnthropicAdapter,
}


def _preferred_provider() -> str:
    return (
        credentials.get_preference("preferred_provider", "")
        or os.environ.get("HUMANIZER_PRIMARY_PROVIDER", "")
        or ""
    )



def _json_response(status_code: int, body: Any) -> dict:
    return {
        "status_code": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _text_response(status_code: int, text: str) -> dict:
    return {
        "status_code": status_code,
        "headers": {"Content-Type": "text/plain; charset=utf-8"},
        "body": text,
    }


async def handle_health() -> dict:
    registry, _router = refresh_registry()
    providers_info = []
    for cfg in registry.list_all():
        if cfg.task_type.name == "GENERATION" and cfg.enabled:
            try:
                adapter_cls = _FACTORIES.get(cfg.provider_id)
                if adapter_cls:
                    h = await adapter_cls(config=cfg).health_check()
                    providers_info.append({
                        "id": cfg.provider_id,
                        "healthy": h.healthy,
                        "status": h.message,
                    })
            except Exception:
                providers_info.append({"id": cfg.provider_id, "healthy": False})
    return {
        "ok": True,
        "providers": providers_info,
        "env": {"supabase_configured": bool(os.environ.get("SUPABASE_URL"))},
    }



async def handle_humanize(payload: dict[str, Any]) -> dict:
    input_text = payload.get("input_text", "").strip()
    mode = payload.get("mode", "natural")
    intensity = payload.get("intensity", "balanced")
    custom_instruction = payload.get("custom_instruction", "") or None
    allow_paid = payload.get("allow_paid", False) and bool(os.environ.get("PAID_PROVIDERS_ENABLED"))

    # Optional local post-processing controls (validated/clamped).
    try:
        strength = float(payload.get("strength", 0.6))
    except (TypeError, ValueError):
        strength = 0.6
    strength = max(0.0, min(1.0, strength))
    formal = _coerce_bool(payload.get("formal", False))

    if not input_text:
        return _json_response(400, {"error": "input_text is required"})

    digest = hashlib.md5(input_text.encode()).hexdigest()[:8]
    job_id = f"job-{datetime.utcnow().isoformat()}_{digest}"

    options = type("_Opt", (), {
        "mode": HumanizationMode(mode),
        "intensity": RewriteIntensity(intensity),
        "preserve_meaning": payload.get("preserve_meaning", True),
        "preserve_facts": payload.get("preserve_facts", True),
        "preserve_citations": payload.get("preserve_citations", True),
        "preserve_formatting": payload.get("preserve_formatting", True),
        "preserve_quotes": payload.get("preserve_quotes", True),
        "custom_instruction": custom_instruction,
        "target_language": payload.get("target_language"),
        "deep_humanize": bool(payload.get("deep_humanize", False)),
    })()

    routing_mode = RoutingMode(
        payload.get("routing_mode")
        or credentials.get_preference("routing_mode")
        or "free_only"
    )
    registry, router = refresh_registry()

    service = HumanizerService(
        router=router,
        provider_factories=_FACTORIES,
    )

    job, warnings = await service.create_job(
        job_id=job_id,
        document_id=payload.get("document_id", "local"),
        input_text=input_text,
        options=options,
        routing_mode=routing_mode,
        allow_paid=allow_paid,
    )

    budget_usd = float(os.environ.get("PAID_MONTHLY_BUDGET_USD", "0") or 0)
    paid_enabled = allow_paid and bool(os.environ.get("PAID_PROVIDERS_ENABLED"))
    preferred = _preferred_provider()

    completed_chunks = {}
    failed_chunks = []
    provider_used = ""
    model_used = ""
    last_error = None

    while True:
        more, ok = await service.process_next_chunk(
            job,
            paid_enabled=paid_enabled,
            monthly_budget_usd=budget_usd,
            preferred_provider_id=preferred or None,
            use_fallback=True,
        )
        if not ok:
            failed_chunks.extend(
                c.chunk_id
                for c in job.chunks
                if c.chunk_id not in job.completed_chunks
            )
            break
        completed_chunks.update(job.completed_chunks)
        provider_used = job.current_provider or ""
        model_used = job.current_model or ""
        if not more:
            break
        if len(completed_chunks) + len(failed_chunks) >= len(job.chunks):
            break

    if job.failed_chunks:
        last_error = job.last_error_message_safe
        status = JobStatus.FAILED.value if not job.status else job.status.value
    elif job.status == JobStatus.COMPLETED:
        status = JobStatus.COMPLETED.value
    else:
        status = job.status.value if hasattr(job, "status") else "failed"

    output = service.assemble_output(job) if job.completed_chunks else ""

    # Local post-processing layer — never called on empty or error responses,
    # and never allowed to break the request.
    if output.strip() and not job.failed_chunks and _local_layer_enabled():
        api_text = output
        try:
            output = humanize_layer(api_text, strength=strength, seed=None, formal=formal)
        except Exception:
            logger.exception("Local humanizer layer failed; returning original API text")
            output = api_text

    return _json_response(200, {
        "job_id": job_id,
        "status": status,
        "total_chunks": len(job.chunks),
        "completed_chunks": len(completed_chunks),
        "failed_chunks": failed_chunks,
        "warnings": warnings,
        "provider_used": provider_used,
        "model_used": model_used,
        "output": output,
        "error_message": last_error,
    })


async def handle_providers() -> dict:
    registry, _router = refresh_registry()
    info = []
    for cfg in registry.list_all():
        spec = spec_for(cfg.provider_id) or {}
        summary = credentials.provider_summary(
            cfg.provider_id, spec.get("key_env", "")
        )
        info.append({
            "provider_id": cfg.provider_id,
            "display_name": cfg.display_name,
            "tier": cfg.tier.value,
            "enabled": cfg.enabled,
            "default_model": cfg.default_model,
            "priority": cfg.priority,
            "secret_source": summary["source"],
            "secret_masked": summary["masked"],
            "base_url": cfg.base_url,
        })
    return _json_response(200, {"providers": info})



async def handle_scan(payload: dict[str, Any]) -> dict:
    """Offline writing-style scan (no text leaves the machine)."""
    text = str(payload.get("text") or "")
    return _json_response(200, scan_text(text).as_dict())


async def handle_models(payload: dict[str, Any]) -> dict:
    """Return the (non-secret) model catalog for one provider."""
    provider_id = str(payload.get("provider") or "")
    spec = spec_for(provider_id)
    if spec is None:
        return _json_response(404, {"error": f"Unknown provider: {provider_id}"})

    effective = _effective(provider_id, spec)
    catalog = await fetch_models(
        provider_id,
        base_url=effective["base_url"],
        api_key=effective["api_key"],
        provider_tier=spec["tier"].value,
    )
    return _json_response(200, catalog.as_dict())


async def handler(request: Any) -> dict:
    """Entry point for Vercel Python Functions."""
    method = getattr(request, "method", request.get("httpMethod", "GET")).upper()
    path = getattr(request, "path", request.get("rawPath", "/"))
    raw_body = getattr(request, "body", request.get("body", "{}"))

    if path.startswith("/api/health"):
        return await handle_health()
    if path.startswith("/api/providers"):
        if method == "GET":
            return await handle_providers()
    if path.startswith("/api/scan"):
        if method == "POST":
            try:
                payload = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
            except Exception:
                payload = {}
        else:
            payload = {}
        return await handle_scan(payload)
    if path.startswith("/api/models"):
        if method == "POST":
            try:
                payload = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
            except Exception:
                payload = {}
        else:
            query = path.split("?", 1)[1] if "?" in path else ""
            payload = dict(
                part.split("=", 1) for part in query.split("&") if "=" in part
            )
        return await handle_models(payload)
    if path.startswith("/api/humanize"):
        if method == "POST":
            try:
                payload = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
            except Exception:
                payload = {}
            return await handle_humanize(payload)

    return _json_response(404, {"error": "not found"})
