"""GeoTask Runtime contracts v0.1 — dataclasses and enums.

THIS IS A SKELETON / INTERFACE DEFINITION.
All types here define the contract between public Core and private Runtime.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class EncodingType(str, Enum):
    NATURAL_LANGUAGE = "natural_language"
    GEOTASK_YAML = "geotask_yaml"
    COMPACT_DSL = "compact_dsl"


class TaskStatus(str, Enum):
    VERIFIED = "verified"
    CONTRADICTED = "contradicted"
    NEED_REVIEW = "need_review"
    INVALID_OPERATOR = "invalid_operator"
    INVALID_REFERENCE = "invalid_reference"


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


@dataclass
class TaskContext:
    local_objects: dict = field(default_factory=dict)
    available_operators: list[str] = field(default_factory=list)
    available_data_sources: list[str] = field(default_factory=list)
    domain_rules: list[dict] = field(default_factory=list)
    known_gaps: list[str] = field(default_factory=list)


@dataclass
class EncodingPlan:
    encoding_type: EncodingType
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
