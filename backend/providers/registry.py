"""Build ready provider instances from catalog specs and SQLite overrides."""
from __future__ import annotations

from dataclasses import dataclass

from backend.db import repository
from backend.providers import catalog
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
    source: str  # "saved" | "none"
    masked_key: str
    model: str
    base_url: str


class ProviderRegistry:
    """Builds providers from SQLite overrides, then the catalog defaults."""

    def _values(self, spec: catalog.ProviderSpec) -> dict[str, str]:
        saved = repository.provider_setting(spec.id) or {}
        key = str(saved.get("api_key") or "").strip()
        model = str(saved.get("model") or spec.model).strip()
        base = str(saved.get("base_url") or spec.base_url).strip().rstrip("/")
        return {"key": key, "model": model, "base": base}

    def resolve(self, provider_id: str) -> ConfiguredProvider | None:
        spec = catalog.get_spec(provider_id)
        if spec is None or not spec.enabled:
            return None
        values = self._values(spec)
        if spec.requires_key and not values["key"]:
            return None
        provider = OpenAICompatibleProvider(
            provider_id=provider_id,
            api_key=values["key"],
            model=values["model"],
            base_url=values["base"],
        )
        return ConfiguredProvider(
            spec=spec,
            provider=provider,
            source="saved" if values["key"] else "none",
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
        providers.sort(key=lambda item: item.spec.priority)
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
            items.append(
                {
                    "id": spec.id,
                    "name": spec.name,
                    "anonymous": spec.anonymous,
                    "requires_key": spec.requires_key,
                    "configured": self.resolve(spec.id) is not None,
                    "source": "saved" if record.get("api_key") else "none",
                    "masked_key": mask_key(values["key"]),
                    "model": values["model"],
                    "base_url": values["base"],
                    "enabled": int(record["enabled"]) if record.get("enabled") is not None else 1,
                    "rate_limit_requests_per_minute": spec.rate_limit_requests_per_minute,
                }
            )
        return items

    async def test(self, provider_id: str) -> tuple[bool, str]:
        configured = self.resolve(provider_id)
        if configured is None:
            return False, "This provider is not configured."
        return await configured.provider.health()
