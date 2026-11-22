"""Humanizer use-case orchestration."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from core.chunking_service import Chunker
from core.humanizer_postprocess import apply_human_touch
from core.output_validator import OutputValidator
from core.prompt_builder import build_dehumanize_prompt, build_humanizer_prompt
from phrasia_domain import ChunkPlan, HumanizationOptions, JobStatus, RoutingMode
from providers.base import GenerationProvider, GenerationRequest
from providers.errors import ProviderError
from providers.router import ProviderRouter, check_paid_authorization

logger = logging.getLogger(__name__)


@dataclass
class HumanizationJob:
    job_id: str
    document_id: str
    status: JobStatus
    options: HumanizationOptions
    chunks: list[ChunkPlan]
    completed_chunks: dict[str, str]  # chunk_id -> output text
    failed_chunks: list[str]
    current_provider: Optional[str] = None
    current_model: Optional[str] = None
    last_error_code: Optional[str] = None
    last_error_message_safe: Optional[str] = None
    input_text: str = ""
    routing_mode: RoutingMode = RoutingMode.FREE_ONLY
    allow_paid: bool = False


class HumanizerService:
    def __init__(
        self,
        router: ProviderRouter,
        provider_factories: dict[str, type[GenerationProvider]],
        chunker_max_input_tokens: int = 4000,
    ):
        self.router = router
        self.provider_factories = provider_factories
        self.chunker = Chunker(max_input_tokens=chunker_max_input_tokens)
        self.validator = OutputValidator()

    async def create_job(
        self,
        *,
        job_id: str,
        document_id: str,
        input_text: str,
        options: HumanizationOptions,
        routing_mode: RoutingMode = RoutingMode.FREE_ONLY,
        allow_paid: bool = False,
    ) -> tuple[HumanizationJob, list[str]]:
        if not input_text.strip():
            raise ValueError("Input text must not be empty")
        validation_warnings: list[str] = []
        if len(input_text) > 1_000_000:
            validation_warnings.append("Very large input detected; processing may take longer")
        chunks = self.chunker.chunk(input_text)
        if not chunks:
            raise ValueError("No valid content found in input text")
        job = HumanizationJob(
            job_id=job_id,
            document_id=document_id,
            status=JobStatus.QUEUED,
            options=options,
            chunks=chunks,
            completed_chunks={},
            failed_chunks=[],
            input_text=input_text,
            routing_mode=routing_mode,
            allow_paid=allow_paid,
        )
        return job, validation_warnings

    def _candidate_providers(
        self,
        job: HumanizationJob,
        *,
        paid_enabled: bool,
        preferred_provider_id: Optional[str],
        fallback_provider_ids: Optional[list[str]],
        use_fallback: bool,
    ):
        allow_paid = paid_enabled and job.allow_paid
        if use_fallback:
            return self.router.ordered_generation_providers(
                routing_mode=job.routing_mode,
                allow_paid=allow_paid,
                preferred_provider_id=preferred_provider_id,
                fallback_provider_ids=fallback_provider_ids,
            )
        cfg = self.router.select_provider(
            routing_mode=job.routing_mode,
            allow_paid=allow_paid,
            preferred_provider_id=preferred_provider_id,
        )
        return [cfg] if cfg else []

    async def process_next_chunk(
        self,
        job: HumanizationJob,
        *,
        paid_enabled: bool = False,
        monthly_budget_usd: float = 0.0,
        monthly_spend_usd: float = 0.0,
        timeout_seconds: float = 60.0,
        preferred_provider_id: Optional[str] = None,
        fallback_provider_ids: Optional[list[str]] = None,
        use_fallback: bool = False,
    ) -> tuple[bool, bool]:
        """Process one pending chunk. Returns (has_more, success).

        When ``use_fallback`` is set the chunk is retried against the next
        eligible provider if the current one fails (quota, rate limit, auth,
        model unavailable), so one exhausted key does not fail the job.
        """
        candidates = self._candidate_providers(
            job,
            paid_enabled=paid_enabled,
            preferred_provider_id=preferred_provider_id,
            fallback_provider_ids=fallback_provider_ids,
            use_fallback=use_fallback,
        )
        if not candidates:
            job.last_error_code = "NO_ELIGIBLE_PROVIDER"
            job.last_error_message_safe = (
                "No eligible provider configured. Add an API key in Settings."
            )
            job.status = JobStatus.PAUSED_PROVIDER_ERROR
            return False, False

        next_idx = next(
            (i for i, c in enumerate(job.chunks) if c.chunk_id not in job.completed_chunks),
            None,
        )
        if next_idx is None:
            remaining = [c for c in job.chunks if c.chunk_id not in job.completed_chunks]
            if not remaining:
                job.status = JobStatus.COMPLETED
                return False, True
            job.last_error_code = "ALL_CHUNKS_FAILED"
            job.last_error_message_safe = "All chunks have failed after retries."
            job.status = JobStatus.FAILED
            return False, False

        chunk = job.chunks[next_idx]
        system_instr, user_instr = build_humanizer_prompt(
            mode=job.options.mode.value,
            intensity=job.options.intensity.value,
            preserve_meaning=job.options.preserve_meaning,
            preserve_facts=job.options.preserve_facts,
            preserve_citations=job.options.preserve_citations,
            preserve_formatting=job.options.preserve_formatting,
            preserve_quotes=job.options.preserve_quotes,
            custom_instruction=job.options.custom_instruction,
            language_hint=None,
        )

        attempted: list[str] = []
        last_error: Optional[str] = None

        for provider_cfg in candidates:
            if not check_paid_authorization(
                provider_cfg,
                paid_enabled=paid_enabled,
                monthly_budget_usd=monthly_budget_usd,
                monthly_spend_usd=monthly_spend_usd,
                require_per_job_confirmation=True,
                job_authorized=False,
            )[0]:
                job.last_error_code = "PAID_AUTH_REQUIRED"
                job.last_error_message_safe = (
                    f"Paid provider {provider_cfg.provider_id} requires explicit authorization."
                )
                last_error = job.last_error_message_safe
                continue

            adapter_cls = self.provider_factories.get(provider_cfg.provider_id)
            if not adapter_cls:
                job.last_error_code = "ADAPTER_NOT_FOUND"
                job.last_error_message_safe = (
                    f"No adapter registered for {provider_cfg.provider_id}"
                )
                last_error = job.last_error_message_safe
                continue

            attempted.append(provider_cfg.provider_id)
            gen_req = GenerationRequest(
                system_instruction=system_instr,
                user_instruction=user_instr,
                chunk_text=chunk.source_text,
                model=provider_cfg.default_model or "auto",
                max_output_tokens=2000,
                timeout_seconds=timeout_seconds,
                job_id=job.job_id,
                chunk_id=chunk.chunk_id,
            )

            try:
                adapter = adapter_cls(config=provider_cfg)
                result = await asyncio.wait_for(
                    adapter.generate(gen_req), timeout=timeout_seconds + 5
                )
            except asyncio.TimeoutError:
                job.last_error_code = "TIMEOUT"
                job.last_error_message_safe = (
                    f"Chunk {chunk.chunk_id} timed out on {provider_cfg.provider_id}"
                )
                last_error = job.last_error_message_safe
                continue
            except ProviderError as exc:
                if exc.category.name == "RATE_LIMITED":
                    job.last_error_code = "RATE_LIMITED"
                    job.last_error_message_safe = (
                        f"Rate limited by {provider_cfg.provider_id}. Trying next provider."
                    )
                    job.status = JobStatus.PAUSED_RATE_LIMIT
                else:
                    job.last_error_code = exc.category.name
                    job.last_error_message_safe = exc.message[:200]
                last_error = job.last_error_message_safe
                continue
            except Exception as exc:
                job.last_error_code = "UNKNOWN_ERROR"
                job.last_error_message_safe = str(exc)[:200]
                last_error = job.last_error_message_safe
                continue

            valid, warnings = self.validator.validate(chunk, result)
            for w in warnings:
                logger.warning("Chunk %s warning: %s", chunk.chunk_id, w)

            if not valid and len(result.output_text) < self.validator.MIN_OUTPUT_LENGTH * 2:
                job.last_error_code = "INVALID_OUTPUT"
                job.last_error_message_safe = "Chunk output invalid — too short or malformed"
                last_error = job.last_error_message_safe
                continue

            output_text = apply_human_touch(
                result.output_text,
                mode=job.options.mode.value,
                intensity=job.options.intensity.value,
            )
            if getattr(job.options, "deep_humanize", False):
                refined = await self._dehumanize_pass(
                    adapter,
                    provider_cfg,
                    output_text,
                    gen_req,
                    job.options,
                    timeout_seconds,
                )
                if refined:
                    output_text = refined

            job.completed_chunks[chunk.chunk_id] = output_text
            job.current_provider = provider_cfg.provider_id
            job.current_model = result.model_id
            has_more = next_idx + 1 < len(job.chunks)
            job.status = JobStatus.RUNNING if has_more else JobStatus.COMPLETED
            if len(attempted) > 1:
                logger.warning(
                    "Chunk %s succeeded via fallback provider %s after %s",
                    chunk.chunk_id,
                    provider_cfg.provider_id,
                    ", ".join(attempted[:-1]),
                )
            return has_more, True

        if job.last_error_message_safe is None:
            job.last_error_message_safe = last_error or "All providers failed"
        job.failed_chunks.append(chunk.chunk_id)
        return True, False


    async def _dehumanize_pass(
        self,
        adapter: GenerationProvider,
        provider_cfg,
        draft: str,
        base_request: GenerationRequest,
        options,
        timeout_seconds: float,
    ) -> str | None:
        """Optional second pass that strips remaining machine-like patterns."""
        system, user = build_dehumanize_prompt(language_hint=None)
        second_req = GenerationRequest(
            system_instruction=system,
            user_instruction=user,
            chunk_text=draft,
            model=base_request.model,
            max_output_tokens=max(2000, len(draft.split()) * 2),
            timeout_seconds=base_request.timeout_seconds,
            job_id=base_request.job_id,
            chunk_id=base_request.chunk_id,
        )
        try:
            result = await asyncio.wait_for(
                adapter.generate(second_req), timeout=timeout_seconds + 5
            )
            if result.output_text.strip():
                return apply_human_touch(
                    result.output_text,
                    mode=options.mode.value,
                    intensity=options.intensity.value,
                )
        except Exception as exc:  # never fail a chunk because of the bonus pass
            logger.warning(
                "Second human pass failed on %s: %s", provider_cfg.provider_id, exc
            )
        return None

    @staticmethod
    def assemble_output(job: HumanizationJob) -> str:
        sorted_ids = sorted(
            job.completed_chunks.keys(),
            key=lambda cid: int(cid.replace("chunk-", "").zfill(4)),
        )
        parts = [job.completed_chunks[cid] for cid in sorted_ids]
        return "\n\n".join(parts)
