"""Phrasia main Reflex app definition."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Resolve paths relative to project root
here = Path(__file__).parent

# Load .env so local dev has SUPABASE_* and provider keys in the environment.
load_dotenv(here / ".env")

# Import pages
import reflex as rx  # noqa: E402
from reflex_base.registry import RegistrationContext  # noqa: E402

from app.pages.history import history_page  # noqa: E402
from app.pages.settings import settings_page  # noqa: E402
from app.pages.workspace import home_page, workspace_page  # noqa: E402

# ── Guard against re-entrant import ────────────────────────────────────────────
# App.__post_init__ calls reload_config() → _get_config() → re-imports this
# module. On re-import the RegistrationContext already holds an App, so reuse
# it instead of creating a second one (which would raise ReflexRuntimeError).
try:
    _ctx = RegistrationContext.get()
    app = _ctx._app
except LookupError:
    _ctx = None
    app = None

if app is None:
    app = rx.App(
        theme=rx.theme(
            accentColor="emerald",
            grayColor="gray",
            radius="large",
            scaling="90%",
        ),
    )

# ── Pages (registered once) ───────────────────────────────────────────────────
if not getattr(app, "_phrasia_pages_registered", False):
    app.add_page(
        home_page,
        route="/",
        title="Phrasia — Words, Refined.",
        description="An intelligent workspace for better writing.",
    )
    app.add_page(workspace_page, route="/workspace", title="Workspace — Phrasia")
    app.add_page(history_page, route="/history", title="History — Phrasia")
    app.add_page(settings_page, route="/settings", title="Settings — Phrasia")
    app._phrasia_pages_registered = True

# ── Config ────────────────────────────────────────────────────────────────────
config = rx.Config(
    app_name="phrasia",
    app_module_import="rxconfig",
    site_name="Phrasia",
    description="An intelligent workspace for better writing.",
    background_color="#E8EDE6",
    dark_background_color="#E8EDE6",
    primary_color="#10b981",
    # The Workspace UI is designed light-only; forcing light mode keeps Radix
    # text, placeholders and disabled controls readable on light panels.
    default_color_mode="light",
    mode="bun" if os.environ.get("REFLEX_MODE") == "bun" else "prod",
)

# ── Environment hint ───────────────────────────────────────────────────────────
if not all(os.environ.get(k) for k in ["SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY"]):
    print("\n⚠️  SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY are not set.")
    print("   Local dev will work but persistence features require a Supabase project.\n")
