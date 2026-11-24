"""Resolve saved/environment configuration into ready provider instances."""
from __future__ import annotations

import os
from dataclasses import dataclass

from backend.config import PAID_MODELS_ENABLED
from backend.db import repository
from backend.providers import catalog
from backend.providers.adapters.gemini import GeminiProvider
from backend.providers.adapters.openai_compatible import OpenAICompatibleProvider
from backend.providers.base import Provider


def mask_key(key: str) -> str:
    value = (key or "").strip()
    if not value:
        return ""
    if len(value) <= 8:
        return "••••••••"
    return f"••••{value[-4:]}"


@dataclass
class ConfiguredProvider:
    spec: catalog.ProviderSpec
    provider: Provider
    source: str  # "saved" | "env"
    masked_key: str
    model: str
    base_url: str


class ProviderRegistry:
    """Builds providers from SQLite overrides first, then environment variables."""

    def _values(self, spec: catalog.ProviderSpec) -> dict[str, str]:
        saved = repository.provider_setting(spec.id) or {}
        key = str(saved.get("api_key") or os.environ.get(spec.env_key) or "").strip()
        model = str(
            saved.get("model") or os.environ.get(spec.env_model) or spec.default_model
        ).strip()
        base = str(
            saved.get("base_url") or os.environ.get(spec.env_base) or spec.default_base
        ).strip().rstrip("/")
        return {"key": key, "model": model, "base": base}

    def resolve(self, provider_id: str) -> ConfiguredProvider | None:
        spec = catalog.get_spec(provider_id)
        if spec is None:
            return None
        values = self._values(spec)
        saved = repository.provider_setting(provider_id) or {}
        if saved.get("enabled") is not None and int(saved["enabled"]) == 0:
            return None
        if spec.requires_key and not values["key"]:
            return None
        if spec.id == "custom" and (not values["base"] or not values["model"]):
            return None
        if not catalog.model_allowed(provider_id, values["model"]):
            return None

        source = "saved" if saved.get("api_key") else ("env" if values["key"] else "none")
        if spec.adapter == "gemini":
            provider: Provider = GeminiProvider(
                api_key=values["key"],
                model=values["model"],
                base_url=values["base"],
            )
        else:
            provider = OpenAICompatibleProvider(
                provider_id=provider_id,
                api_key=values["key"],
                model=values["model"],
                base_url=values["base"],
            )
        return ConfiguredProvider(
            spec=spec,
            provider=provider,
            source=source,
            masked_key=mask_key(values["key"]),
            model=values["model"],
            base_url=values["base"],
        )

    def preferred_provider_id(self) -> str | None:
        value = repository.get_preference("preferred_provider", "") or ""
        return value or None

    def configured(self) -> list[ConfiguredProvider]:
        providers = [
            configured
            for spec in catalog.PROVIDERS
            if (configured := self.resolve(spec.id)) is not None
        ]
        preferred = self.preferred_provider_id()
        providers.sort(
            key=lambda item: (
                0 if item.spec.id == preferred else 1,
                item.spec.priority,
            )
        )
        return providers

    def get(self, provider_id: str) -> ConfiguredProvider | None:
        return next(
            (item for item in self.configured() if item.spec.id == provider_id),
            None,
        )

    def settings_view(self) -> list[dict[str, object]]:
        saved = repository.provider_settings()
        items: list[dict[str, object]] = []
        for spec in catalog.PROVIDERS:
            values = self._values(spec)
            record = saved.get(spec.id) or {}
            resolved = self.resolve(spec.id)
            source = (
                "saved"
                if record.get("api_key")
                else ("env" if os.environ.get(spec.env_key) else "none")
            )
            items.append(
                {
                    "id": spec.id,
                    "name": spec.name,
                    "tier": spec.tier,
                    "notes": spec.notes,
                    "env_key": spec.env_key,
                    "requires_key": spec.requires_key,
                    "requires_base_url": spec.id == "custom",
                    "configured": resolved is not None,
                    "source": source,
                    "masked_key": mask_key(values["key"]),
                    "model": values["model"],
                    "base_url": values["base"],
                    "enabled": record.get("enabled"),
                    "models": catalog.models_for(spec.id),
                }
            )
        return items

    async def test(self, provider_id: str) -> tuple[bool, str]:
        configured = self.resolve(provider_id)
        if configured is None:
            return False, "This provider is not configured."
        return await configured.provider.health()


def paid_models_enabled() -> bool:
    return PAID_MODELS_ENABLED
