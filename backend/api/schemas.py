"""Request/response models for the JSON API."""
from __future__ import annotations

from pydantic import BaseModel, Field

from backend.config import MAX_INPUT_CHARS


class HumanizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_INPUT_CHARS)
    title: str | None = Field(default=None, max_length=200)
    mode: str = Field(default="balanced", max_length=40)
    intensity: str = Field(default="medium", max_length=20)
    preserve_formatting: bool = True
    keep_quotes: bool = True
    deep_humanize: bool = False
    remove_em_dashes: bool = False
    clean_invisible: bool = True
    provider_id: str | None = Field(default=None, max_length=60)


class TextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_INPUT_CHARS)


class ReferenceRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    text: str = Field(min_length=1, max_length=MAX_INPUT_CHARS)


class ProviderUpdate(BaseModel):
    api_key: str | None = Field(default=None, max_length=500)
    model: str | None = Field(default=None, max_length=200)
    base_url: str | None = Field(default=None, max_length=500)
    enabled: bool | None = None


class PreferencesUpdate(BaseModel):
    preferred_provider: str | None = Field(default=None, max_length=60)


class DiffRequest(BaseModel):
    original: str = Field(min_length=1, max_length=MAX_INPUT_CHARS)
    rewritten: str = Field(default="", max_length=MAX_INPUT_CHARS)
