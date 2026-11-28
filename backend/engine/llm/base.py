"""Provider contract shared by every hosted backend."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class LLMError(RuntimeError):
    """A provider call failed. Messages never include request headers or keys."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        retryable: bool = False,
        provider: str = "",
    ) -> None:
        super().__init__(message)
        self.status = status
        self.retryable = retryable
        self.provider = provider


@dataclass
class Completion:
    text: str
    provider: str
    model: str
    cached: bool = False


@dataclass
class LLMUnavailable(RuntimeError):
    errors: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__init__(self.summary())

    def summary(self) -> str:
        if not self.errors:
            return "No hosted provider is configured."
        parts = []
        for error in self.errors:
            name = error.get("provider") or "provider"
            detail = error.get("error") or "failed"
            parts.append(f"{name}: {detail}")
        return "Every hosted provider failed. " + " | ".join(parts)


class LLMProvider(ABC):
    name: str
    model: str

    @abstractmethod
    def rewrite(
        self,
        system: str,
        user: str,
        params: dict[str, Any] | None = None,
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: float = 60,
        **_: Any,
    ) -> str:
        """Return the assistant text for one system/user turn.

        ``params`` is an optional provider-specific extras dict; the common
        keyword arguments ``temperature``, ``max_tokens`` and ``timeout`` are
        accepted too.
        """
