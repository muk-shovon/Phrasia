"""Supabase client wrapper — server-side only."""
from __future__ import annotations

import os
from typing import Optional


def get_supabase_url() -> str:
    return os.environ["SUPABASE_URL"]


def get_supabase_publishable_key() -> str:
    return os.environ["SUPABASE_PUBLISHABLE_KEY"]


def get_supabase_secret_key() -> str:
    return os.environ["SUPABASE_SECRET_KEY"]


def verify_supabase_configured() -> bool:
    required = ["SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY", "SUPABASE_SECRET_KEY"]
    return all(os.environ.get(k) for k in required)