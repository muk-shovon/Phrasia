"""Request models for the JSON API."""
from __future__ import annotations

from pydantic import BaseModel, Field

from backend.config import MAX_INPUT_CHARS


class HumanizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_INPUT_CHARS)
    tone: str = Field(default="casual", max_length=40)
    strength: str = Field(default="medium", max_length=20)
    variation: int = Field(default=0, ge=0, le=1000000)
    clean_invisible: bool = True


class TextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_INPUT_CHARS)


class ExportRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_INPUT_CHARS)
    title: str | None = Field(default=None, max_length=200)


class ReferenceRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    text: str = Field(min_length=1, max_length=MAX_INPUT_CHARS)
