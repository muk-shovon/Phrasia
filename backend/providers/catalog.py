"""Single source of truth for provider specs and the model catalog.

Add or remove providers/models here only. The settings UI, the humanizer and
the API all read this module.
"""
from __future__ import annotations

from dataclasses import dataclass

from backend.config import PAID_MODELS_ENABLED


@dataclass(frozen=True)
class ModelSpec:
    id: str
    label: str
    paid: bool = False


@dataclass(frozen=True)
class ProviderSpec:
    id: str
    name: str
    adapter: str  # "gemini" | "openai_compatible"
    tier: str  # "free" | "paid"
    env_key: str
    env_model: str
    env_base: str
    default_model: str
    default_base: str
    priority: int
    notes: str
    requires_key: bool = True


PROVIDERS: tuple[ProviderSpec, ...] = (
    ProviderSpec(
        id="gemini",
        name="Google Gemini",
        adapter="gemini",
        tier="free",
        env_key="GEMINI_API_KEY",
        env_model="GEMINI_MODEL",
        env_base="GEMINI_BASE_URL",
        default_model="gemini-2.5-flash",
        default_base="https://generativelanguage.googleapis.com/v1beta",
        priority=10,
        notes="Free-tier Gemini API. Quotas depend on your Google account.",
    ),
    ProviderSpec(
        id="groq",
        name="Groq",
        adapter="openai_compatible",
        tier="free",
        env_key="GROQ_API_KEY",
        env_model="GROQ_MODEL",
        env_base="GROQ_BASE_URL",
        default_model="llama-3.3-70b-versatile",
        default_base="https://api.groq.com/openai/v1",
        priority=20,
        notes="Free-tier Groq API with OpenAI-compatible chat completions.",
    ),
    ProviderSpec(
        id="openrouter",
        name="OpenRouter",
        adapter="openai_compatible",
        tier="free",
        env_key="OPENROUTER_API_KEY",
        env_model="OPENROUTER_MODEL",
        env_base="OPENROUTER_BASE_URL",
        default_model="meta-llama/llama-3.3-70b-instruct:free",
        default_base="https://openrouter.ai/api/v1",
        priority=30,
        notes="OpenRouter routes to many models. Only :free models are enabled unless paid models are turned on.",
    ),
    ProviderSpec(
        id="custom",
        name="Custom OpenAI-compatible endpoint",
        adapter="openai_compatible",
        tier="free",
        env_key="CUSTOM_API_KEY",
        env_model="CUSTOM_MODEL",
        env_base="CUSTOM_BASE_URL",
        default_model="",
        default_base="",
        priority=40,
        notes="Any online endpoint that speaks /chat/completions. Base URL and model are required.",
        requires_key=False,
    ),
)


MODELS: dict[str, tuple[ModelSpec, ...]] = {
    "gemini": (
        ModelSpec("gemini-2.5-flash", "Gemini 2.5 Flash"),
        ModelSpec("gemini-2.5-flash-lite", "Gemini 2.5 Flash Lite"),
        ModelSpec("gemini-2.0-flash", "Gemini 2.0 Flash"),
        ModelSpec("gemini-2.0-flash-lite", "Gemini 2.0 Flash Lite"),
        ModelSpec("gemini-2.5-pro", "Gemini 2.5 Pro", paid=True),
    ),
    "groq": (
        ModelSpec("llama-3.3-70b-versatile", "Llama 3.3 70B Versatile"),
        ModelSpec("llama-3.1-8b-instant", "Llama 3.1 8B Instant"),
        ModelSpec("openai/gpt-oss-120b", "GPT-OSS 120B"),
        ModelSpec("openai/gpt-oss-20b", "GPT-OSS 20B"),
        ModelSpec("gemma2-9b-it", "Gemma 2 9B"),
    ),
    "openrouter": (
        ModelSpec(
            "meta-llama/llama-3.3-70b-instruct:free",
            "Llama 3.3 70B Instruct (free)",
        ),
        ModelSpec(
            "google/gemini-2.0-flash-exp:free",
            "Gemini 2.0 Flash Exp (free)",
        ),
        ModelSpec(
            "deepseek/deepseek-r1:free",
            "DeepSeek R1 (free)",
        ),
        ModelSpec("deepseek/deepseek-chat", "DeepSeek Chat", paid=True),
        ModelSpec("openai/gpt-4o-mini", "GPT-4o mini", paid=True),
        ModelSpec("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet", paid=True),
    ),
    "custom": (),
}


def get_spec(provider_id: str) -> ProviderSpec | None:
    return next((spec for spec in PROVIDERS if spec.id == provider_id), None)


def get_model(provider_id: str, model_id: str) -> ModelSpec | None:
    return next(
        (model for model in MODELS.get(provider_id, ()) if model.id == model_id),
        None,
    )


def model_is_paid(provider_id: str, model_id: str) -> bool:
    """Unknown/custom models are treated as user-managed, not catalog-paid."""
    model = get_model(provider_id, model_id)
    return bool(model and model.paid)


def model_allowed(provider_id: str, model_id: str) -> bool:
    return PAID_MODELS_ENABLED or not model_is_paid(provider_id, model_id)


def models_for(provider_id: str, *, include_paid: bool = True) -> list[dict[str, object]]:
    return [
        {
            "id": model.id,
            "label": model.label,
            "paid": model.paid,
            "enabled": include_paid or not model.paid,
        }
        for model in MODELS.get(provider_id, ())
    ]
