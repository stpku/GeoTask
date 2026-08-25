"""Explicit sufficiency-to-construction binding for GeoTask v2.1.

GT-C3c preserves an already-composed ``SufficiencyAssessment`` across the
construction boundary. Binding validates closure and carries composition lineage into
``ContextConstructionRequest.source_refs``; it does not recompute requirement
assessment or aggregate sufficiency.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Sequence

from geotask_core.v1.context_construction import (
    ContextConstructionRequest,
    ContextConstructionResult,
    ContextConstructor,
)
from geotask_core.v1.task_context import (
    CONTEXT_CONTRACT_VERSION,
    ContextGap,
    SufficiencyAssessment,
    TaskContextContractError,
)

SUFFICIENCY_CONSTRUCTION_BINDING_CONTRACT_ID = "geotask.sufficiency-construction-binding"


def _require_text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise TaskContextContractError(f"{name} must be a non-empty string")


def _require_timestamp(value: str, name: str) -> datetime:
    _require_text(value, name)
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise TaskContextContractError(f"{name} must be an ISO 8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TaskContextContractError(f"{name} must include a timezone offset")
    return parsed


def _dedupe_texts(values: Sequence[str]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        _require_text(value, "source_ref")
        if value not in seen:
            seen.add(value)
            result.append(value)
    return tuple(result)


def _request_assessments(request: ContextConstructionRequest):
    return tuple(item.assessment for item in request.items)


def _request_gaps(request: ContextConstructionRequest) -> tuple[ContextGap, ...]:
    return tuple(item.gap for item in request.items if item.gap is not None)


@dataclass(frozen=True, slots=True)
class SufficiencyConstructionBinding:
    """Replayable receipt proving one sufficiency conclusion is bound to one request."""

    binding_ref: str
    request_ref: str
    context_ref: str
    assessment_ref: str
    sufficiency_method_ref: str
    bound_at: str
    source_refs: tuple[str, ...]
    contract_version: str = CONTEXT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name, value in (
            ("binding_ref", self.binding_ref),
            ("request_ref", self.request_ref),
            ("context_ref", self.context_ref),
            ("assessment_ref", self.assessment_ref),
            ("sufficiency_method_ref", self.sufficiency_method_ref),
        ):
            _require_text(value, name)
        _require_timestamp(self.bound_at, "bound_at")
        if self.contract_version != CONTEXT_CONTRACT_VERSION:
            raise TaskContextContractError(
                f"contract_version must equal {CONTEXT_CONTRACT_VERSION!r}"
            )
        object.__setattr__(self, "source_refs", _dedupe_texts(self.source_refs))
        if self.binding_ref not in self.source_refs:
            raise TaskContextContractError("binding source_refs must include binding_ref")
        if self.sufficiency_method_ref not in self.source_refs:
            raise TaskContextContractError(
                "binding source_refs must include sufficiency_method_ref"
            )


@dataclass(frozen=True, slots=True)
class BoundContextConstruction:
    """Validated construction input plus the sufficiency conclusion it must preserve."""

    binding: SufficiencyConstructionBinding
    request: ContextConstructionRequest
    sufficiency: SufficiencyAssessment

    def __post_init__(self) -> None:
        _validate_binding_closure(self.binding, self.request, self.sufficiency)


def bind_sufficiency_to_construction(
    request: ContextConstructionRequest,
    sufficiency: SufficiencyAssessment,
    *,
    binding_ref: str,
    sufficiency_method_ref: str,
    bound_at: str,
) -> BoundContextConstruction:
    """Bind an existing sufficiency result to construction without recomputation."""
    _require_text(binding_ref, "binding_ref")
    _require_text(sufficiency_method_ref, "sufficiency_method_ref")
    bound_time = _require_timestamp(bound_at, "bound_at")
    assessed_time = _require_timestamp(sufficiency.assessed_at, "sufficiency.assessed_at")
    if bound_time < assessed_time:
        raise TaskContextContractError("bound_at must not be earlier than sufficiency.assessed_at")

    _validate_request_matches_sufficiency(request, sufficiency)
    if sufficiency_method_ref not in sufficiency.source_refs:
        raise TaskContextContractError(
            "sufficiency.source_refs must include explicit sufficiency_method_ref"
        )

    lineage = _dedupe_texts(
        (
            *request.source_refs,
            binding_ref,
            sufficiency_method_ref,
            *sufficiency.source_refs,
        )
    )
    bound_request = replace(request, source_refs=lineage)
    binding = SufficiencyConstructionBinding(
        binding_ref=binding_ref,
        request_ref=request.request_ref,
        context_ref=request.context_ref,
        assessment_ref=request.assessment_ref,
        sufficiency_method_ref=sufficiency_method_ref,
        bound_at=bound_at,
        source_refs=lineage,
    )
    return BoundContextConstruction(
        binding=binding,
        request=bound_request,
        sufficiency=sufficiency,
    )


def construct_bound_context(
    constructor: ContextConstructor,
    bound: BoundContextConstruction,
) -> ContextConstructionResult:
    """Construct and prove that composition/binding lineage survived unchanged."""
    result = constructor.construct(bound.request)
    _validate_result_matches_bound(result, bound)
    return result


def sufficiency_construction_binding_payload(
    binding: SufficiencyConstructionBinding,
) -> dict[str, object]:
    return {
        "contract": SUFFICIENCY_CONSTRUCTION_BINDING_CONTRACT_ID,
        "contract_version": binding.contract_version,
        "binding_ref": binding.binding_ref,
        "request_ref": binding.request_ref,
        "context_ref": binding.context_ref,
        "assessment_ref": binding.assessment_ref,
        "sufficiency_method_ref": binding.sufficiency_method_ref,
        "bound_at": binding.bound_at,
        "source_refs": list(binding.source_refs),
    }


def _validate_request_matches_sufficiency(
    request: ContextConstructionRequest,
    sufficiency: SufficiencyAssessment,
) -> None:
    checks = (
        (request.context_ref, sufficiency.context_ref, "context_ref"),
        (request.assessment_ref, sufficiency.assessment_ref, "assessment_ref"),
        (request.assessed_at, sufficiency.assessed_at, "assessed_at"),
        (request.sufficiency_status, sufficiency.status, "sufficiency_status"),
        (request.valid_until, sufficiency.valid_until, "valid_until"),
        (request.trace_ref, sufficiency.trace_ref, "trace_ref"),
    )
    for request_value, sufficiency_value, name in checks:
        if request_value != sufficiency_value:
            raise TaskContextContractError(
                f"construction request {name} must match composed SufficiencyAssessment"
            )

    if _request_assessments(request) != sufficiency.assessments:
        raise TaskContextContractError(
            "construction request item assessments must match composed SufficiencyAssessment"
        )
    if _request_gaps(request) != sufficiency.gaps:
        raise TaskContextContractError(
            "construction request item gaps must match composed SufficiencyAssessment"
        )


def _validate_binding_closure(
    binding: SufficiencyConstructionBinding,
    request: ContextConstructionRequest,
    sufficiency: SufficiencyAssessment,
) -> None:
    _validate_request_matches_sufficiency(request, sufficiency)
    if binding.request_ref != request.request_ref:
        raise TaskContextContractError("binding.request_ref must match request.request_ref")
    if binding.context_ref != request.context_ref:
        raise TaskContextContractError("binding.context_ref must match request.context_ref")
    if binding.assessment_ref != request.assessment_ref:
        raise TaskContextContractError("binding.assessment_ref must match request.assessment_ref")
    if binding.sufficiency_method_ref not in sufficiency.source_refs:
        raise TaskContextContractError(
            "binding sufficiency_method_ref must be present in SufficiencyAssessment.source_refs"
        )
    for ref in binding.source_refs:
        if ref not in request.source_refs:
            raise TaskContextContractError(
                "all binding source_refs must be carried by ContextConstructionRequest.source_refs"
            )


def _validate_result_matches_bound(
    result: ContextConstructionResult,
    bound: BoundContextConstruction,
) -> None:
    expected = bound.sufficiency
    actual = result.sufficiency
    checks = (
        (actual.assessment_ref, expected.assessment_ref, "assessment_ref"),
        (actual.context_ref, expected.context_ref, "context_ref"),
        (actual.assessed_at, expected.assessed_at, "assessed_at"),
        (actual.status, expected.status, "status"),
        (actual.assessments, expected.assessments, "assessments"),
        (actual.gaps, expected.gaps, "gaps"),
        (actual.valid_until, expected.valid_until, "valid_until"),
        (actual.trace_ref, expected.trace_ref, "trace_ref"),
    )
    for actual_value, expected_value, name in checks:
        if actual_value != expected_value:
            raise TaskContextContractError(
                f"constructed SufficiencyAssessment {name} drifted from bound composition result"
            )

    required_lineage = set(bound.binding.source_refs)
    for name, refs in (
        ("TaskContext", result.context.source_refs),
        ("SufficiencyAssessment", result.sufficiency.source_refs),
        ("ContextConstructionTrace", result.trace.source_refs),
    ):
        missing = sorted(required_lineage - set(refs))
        if missing:
            raise TaskContextContractError(
                f"{name} lost sufficiency construction lineage: " + ", ".join(missing)
            )
