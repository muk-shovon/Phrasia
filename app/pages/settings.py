"""Settings page — per-provider API keys, custom endpoints, and routing."""
from __future__ import annotations

import asyncio
import os

import reflex as rx

from app.components import app_header
from app.ui_tokens import (
    BG_CARD,
    BG_PAGE,
    BORDER,
    TEAL_HOVER,
    TEAL_SOLID,
    TEXT_MUTED,
    TEXT_PRIMARY,
)
from providers import credentials

# UI catalog. Keep in sync with ``api.routes.PROVIDER_SPECS``.
PROVIDER_CATALOG = [
    {
        "id": "gemini",
        "name": "Google Gemini",
        "tagline": "Free tier · native Gemini API",
        "tier": "trial",
        "env": "GEMINI_API_KEY",
        "model_env": "GEMINI_MODEL",
        "default_model": "gemini-2.0-flash",
        "base_env": "GEMINI_BASE_URL",
        "default_base": "",
        "show_base": False,
    },
    {
        "id": "groq",
        "name": "Groq",
        "tagline": "Fast free tier · OpenAI-compatible",
        "tier": "free",
        "env": "GROQ_API_KEY",
        "model_env": "GROQ_MODEL",
        "default_model": "llama-3.3-70b-specdec",
        "base_env": "GROQ_BASE_URL",
        "default_base": "",
        "show_base": False,
    },
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "tagline": "One key for many models, including free ones",
        "tier": "trial",
        "env": "OPENROUTER_API_KEY",
        "model_env": "OPENROUTER_MODEL",
        "default_model": "openrouter/auto",
        "base_env": "OPENROUTER_BASE_URL",
        "default_base": "https://openrouter.ai/api/v1",
        "show_base": True,
    },
    {
        "id": "custom",
        "name": "Custom endpoint",
        "tagline": "Any OpenAI-compatible URL — Ollama, LM Studio, vLLM, LiteLLM",
        "tier": "trial",
        "env": "CUSTOM_API_KEY",
        "model_env": "CUSTOM_MODEL",
        "default_model": "",
        "base_env": "CUSTOM_BASE_URL",
        "default_base": "",
        "show_base": True,
        "show_name": True,
    },
    {
        "id": "freellmapi",
        "name": "FreeLLMAPI (local gateway)",
        "tagline": "OpenAI-compatible gateway running on your machine",
        "tier": "free",
        "env": "FREELLMAPI_API_KEY",
        "model_env": "FREELLMAPI_MODEL",
        "default_model": "auto",
        "base_env": "FREELLMAPI_BASE_URL",
        "default_base": "http://127.0.0.1:3001/v1",
        "show_base": True,
    },
    {
        "id": "openai",
        "name": "OpenAI",
        "tagline": "Paid · requires PAID_PROVIDERS_ENABLED plus a budget",
        "tier": "paid",
        "env": "OPENAI_API_KEY",
        "model_env": "OPENAI_MODEL",
        "default_model": "gpt-4o-mini",
        "base_env": "OPENAI_BASE_URL",
        "default_base": "",
        "show_base": False,
    },
    {
        "id": "anthropic",
        "name": "Anthropic",
        "tagline": "Paid · native Messages API",
        "tier": "paid",
        "env": "ANTHROPIC_API_KEY",
        "model_env": "ANTHROPIC_MODEL",
        "default_model": "claude-3-5-haiku-20241022",
        "base_env": "ANTHROPIC_BASE_URL",
        "default_base": "",
        "show_base": False,
    },
]


def _spec(provider_id: str) -> dict:
    return next(s for s in PROVIDER_CATALOG if s["id"] == provider_id)


AUTO_LABEL = "Auto — priority order + fallback"
MANUAL_LABEL = "Manual — type a model id"
FILTERS = (("all", "All"), ("free", "Free"), ("paid", "Paid"))


