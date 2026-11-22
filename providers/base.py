"""Vendor-neutral provider interfaces and registry."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol

from phrasia_domain import ProviderTask, ProviderTier
from providers.errors import ProviderError


@dataclass
class ProviderConfig:
    provider_id: str
    display_name: str
    task_type: ProviderTask
    tier: ProviderTier = ProviderTier.UNKNOWN
    enabled: bool = False
    priority: int = 50
    default_model: Optional[str] = None
    secret_reference: Optional[str] = None
    base_url: Optional[str] = None
    configuration: dict = field(default_factory=dict)
    last_health_status: Optional[str] = None

    def is_eligible(self, *, allow_paid: bool) -> bool:
        if not self.enabled:
            return False
        if not allow_paid and self.tier == ProviderTier.PAID:
            return False
        return True


class GenerationProvider(Protocol):
    provider_id: str

    async def generate(self, request: "GenerationRequest") -> "GenerationResult":
        ...

    async def health_check(self) -> "ProviderHealth":
        ...


@dataclass
class GenerationRequest:
    system_instruction: str
    user_instruction: str
    chunk_text: str
    model: str
    max_output_tokens: int
    temperature: float = 0.4
    timeout_seconds: float = 60.0
    job_id: Optional[str] = None
    chunk_id: Optional[str] = None
    context_notes: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class GenerationResult:
    output_text: str
    provider_id: str
    model_id: str
    provider_request_id: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
    finish_reason: Optional[str] = None
    warnings: list = field(default_factory=list)
    raw_response: Optional[dict] = None


@dataclass
class ProviderHealth:
    provider_id: str
    healthy: bool
    status_code: Optional[int] = None
    message: str = ""
    latency_ms: float = 0.0


class ProviderRegistry:
    """In-memory registry of configured providers. Server-side only."""

    def __init__(self):
        self._providers: dict[str, ProviderConfig] = {}

    def register(self, config: ProviderConfig) -> None:
        self._providers[config.provider_id] = config

    def get(self, provider_id: str) -> Optional[ProviderConfig]:
        return self._providers.get(provider_id)

    def list_all(self) -> list[ProviderConfig]:
        return list(self._providers.values())

    def list_by_task(self, task: ProviderTask) -> list[ProviderConfig]:
        return [p for p in self._providers.values() if p.task_type == task]

    def eligible_for_generation(self, *, allow_paid: bool) -> list[ProviderConfig]:
        return sorted(
            (p for p in self.list_by_task(ProviderTask.GENERATION) if p.is_eligible(allow_paid=allow_paid)),
            key=lambda p: p.priority,
        )