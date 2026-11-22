"""Provider registry and routing policies."""
from __future__ import annotations

from typing import Optional

from phrasia_domain import ProviderTask, ProviderTier, RoutingMode
from providers.base import ProviderConfig, ProviderRegistry


class ProviderRouter:
    """Routes generation requests to eligible providers with paid-safety gating."""

    def __init__(self, registry: ProviderRegistry):
        self.registry = registry

    def eligible_generation_providers(
        self, *, routing_mode: RoutingMode, allow_paid: bool
    ) -> list[ProviderConfig]:
        free = self.registry.eligible_for_generation(allow_paid=False)
        if routing_mode == RoutingMode.FREE_ONLY:
            return free
        if routing_mode == RoutingMode.HYBRID:
            if not allow_paid:
                return free
            paid = [
                p
                for p in self.registry.eligible_for_generation(allow_paid=True)
                if p.tier == ProviderTier.PAID
            ]
            return free + paid
        return free

    def select_provider(
        self,
        *,
        routing_mode: RoutingMode,
        allow_paid: bool,
        preferred_provider_id: Optional[str] = None,
    ) -> Optional[ProviderConfig]:
        if preferred_provider_id:
            cfg = self.registry.get(preferred_provider_id)
            if (
                cfg
                and cfg.is_eligible(allow_paid=allow_paid)
                and cfg.task_type == ProviderTask.GENERATION
            ):
                return cfg
        eligible = self.eligible_generation_providers(
            routing_mode=routing_mode, allow_paid=allow_paid
        )
        return eligible[0] if eligible else None

    def ordered_generation_providers(
        self,
        *,
        routing_mode: RoutingMode,
        allow_paid: bool,
        preferred_provider_id: Optional[str] = None,
        fallback_provider_ids: Optional[list[str]] = None,
    ) -> list[ProviderConfig]:
        """Eligible providers in attempt order: preferred → fallbacks → priority.

        Used for automatic failover so a provider whose quota is exhausted does
        not take the whole job down when another configured provider can finish.
        """
        eligible = self.eligible_generation_providers(
            routing_mode=routing_mode, allow_paid=allow_paid
        )
        remaining = {p.provider_id: p for p in eligible}
        ordered: list[ProviderConfig] = []
        if preferred_provider_id and preferred_provider_id in remaining:
            ordered.append(remaining.pop(preferred_provider_id))
        for provider_id in fallback_provider_ids or []:
            if provider_id in remaining:
                ordered.append(remaining.pop(provider_id))
        ordered.extend(sorted(remaining.values(), key=lambda p: p.priority))
        return ordered



def check_paid_authorization(
    provider: ProviderConfig,
    *,
    paid_enabled: bool,
    monthly_budget_usd: float,
    monthly_spend_usd: float,
    require_per_job_confirmation: bool,
    job_authorized: bool,
) -> tuple[bool, Optional[str]]:
    """Server-side paid safety gate. Returns (allowed, reason)."""
    if provider.tier != ProviderTier.PAID:
        return True, None
    if not paid_enabled:
        return False, "Paid providers are disabled"
    if not job_authorized and require_per_job_confirmation:
        return False, "Per-job paid authorization required"
    if monthly_budget_usd <= 0:
        return False, "Monthly paid budget is USD 0"
    if monthly_spend_usd >= monthly_budget_usd:
        return False, "Monthly paid budget exhausted"
    return True, None