class SettingsState(rx.State):
    """Credential drafts plus a safe (masked) status map for rendering."""

    draft: dict[str, str] = {}
    status: dict[str, str] = {}
    provider_options: list[str] = [AUTO_LABEL]
    preferred: str = "auto"
    preferred_label: str = AUTO_LABEL
    routing_mode: str = "free_only"
    flash: str = ""
    flash_level: str = "success"
    supabase_configured: bool = False
    paid_enabled: bool = False

    # ── Model catalog state ───────────────────────────────────────────────────
    models_all: dict[str, list[str]] = {}      # provider id -> all model ids
    model_tiers: dict[str, str] = {}           # "pid:model" -> free/paid/unknown
    model_labels: dict[str, str] = {}          # "pid:[tier] model" -> model id
    model_options: dict[str, list[str]] = {}   # provider id -> visible option labels
    model_filter: dict[str, str] = {}          # provider id -> all/free/paid
    model_selected: dict[str, str] = {}        # provider id -> selected option label
    model_status: dict[str, str] = {}          # provider id -> short catalog summary
    manual_model: dict[str, str] = {}          # provider id -> "1" when manual entry

    # ── Data loading ──────────────────────────────────────────────────────────
    async def load(self) -> None:
        self.draft = {}
        self.flash = ""
        self.model_filter = {spec["id"]: "all" for spec in PROVIDER_CATALOG}
        self.manual_model = {spec["id"]: "" for spec in PROVIDER_CATALOG}
        self.model_options = {spec["id"]: [MANUAL_LABEL] for spec in PROVIDER_CATALOG}
        self.model_selected = {spec["id"]: "" for spec in PROVIDER_CATALOG}
        self.refresh()
        await self.fetch_all_models()

    def refresh(self) -> None:
        results = {k: v for k, v in self.status.items() if k.endswith(":result")}
        status: dict[str, str] = {}
        options = [AUTO_LABEL, *[spec["name"] for spec in PROVIDER_CATALOG]]
        for spec in PROVIDER_CATALOG:
            pid = spec["id"]
            source = credentials.secret_source(pid, spec["env"])
            masked = credentials.mask_secret(
                credentials.resolve_secret(pid, spec["env"])
            )
            model = credentials.resolve_setting(
                pid, "model", spec["model_env"], spec["default_model"]
            )
            base = credentials.resolve_setting(
                pid, "base_url", spec["base_env"], spec["default_base"]
            )
            name = credentials.get_provider(pid).get("display_name", "")
            status[f"{pid}:source"] = source
            status[f"{pid}:hint"] = (
                f"Configured · {masked}" if masked else "Paste API key"
            )
            status[f"{pid}:model"] = model
            status[f"{pid}:base"] = base
            status[f"{pid}:name"] = name
            status[f"{pid}:result"] = results.get(f"{pid}:result", "")

        self.status = status
        self.provider_options = options
        settings = credentials.get_settings()
        pref = settings["preferences"].get("preferred_provider", "") or "auto"
        if pref != "auto" and pref not in {s["id"] for s in PROVIDER_CATALOG}:
            pref = "auto"
        self.preferred = pref
        self.preferred_label = (
            AUTO_LABEL if pref == "auto" else _spec(pref)["name"]
        )
        self.routing_mode = settings["preferences"].get("routing_mode", "free_only")
        self.supabase_configured = all(
            os.environ.get(key)
            for key in ["SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY", "SUPABASE_SECRET_KEY"]
        )
        self.paid_enabled = bool(os.environ.get("PAID_PROVIDERS_ENABLED"))

    # ── Model catalog ─────────────────────────────────────────────────────────
    def _rebuild_model_options(self, provider_id: str) -> None:
        filt = self.model_filter.get(provider_id, "all")
        labels: list[str] = []
        label_map: dict[str, str] = {}
        selected = self.model_selected.get(provider_id, "")

        for mid in self.models_all.get(provider_id, []):
            tier = self.model_tiers.get(f"{provider_id}:{mid}", "unknown")
            if filt != "all" and tier != filt:
                continue
            label = f"[{tier}] {mid}"
            labels.append(label)
            label_map[f"{provider_id}:{label}"] = mid

        # Keep the current choice visible even when a filter would hide it.
        if selected and selected != MANUAL_LABEL and selected not in labels:
            labels.insert(0, selected)
            mid = self.model_labels.get(f"{provider_id}:{selected}", "")
            if mid:
                label_map[f"{provider_id}:{selected}"] = mid

        labels.append(MANUAL_LABEL)
        label_map[f"{provider_id}:{MANUAL_LABEL}"] = ""

        self.model_options = {**self.model_options, provider_id: labels}
        self.model_labels = {**self.model_labels, **label_map}
        if selected and selected not in labels:
            self.model_selected = {**self.model_selected, provider_id: ""}

    def _apply_catalog(self, provider_id: str, catalog, spec: dict) -> None:
        tiers: dict[str, str] = {}
        labels: dict[str, str] = {}
        for model in catalog.models:
            tiers[f"{provider_id}:{model.id}"] = model.tier
            labels[f"{provider_id}:[{model.tier}] {model.id}"] = model.id

        self.models_all = {**self.models_all, provider_id: [m.id for m in catalog.models]}
        self.model_tiers = {**self.model_tiers, **tiers}
        self.model_labels = {**self.model_labels, **labels}

        current = credentials.resolve_setting(
            provider_id,
            "model",
            spec.get("model_env", ""),
            spec.get("default_model", ""),
        )
        selected = next(
            (f"[{m.tier}] {m.id}" for m in catalog.models if m.id == current), ""
        )
        self.model_selected = {**self.model_selected, provider_id: selected}
        self.manual_model = {
            **self.manual_model,
            provider_id: "1" if not selected else "",
        }
        self._rebuild_model_options(provider_id)

        free = sum(1 for m in catalog.models if m.tier == "free")
        paid = sum(1 for m in catalog.models if m.tier == "paid")
        source = "live" if catalog.source == "live" else "built-in list"
        self.model_status = {
            **self.model_status,
            provider_id: f"{len(catalog.models)} models · {free} free / {paid} paid · {source}",
        }

    async def _fetch_one(self, spec: dict):
        from api.routes import _effective, spec_for
        from providers.model_catalog import fetch_models

        provider_id = spec["id"]
        effective = _effective(provider_id, spec_for(provider_id))
        catalog = await fetch_models(
            provider_id,
            base_url=effective["base_url"],
            api_key=effective["api_key"],
            provider_tier=spec["tier"],
        )
        return provider_id, catalog

    async def fetch_all_models(self) -> None:
        results = await asyncio.gather(
            *[self._fetch_one(spec) for spec in PROVIDER_CATALOG],
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                continue
            provider_id, catalog = result
            self._apply_catalog(provider_id, catalog, _spec(provider_id))

    async def fetch_provider_models(self, provider_id: str) -> None:
        spec = _spec(provider_id)
        self.model_status = {**self.model_status, provider_id: "Fetching models…"}
        try:
            _, catalog = await self._fetch_one(spec)
        except Exception as exc:  # pragma: no cover - network failures
            self.model_status = {
                **self.model_status,
                provider_id: f"Fetch failed: {type(exc).__name__}",
            }
            return
        self._apply_catalog(provider_id, catalog, spec)
        self.flash_level = "info"
        self.flash = f"{spec['name']} model list refreshed."

    def set_model_filter(self, provider_id: str, value: str) -> None:
        self.model_filter = {**self.model_filter, provider_id: value}
        self._rebuild_model_options(provider_id)

    def select_model(self, provider_id: str, label: str) -> None:
        self.model_selected = {**self.model_selected, provider_id: label}
        manual = label == MANUAL_LABEL
        self.manual_model = {**self.manual_model, provider_id: "1" if manual else ""}
        if not manual:
            mid = self.model_labels.get(f"{provider_id}:{label}", "")
            if mid:
                self.stage(provider_id, "model", mid)

    # ── Draft editing ─────────────────────────────────────────────────────────
    def stage(self, provider_id: str, field: str, value: str) -> None:
        self.draft = {**self.draft, f"{provider_id}:{field}": value}

    def _clear_draft(self, provider_id: str) -> None:
        self.draft = {
            key: value
            for key, value in self.draft.items()
            if not key.startswith(f"{provider_id}:")
        }

    def _set_result(self, provider_id: str, message: str) -> None:
        self.status = {**self.status, f"{provider_id}:result": message}

    # ── Actions ───────────────────────────────────────────────────────────────
    def save_provider(self, provider_id: str) -> None:
        spec = _spec(provider_id)
        key = self.draft.get(f"{provider_id}:key", "")
        model = self.draft.get(f"{provider_id}:model")
        base = self.draft.get(f"{provider_id}:base")
        name = self.draft.get(f"{provider_id}:name")
        changed = bool(key.strip()) or model is not None or base is not None

        if provider_id == "custom":
            effective_base = base if base is not None else self.status.get("custom:base", "")
            effective_model = (
                model if model is not None else self.status.get("custom:model", "")
            )
            if not (effective_base or "").strip() or not (effective_model or "").strip():
                self.flash_level = "error"
                self.flash = "Custom endpoint needs both a base URL and a model id."
                return

        credentials.update_provider(
            provider_id,
            api_key=key or None,
            model=model,
            base_url=base,
            display_name=name,
        )
        self._clear_draft(provider_id)
        self.refresh()
        if model:
            matched = next(
                (
                    f"[{tier}] {model}"
                    for mid, tier in (
                        (m, self.model_tiers.get(f"{provider_id}:{m}", "unknown"))
                        for m in self.models_all.get(provider_id, [])
                    )
                    if mid == model
                ),
                "",
            )
            self.model_selected = {
                **self.model_selected,
                provider_id: matched or MANUAL_LABEL,
            }
            self.manual_model = {
                **self.manual_model,
                provider_id: "" if matched else "1",
            }
        if changed:
            self.flash_level = "success"
            self.flash = f"{spec['name']} settings saved."
        else:
            self.flash_level = "info"
            self.flash = "Nothing to save yet — paste an API key or edit a field."

    def clear_provider(self, provider_id: str) -> None:
        spec = _spec(provider_id)
        credentials.remove_provider(provider_id)
        self._clear_draft(provider_id)
        self.refresh()
        model = credentials.resolve_setting(
            provider_id,
            "model",
            spec["model_env"],
            spec["default_model"],
        )
        matched = next(
            (f"[{tier}] {model}" for mid, tier in (
                (m, self.model_tiers.get(f"{provider_id}:{m}", "unknown"))
                for m in self.models_all.get(provider_id, [])
            ) if mid == model),
            "",
        )
        self.model_selected = {**self.model_selected, provider_id: matched}
        self.manual_model = {**self.manual_model, provider_id: "" if matched else "1"}
        self.flash_level = "info"
        self.flash = f"{spec['name']} credentials removed."

    async def test_provider(self, provider_id: str) -> None:
        spec = _spec(provider_id)
        # Imported lazily to avoid a page-load dependency on the API layer.
        from api.routes import _FACTORIES, refresh_registry

        registry, _router = refresh_registry()
        cfg = registry.get(provider_id)
        if cfg is None or not cfg.enabled:
            self._set_result(provider_id, "Not configured — save a key first.")
            return
        factory = _FACTORIES.get(provider_id)
        if factory is None:
            self._set_result(provider_id, "No adapter registered.")
            return
        self._set_result(provider_id, "Testing…")
        try:
            health = await factory(config=cfg).health_check()
        except Exception as exc:  # pragma: no cover - network failures
            self._set_result(provider_id, f"Failed: {type(exc).__name__}")
            return
        if health.healthy:
            self._set_result(provider_id, "Reachable ✓")
            self.flash_level = "success"
            self.flash = f"{spec['name']} responded successfully."
        else:
            detail = health.message or str(health.status_code or "unknown error")
            self._set_result(provider_id, f"Failed: {detail}")
            self.flash_level = "error"
            self.flash = f"{spec['name']} test failed: {detail}"

    def set_preferred(self, value: str) -> None:
        if value == AUTO_LABEL:
            credentials.set_preferences(preferred_provider="")
            self.preferred = "auto"
            self.preferred_label = AUTO_LABEL
            self.flash_level = "info"
            self.flash = "Routing: automatic priority order with fallback."
            return

        provider_id = next(
            (spec["id"] for spec in PROVIDER_CATALOG if spec["name"] == value), ""
        )
        credentials.set_preferences(preferred_provider=provider_id)
        self.preferred = provider_id or "auto"
        self.preferred_label = value if provider_id else AUTO_LABEL
        self.flash_level = "info"
        configured = (
            credentials.secret_source(provider_id, _spec(provider_id)["env"]) != "none"
            if provider_id
            else False
        )
        self.flash = f"{value} will be tried first."
        if not configured:
            self.flash += " Add its key below to activate it."

    def set_routing_mode(self, mode: str) -> None:
        credentials.set_preferences(routing_mode=mode)
        self.routing_mode = mode


def _source_badge(provider_id: str) -> rx.Component:
    source = SettingsState.status[f"{provider_id}:source"]
    return rx.badge(
        rx.cond(
            source == "saved",
            "Saved key",
            rx.cond(source == "env", "From .env", "No key"),
        ),
        color_scheme=rx.cond(
            source == "saved",
            "green",
            rx.cond(source == "env", "blue", "gray"),
        ),
        variant="soft",
        size="1",
    )


def _field(
    provider_id: str,
    field: str,
    placeholder,
    *,
    password: bool = False,
    flex_basis: str = "220px",
) -> rx.Component:
    return rx.input(
        type="password" if password else "text",
        auto_complete="new-password" if password else "off",
        placeholder=placeholder,
        value=SettingsState.draft[f"{provider_id}:{field}"],
        on_change=lambda value: SettingsState.stage(provider_id, field, value),
        debounce_timeout=150,
        force_notify_on_blur=True,
        size="2",
        variant="surface",
        style={"flex": f"1 1 {flex_basis}", "minWidth": "180px"},
    )


def _filter_button(provider_id: str, value: str, label: str) -> rx.Component:
    return rx.button(
        label,
        size="1",
        on_click=lambda: SettingsState.set_model_filter(provider_id, value),
        variant=rx.cond(
            SettingsState.model_filter[provider_id] == value, "solid", "outline"
        ),
        color_scheme="gray",
        style={
            "height": "26px",
            "minWidth": "42px",
            "fontSize": "0.72rem",
            "background": rx.cond(
                SettingsState.model_filter[provider_id] == value,
                TEAL_SOLID,
                BG_CARD,
            ),
            "color": rx.cond(
                SettingsState.model_filter[provider_id] == value,
                "#FFFFFF",
                TEXT_PRIMARY,
            ),
        },
    )


def _model_picker(provider_id: str) -> rx.Component:
    """A filterable model dropdown populated from the provider's live API."""
    return rx.vstack(
        rx.hstack(
            rx.text(
                "MODEL",
                font_size="0.7rem",
                font_weight="700",
                color=TEXT_MUTED,
                letter_spacing="0.5px",
                text_transform="uppercase",
            ),
            rx.hstack(
                *[_filter_button(provider_id, value, label) for value, label in FILTERS],
                gap="4px",
                align="center",
            ),
            rx.spacer(),
            rx.button(
                "↻ Fetch models",
                size="1",
                variant="ghost",
                color_scheme="gray",
                title="Fetch the latest model list from this provider",
                on_click=lambda: SettingsState.fetch_provider_models(provider_id),
                style={"height": "26px", "fontSize": "0.72rem"},
            ),
            width="100%",
            align="center",
            gap="8px",
            wrap="wrap",
        ),
        rx.select(
            SettingsState.model_options[provider_id],
            value=SettingsState.model_selected[provider_id],
            on_change=lambda value: SettingsState.select_model(provider_id, value),
            placeholder="Select a model…",
            size="2",
            width="100%",
        ),
        rx.cond(
            SettingsState.manual_model[provider_id] == "1",
            _field(
                provider_id,
                "model",
                rx.cond(
                    SettingsState.status[f"{provider_id}:model"] != "",
                    SettingsState.status[f"{provider_id}:model"],
                    "Type a model id manually",
                ),
                flex_basis="100%",
            ),
            rx.fragment(),
        ),
        rx.cond(
            SettingsState.model_status[provider_id] != "",
            rx.text(
                SettingsState.model_status[provider_id],
                font_size="0.7rem",
                color=TEXT_MUTED,
            ),
            rx.fragment(),
        ),
        width="100%",
        spacing="1",
        align="start",
    )


def _provider_card(spec: dict) -> rx.Component:
    pid = spec["id"]
    fields: list[rx.Component] = [
        _field(pid, "key", SettingsState.status[f"{pid}:hint"], password=True),
    ]
    if spec.get("show_base"):
        fields.append(
            _field(
                pid,
                "base",
                rx.cond(
                    SettingsState.status[f"{pid}:base"] != "",
                    SettingsState.status[f"{pid}:base"],
                    "https://your-endpoint/v1",
                ),
                flex_basis="260px",
            )
        )
    if spec.get("show_name"):
        fields.append(
            _field(
                pid,
                "name",
                rx.cond(
                    SettingsState.status[f"{pid}:name"] != "",
                    SettingsState.status[f"{pid}:name"],
                    "Endpoint name (optional)",
                ),
                flex_basis="200px",
            )
        )

    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.text(
                        spec["name"],
                        font_size="0.95rem",
                        font_weight="700",
                        color=TEXT_PRIMARY,
                    ),
                    rx.text(
                        spec["tagline"],
                        font_size="0.74rem",
                        color=TEXT_MUTED,
                    ),
                    spacing="1",
                    align="start",
                ),
                rx.spacer(),
                rx.hstack(
                    _source_badge(pid),
                    rx.cond(
                        spec["tier"] == "paid",
                        rx.badge("paid", color_scheme="amber", variant="soft", size="1"),
                        rx.fragment(),
                    ),
                    gap="6px",
                    align="center",
                ),
                width="100%",
                align="start",
                gap="8px",
                wrap="wrap",
            ),
            _model_picker(pid),
            rx.flex(*fields, wrap="wrap", gap="8px", width="100%"),
            rx.flex(
                rx.button(
                    "Save",
                    size="1",
                    on_click=lambda: SettingsState.save_provider(pid),
                    style={
                        "background": TEAL_SOLID,
                        "color": "#FFFFFF",
                        "height": "32px",
                        "_hover": {"background": TEAL_HOVER},
                    },
                ),
                rx.button(
                    "Test",
                    size="1",
                    variant="soft",
                    color_scheme="gray",
                    on_click=lambda: SettingsState.test_provider(pid),
                    style={"height": "32px"},
                ),
                rx.button(
                    "Clear",
                    size="1",
                    variant="ghost",
                    color_scheme="red",
                    on_click=lambda: SettingsState.clear_provider(pid),
                    style={"height": "32px"},
                ),
                rx.spacer(),
                rx.cond(
                    SettingsState.status[f"{pid}:result"] != "",
                    rx.text(
                        SettingsState.status[f"{pid}:result"],
                        font_size="0.74rem",
                        color=TEXT_MUTED,
                    ),
                    rx.fragment(),
                ),
                width="100%",
                align="center",
                wrap="wrap",
                gap="8px",
            ),
            width="100%",
            align="start",
            spacing="3",
        ),
        background=BG_CARD,
        border=f"1px solid {BORDER}",
        border_radius="12px",
        padding="16px",
        box_shadow="0 2px 10px rgba(27,94,59,0.05)",
        min_width="0",
    )


