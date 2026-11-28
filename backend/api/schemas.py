"""Request models for the JSON API."""
from __future__ import annotations

from pydantic import BaseModel, Field

from backend.config import MAX_INPUT_CHARS


class HumanizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_INPUT_CHARS)
    tone: str = Field(default="casual", max_length=40)
    strength: str = Field(default="medium", max_length=20)
    intensity: str | None = Field(default=None, max_length=20)
    provider: str = Field(default="auto", max_length=40)
    mode: str = Field(default="auto", max_length=20)
    variation: int = Field(default=0, ge=0, le=1000000)
    clean_invisible: bool = True
    replace_dashes: bool = True
    straight_quotes: bool = True
    offline_fallback: bool = True


class SentenceRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    tone: str = Field(default="casual", max_length=40)
    strength: str = Field(default="medium", max_length=20)
    provider: str = Field(default="auto", max_length=40)
    replace_dashes: bool = True
    straight_quotes: bool = True


class FeedbackRequest(BaseModel):
    action: str = Field(pattern="^(accepted|rejected|edited)$")
    version_id: int | None = Field(default=None, ge=1)
    sentence_idx: int | None = Field(default=None, ge=0)
    operation: str = Field(default="keep", max_length=40)
    source_text: str = Field(default="", max_length=4000)
    final_text: str = Field(default="", max_length=8000)
    tone: str = Field(default="casual", max_length=40)
    strength: str = Field(default="medium", max_length=20)


class KeyRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=40)
    api_key: str = Field(min_length=1, max_length=500)


class ProviderRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=40)
    api_key: str | None = Field(default=None, max_length=500)


class SettingsUpdate(BaseModel):
    enabled: bool | None = None
    provider_order: list[str] | None = None
    models: dict[str, str] | None = None
    preferred_provider: str | None = Field(default=None, max_length=40)
    offline_fallback: bool | None = None
    temperature: float | None = Field(default=None, ge=0, le=1.5)
    max_tokens: int | None = Field(default=None, ge=256, le=8192)
    timeout_seconds: int | None = Field(default=None, ge=5, le=180)
    target_density: float | None = Field(default=None, ge=0, le=10)


class TextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_INPUT_CHARS)


class ExportRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_INPUT_CHARS)
    title: str | None = Field(default=None, max_length=200)


class ReferenceRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    text: str = Field(min_length=1, max_length=MAX_INPUT_CHARS)
