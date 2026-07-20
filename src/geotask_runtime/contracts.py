"""GeoTask Runtime contracts — dataclasses and enums for v1.0 orchestration.

Imports v1.0 enums from geotask_core.v1.enums for canonical type definitions.
Maintains backward compatibility with v0.1 TaskStatus values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# ── Re-export v1.0 canonical types from Core ────────────────────────
from geotask_core.v1.enums import (
    AssuranceLevel,
    ClaimStatus,
    EncodingType,
    ExecutionMode,
    ExecutionStatus,
    ExecutorType,
    VerificationMode,
)

# ── Backward-compatible TaskStatus (v0.1) ───────────────────────────
from enum import Enum


class TaskStatus(str, Enum):
    """Legacy task status values (v0.1 compatible)."""
    VERIFIED = "verified"
    CONTRADICTED = "contradicted"
    NEED_REVIEW = "need_review"
    INVALID_OPERATOR = "invalid_operator"
    INVALID_REFERENCE = "invalid_reference"


# ── v1.0 Runtime Contracts ──────────────────────────────────────────

@dataclass
class TaskRequest:
    task_id: str
    task_type: str
    task_goal: str
    domain: str = "general_spatial"
    input_objects: list[dict] = field(default_factory=list)
    requested_outputs: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    token_budget: Optional[int] = None
    metadata: dict = field(default_factory=dict)
    # v1.0: execution mode preference
    preferred_execution_mode: str = ""  # ExecutionMode value


@dataclass
class TaskContext:
    local_objects: dict = field(default_factory=dict)
    available_operators: list[str] = field(default_factory=list)
    available_data_sources: list[str] = field(default_factory=list)
    domain_rules: list[dict] = field(default_factory=list)
    known_gaps: list[str] = field(default_factory=list)


@dataclass
class EncodingPlan:
    encoding_type: EncodingType  # v1.0: typed enum
    encoded_task: str = ""
    estimated_tokens: int = 0
    required_objects: list[str] = field(default_factory=list)
    required_operators: list[str] = field(default_factory=list)
    required_constraints: list[str] = field(default_factory=list)
    verification_requirements: list[str] = field(default_factory=list)
    reason: str = ""


@dataclass
class ModelRequest:
    provider: str = "mock"
    model: str = "deterministic-placeholder"
    prompt: str = ""
    encoding_plan: Optional[EncodingPlan] = None
    temperature: float = 0.0
    max_output_tokens: int = 1024


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ModelResponse:
    raw_text: str = ""
    structured_content: dict = field(default_factory=dict)
    provider_metadata: dict = field(default_factory=dict)
    token_usage: Optional[TokenUsage] = None
    error: Optional[str] = None


@dataclass
class VerificationPlan:
    verifiable_claims: list[str] = field(default_factory=list)
    non_verifiable_claims: list[str] = field(default_factory=list)
    required_operators: list[str] = field(default_factory=list)
    required_data: list[str] = field(default_factory=list)
    review_requirements: list[str] = field(default_factory=list)
    # v1.0: verification mode and required assurance
    verification_mode: str = ""  # VerificationMode value
    required_assurance: str = ""  # AssuranceLevel value


@dataclass
class RuntimeEvent:
    event_type: str
    timestamp: str = ""
    detail: dict = field(default_factory=dict)


@dataclass
class GovernedTaskResult:
    task_id: str
    normalized_result: dict = field(default_factory=dict)
    verification_result: dict = field(default_factory=dict)
    overall_status: str = TaskStatus.NEED_REVIEW.value
    review_reasons: list[str] = field(default_factory=list)
    used_encoding_plan: Optional[EncodingPlan] = None
    runtime_events: list[RuntimeEvent] = field(default_factory=list)
    # v1.0: execution and assurance tracking
    execution_mode: str = ""  # ExecutionMode value
    execution_status: str = ""  # ExecutionStatus value
    assurance_level: str = ""  # AssuranceLevel value
    verification_mode: str = ""  # VerificationMode value