def _section_title(title: str, subtitle: str) -> rx.Component:
    return rx.vstack(
        rx.text(title, font_size="1.05rem", font_weight="700", color=TEXT_PRIMARY),
        rx.text(subtitle, font_size="0.82rem", color=TEXT_MUTED),
        spacing="1",
        align="start",
        width="100%",
    )


def settings_page() -> rx.Component:
    state = SettingsState
    return rx.box(
        app_header("settings"),
        rx.box(
            rx.vstack(
                rx.vstack(
                    rx.text(
                        "Settings",
                        font_size="1.5rem",
                        font_weight="bold",
                        color=TEXT_PRIMARY,
                    ),
                    rx.text(
                        "Bring your own API keys. Saved keys are used before "
                        "environment variables and never leave the server.",
                        font_size="0.84rem",
                        color=TEXT_MUTED,
                    ),
                    spacing="1",
                    align="start",
                ),
                rx.cond(
                    state.flash != "",
                    rx.callout.root(
                        rx.callout.icon(),
                        rx.callout.text(state.flash),
                        color_scheme=rx.cond(
                            state.flash_level == "success",
                            "green",
                            rx.cond(state.flash_level == "error", "red", "blue"),
                        ),
                        size="1",
                        width="100%",
                    ),
                    rx.fragment(),
                ),
                _section_title(
                    "Provider API keys",
                    "Fetch every free and paid model from each provider, pick the one you "
                    "want, and add a key. If a provider runs out of quota, Phrasia falls back "
                    "to the next configured provider.",
                ),
                rx.grid(
                    *[_provider_card(spec) for spec in PROVIDER_CATALOG],
                    columns=rx.breakpoints(initial="1", md="2"),
                    gap="14px",
                    width="100%",
                    align_items="stretch",
                ),
                _section_title(
                    "Routing & fallback",
                    "Choose which provider is attempted first and whether paid "
                    "providers may be used.",
                ),
                rx.box(
                    rx.vstack(
                        rx.text(
                            "Preferred provider",
                            font_size="0.78rem",
                            font_weight="700",
                            color=TEXT_MUTED,
                            text_transform="uppercase",
                            letter_spacing="0.6px",
                        ),
                        rx.select(
                            state.provider_options,
                            value=state.preferred_label,
                            on_change=state.set_preferred,
                            size="2",
                            width="100%",
                            max_width="420px",
                        ),
                        rx.text(
                            "Routing mode",
                            font_size="0.78rem",
                            font_weight="700",
                            color=TEXT_MUTED,
                            text_transform="uppercase",
                            letter_spacing="0.6px",
                            margin_top="4px",
                        ),
                        rx.hstack(
                            rx.button(
                                "Free only",
                                size="1",
                                on_click=lambda: state.set_routing_mode("free_only"),
                                variant=rx.cond(
                                    state.routing_mode == "free_only", "solid", "outline"
                                ),
                                color_scheme="gray",
                                style={
                                    "height": "32px",
                                    "background": rx.cond(
                                        state.routing_mode == "free_only",
                                        TEAL_SOLID,
                                        BG_CARD,
                                    ),
                                    "color": rx.cond(
                                        state.routing_mode == "free_only",
                                        "#FFFFFF",
                                        TEXT_PRIMARY,
                                    ),
                                },
                            ),
                            rx.button(
                                "Hybrid",
                                size="1",
                                on_click=lambda: state.set_routing_mode("hybrid"),
                                variant=rx.cond(
                                    state.routing_mode == "hybrid", "solid", "outline"
                                ),
                                color_scheme="gray",
                                style={
                                    "height": "32px",
                                    "background": rx.cond(
                                        state.routing_mode == "hybrid",
                                        TEAL_SOLID,
                                        BG_CARD,
                                    ),
                                    "color": rx.cond(
                                        state.routing_mode == "hybrid",
                                        "#FFFFFF",
                                        TEXT_PRIMARY,
                                    ),
                                },
                            ),
                            gap="8px",
                            align="center",
                        ),
                        width="100%",
                        align="start",
                        spacing="2",
                    ),
                    background=BG_CARD,
                    border=f"1px solid {BORDER}",
                    border_radius="12px",
                    padding="16px",
                ),
                _section_title(
                    "Account & storage",
                    "Connection status and how your keys are kept safe.",
                ),
                rx.grid(
                    rx.box(
                        rx.vstack(
                            rx.text(
                                "Supabase",
                                font_size="0.95rem",
                                font_weight="700",
                                color=TEXT_PRIMARY,
                            ),
                            rx.badge(
                                rx.cond(
                                    state.supabase_configured,
                                    "connected",
                                    "not configured",
                                ),
                                size="1",
                                color_scheme=rx.cond(
                                    state.supabase_configured, "green", "red"
                                ),
                                variant="soft",
                            ),
                            width="100%",
                            align="start",
                            spacing="2",
                        ),
                        background=BG_CARD,
                        border=f"1px solid {BORDER}",
                        border_radius="12px",
                        padding="16px",
                    ),
                    rx.box(
                        rx.vstack(
                            rx.text(
                                "API key storage",
                                font_size="0.95rem",
                                font_weight="700",
                                color=TEXT_PRIMARY,
                            ),
                            rx.text(
                                "Keys are written to .local/provider_settings.json on the "
                                "server (git-ignored, 0600). The browser only sees a masked "
                                "preview. For multi-user deployments, move this to a "
                                "per-user encrypted store.",
                                font_size="0.8rem",
                                color=TEXT_MUTED,
                            ),
                            width="100%",
                            align="start",
                            spacing="2",
                        ),
                        background=BG_CARD,
                        border=f"1px solid {BORDER}",
                        border_radius="12px",
                        padding="16px",
                    ),
                    columns=rx.breakpoints(initial="1", md="2"),
                    gap="14px",
                    width="100%",
                ),
                rx.callout.root(
                    rx.callout.icon(),
                    rx.callout.text(
                        rx.cond(
                            state.paid_enabled,
                            "Paid providers are enabled. OpenAI and Anthropic still respect "
                            "the monthly budget and per-job authorization gate.",
                            "OpenAI and Anthropic are paid providers and stay disabled until "
                            "PAID_PROVIDERS_ENABLED=true and a monthly budget are configured. "
                            "Gemini, Groq, OpenRouter and custom endpoints work immediately "
                            "with your own key.",
                        )
                    ),
                    color_scheme=rx.cond(state.paid_enabled, "green", "yellow"),
                    size="1",
                    width="100%",
                ),
                width="100%",
                max_width="1400px",
                margin_x="auto",
                padding="24px",
                spacing="4",
                align="start",
            ),
            width="100%",
        ),
        width="100%",
        min_height="100vh",
        background=BG_PAGE,
        font_family="Inter, ui-sans-serif, system-ui, sans-serif",
        on_mount=SettingsState.load,
    )
