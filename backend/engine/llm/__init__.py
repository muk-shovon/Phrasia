"""Hosted language-model layer: providers, prompts, retrieval, passes."""
from __future__ import annotations

from backend.engine.llm.base import Completion, LLMError, LLMProvider, LLMUnavailable
from backend.engine.llm.chain import LLMChain, build_chain, build_provider
from backend.engine.llm.rewrite import (
    density,
    passes_for,
    rewrite_document,
    rewrite_single,
)

__all__ = [
    "Completion",
    "LLMChain",
    "LLMError",
    "LLMProvider",
    "LLMUnavailable",
    "build_chain",
    "build_provider",
    "density",
    "passes_for",
    "rewrite_document",
    "rewrite_single",
]
