"""Output validation for generated chunks."""
from __future__ import annotations

from typing import Optional

from phrasia_domain import ChunkPlan
from providers.base import GenerationResult


class OutputValidator:
    """Validates generated chunk output for completeness and placeholder integrity."""

    MIN_OUTPUT_LENGTH = 10
    MAX_COSMETIC_EXPANSION_RATIO = 5.0

    def validate(self, chunk: ChunkPlan, result: GenerationResult) -> tuple[bool, list[str]]:
        warnings: list[str] = []
        if not result.output_text:
            return False, ["Empty output from provider"]
        if len(result.output_text) < self.MIN_OUTPUT_LENGTH:
            warnings.append("Very short output — may be incomplete")
        length_ratio = (
            len(result.output_text) / len(chunk.source_text)
            if chunk.source_text
            else 1.0
        )
        if length_ratio > self.MAX_COSMETIC_EXPANSION_RATIO and length_ratio > 1.5:
            warnings.append("Output is unusually longer than input — check for repetition")
        if result.finish_reason == "length" or result.finish_reason == "max_tokens":
            warnings.append("Output was truncated by provider token limit")
        for span in chunk.protected_spans:
            if span.placeholder and span.placeholder not in result.output_text and span.original_text not in result.output_text:
                warnings.append(f"Protected span '{span.span_type}' missing from output")
        return True, warnings