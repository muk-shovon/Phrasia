"""Phrasia — domain entities, enums, and state machines.

This layer is intentionally free of Reflex and vendor SDK imports.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class HumanizationMode(str, Enum):
    NATURAL = "natural"
    PROFESSIONAL = "professional"
    ACADEMIC = "academic"
    SIMPLE = "simple"
    CONVERSATIONAL = "conversational"
    CONCISE = "concise"
    EXPAND = "expand"
    CUSTOM = "custom"


class RewriteIntensity(str, Enum):
    LIGHT = "light"
    BALANCED = "balanced"
    STRONG = "strong"


class JobStatus(str, Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSE_REQUESTED = "pause_requested"
    PAUSED_USER = "paused_user"
    PAUSED_RATE_LIMIT = "paused_rate_limit"
    PAUSED_QUOTA = "paused_quota"
    PAUSED_PROVIDER_ERROR = "paused_provider_error"
    FAILED = "failed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class ChunkStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ProviderTier(str, Enum):
    FREE = "free"
    TRIAL = "trial"
    PAID = "paid"
    UNKNOWN = "unknown"


class ProviderTask(str, Enum):
    GENERATION = "generation"
    DETECTION = "detection"
    PLAGIARISM = "plagiarism"


class ProviderErrorCategory(str, Enum):
    AUTHENTICATION_ERROR = "authentication_error"
    PERMISSION_ERROR = "permission_error"
    RATE_LIMITED = "rate_limited"
    QUOTA_EXHAUSTED = "quota_exhausted"
    BILLING_REQUIRED = "billing_required"
    INVALID_REQUEST = "invalid_request"
    MODEL_UNAVAILABLE = "model_unavailable"
    CONTENT_POLICY_BLOCK = "content_policy_block"
    TIMEOUT = "timeout"
    TRANSIENT_PROVIDER_ERROR = "transient_provider_error"
    OUTPUT_TRUNCATED = "output_truncated"
    UNKNOWN_PROVIDER_ERROR = "unknown_provider_error"


class RoutingMode(str, Enum):
    FREE_ONLY = "free_only"
    HYBRID = "hybrid"
    MANUAL = "manual"


@dataclass
class HumanizationOptions:
    mode: HumanizationMode = HumanizationMode.NATURAL
    intensity: RewriteIntensity = RewriteIntensity.BALANCED
    preserve_meaning: bool = True
    preserve_facts: bool = True
    preserve_citations: bool = True
    preserve_formatting: bool = True
    preserve_quotes: bool = True
    custom_instruction: Optional[str] = None
    target_language: Optional[str] = None
    deep_humanize: bool = False


@dataclass
class ChunkPlan:
    chunk_id: str
    sequence_index: int
    source_start_offset: int
    source_end_offset: int
    source_text: str
    source_hash: str
    protected_spans: list = field(default_factory=list)


@dataclass
class ProtectedSpan:
    span_id: str
    start_offset: int
    end_offset: int
    span_type: str  # url, email, code, citation, quote, number, identifier
    original_text: str
    placeholder: str


def is_terminal_status(status: JobStatus) -> bool:
    return status in (JobStatus.COMPLETED, JobStatus.CANCELLED)


def can_resume_from(status: JobStatus) -> bool:
    return status in (
        JobStatus.PAUSED_USER,
        JobStatus.PAUSED_RATE_LIMIT,
        JobStatus.PAUSED_QUOTA,
        JobStatus.PAUSED_PROVIDER_ERROR,
        JobStatus.FAILED,
        JobStatus.QUEUED,
    )
