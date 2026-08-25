"""Deterministic GeoTask context-construction seam for Stack v2.1.

This module assembles explicit GeoTask-owned requirement assessments and
explicitly selected provider candidates into ``TaskContext``,
``SufficiencyAssessment``, and ``ContextConstructionTrace``.

It does not acquire candidates, rank them, derive requirements, assess
relevance/applicability/resolution, or inspect provider truth semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Sequence, runtime_checkable

from geotask_core.v1.context_provider import ContextCandidate
from geotask_core.v1.task_context import (
    CONTEXT_CONTRACT_VERSION,
    ContextAssessment,
    ContextConstructionTrace,
    ContextGap,
    ContextRequirement,
    SufficiencyAssessment,
    SufficiencyStatus,
    TaskContext,
    TaskContextContractError,
    TaskFrame,
    context_construction_trace_payload,
    sufficiency_assessment_payload,
    task_context_payload,
    validate_context_bundle,
)

CONTEXT_CONSTRUCTION_REQUEST_CONTRACT_ID = "geotask.context-construction-request"
CONTEXT_CONSTRUCTION_RESULT_CONTRACT_ID = "geotask.context-construction-result"


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


def _unique_texts(values: Sequence[str]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return tuple(result)


@dataclass(frozen=True, slots=True)
class AssessedContextItem:
    """One explicit assessment plus an optional explicitly selected candidate."""

    requirement_id: str
    assessment: ContextAssessment
    selected_candidate: ContextCandidate | None = None
    gap: ContextGap | None = None

    def __post_init__(self) -> None:
        _require_text(self.requirement_id, "requirement_id")
        if self.assessment.requirement_id != self.requirement_id:
            raise TaskContextContractError(
                "assessment.requirement_id must match AssessedContextItem.requirement_id"
            )
        if (
            self.selected_candidate is not None
            and self.selected_candidate.requirement_id != self.requirement_id
        ):
            raise TaskContextContractError(
                "selected_candidate.requirement_id must match AssessedContextItem.requirement_id"
            )
        if self.gap is not None and self.gap.requirement_id != self.requirement_id:
            raise TaskContextContractError(
                "gap.requirement_id must match AssessedContextItem.requirement_id"
            )

        may_select = self.assessment.status in {"satisfied", "degraded"}
        if may_select and self.selected_candidate is None:
            raise TaskContextContractError(
                f"assessment status {self.assessment.status!r} requires an explicit selected_candidate"
            )
        if not may_select and self.selected_candidate is not None:
            raise TaskContextContractError(
                f"assessment status {self.assessment.status!r} cannot expose a selected_candidate"
            )


@dataclass(frozen=True, slots=True)
class ContextConstructionRequest:
    """All explicit decisions required for deterministic context assembly."""

    request_ref: str
    context_ref: str
    assessment_ref: str
    trace_ref: str
    task_frame: TaskFrame
    requirements: tuple[ContextRequirement, ...]
    items: tuple[AssessedContextItem, ...]
    constructed_at: str
    assessed_at: str
    sufficiency_status: SufficiencyStatus
    valid_until: str | None
    method: str
    version: str
    contract_version: str = CONTEXT_CONTRACT_VERSION
    source_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name, value in (
            ("request_ref", self.request_ref),
            ("context_ref", self.context_ref),
            ("assessment_ref", self.assessment_ref),
            ("trace_ref", self.trace_ref),
            ("method", self.method),
            ("version", self.version),
        ):
            _require_text(value, name)
        if self.contract_version != CONTEXT_CONTRACT_VERSION:
            raise TaskContextContractError(
                f"contract_version must equal {CONTEXT_CONTRACT_VERSION!r}"
            )
        object.__setattr__(self, "source_refs", _unique_texts(self.source_refs))

        constructed_at = _require_timestamp(self.constructed_at, "constructed_at")
        assessed_at = _require_timestamp(self.assessed_at, "assessed_at")
        if assessed_at < constructed_at:
            raise TaskContextContractError("assessed_at must not be earlier than constructed_at")
        if self.valid_until is not None:
            valid_until = _require_timestamp(self.valid_until, "valid_until")
            if valid_until < assessed_at:
                raise TaskContextContractError("valid_until must not be earlier than assessed_at")

        requirement_ids = [item.requirement_id for item in self.requirements]
        if len(requirement_ids) != len(set(requirement_ids)):
            raise TaskContextContractError("requirements must have unique requirement_id values")
        item_ids = [item.requirement_id for item in self.items]
        if len(item_ids) != len(set(item_ids)):
            raise TaskContextContractError("items must have unique requirement_id values")
        if set(item_ids) != set(requirement_ids):
            raise TaskContextContractError(
                "items must cover ContextConstructionRequest requirements exactly"
            )

        requirement_by_id = {item.requirement_id: item for item in self.requirements}
        for item in self.items:
            requirement = requirement_by_id[item.requirement_id]
            if item.assessment.critical != requirement.critical:
                raise TaskContextContractError(
                    f"assessment criticality differs from requirement {item.requirement_id!r}"
                )
            if item.gap is not None and item.gap.critical != requirement.critical:
                raise TaskContextContractError(
                    f"gap criticality differs from requirement {item.requirement_id!r}"
                )


@dataclass(frozen=True, slots=True)
class ContextConstructionResult:
    """Closed GeoTask context bundle ready for external consumers."""

    request_ref: str
    context: TaskContext
    sufficiency: SufficiencyAssessment
    trace: ContextConstructionTrace

    def __post_init__(self) -> None:
        _require_text(self.request_ref, "request_ref")
        validate_context_bundle(self.context, self.sufficiency, self.trace)


@runtime_checkable
class ContextConstructor(Protocol):
    """GeoTask-owned construction seam; it does not acquire or assess candidates."""

    @property
    def constructor_ref(self) -> str:
        ...

    def construct(self, request: ContextConstructionRequest) -> ContextConstructionResult:
        ...


class DeterministicContextConstructor:
    """Dependency-free reference assembler for explicitly assessed context."""

    def __init__(self, constructor_ref: str = "geotask://constructor/deterministic-v0.1") -> None:
        _require_text(constructor_ref, "constructor_ref")
        self._constructor_ref = constructor_ref

    @property
    def constructor_ref(self) -> str:
        return self._constructor_ref

    def construct(self, request: ContextConstructionRequest) -> ContextConstructionResult:
        values = {}
        gaps: list[ContextGap] = []
        assessments: list[ContextAssessment] = []
        selected_requirement_ids: list[str] = []
        source_refs: list[str] = [self.constructor_ref, *request.source_refs]

        item_by_requirement = {item.requirement_id: item for item in request.items}
        for requirement in request.requirements:
            item = item_by_requirement[requirement.requirement_id]
            assessments.append(item.assessment)
            source_refs.extend(item.assessment.source_refs)

            if item.selected_candidate is not None:
                selected_requirement_ids.append(requirement.requirement_id)
                values[requirement.requirement_id] = item.selected_candidate.payload
                source_refs.append(item.selected_candidate.candidate_ref)
                source_refs.append(item.selected_candidate.provider_ref)
                source_refs.extend(item.selected_candidate.source_refs)

            if item.gap is not None:
                gaps.append(item.gap)
                source_refs.extend(item.gap.source_refs)

        lineage = _unique_texts(source_refs)
        trace = ContextConstructionTrace(
            trace_ref=request.trace_ref,
            context_ref=request.context_ref,
            constructed_at=request.constructed_at,
            requirement_ids=tuple(item.requirement_id for item in request.requirements),
            selected_requirement_ids=tuple(selected_requirement_ids),
            gap_refs=tuple(item.gap_id for item in gaps),
            source_refs=lineage,
            method=request.method,
            version=request.version,
        )
        context = TaskContext(
            context_ref=request.context_ref,
            task_frame=request.task_frame,
            requirements=request.requirements,
            constructed_at=request.constructed_at,
            values=values,
            source_refs=lineage,
            valid_until=request.valid_until,
            trace_ref=request.trace_ref,
        )
        sufficiency = SufficiencyAssessment(
            assessment_ref=request.assessment_ref,
            context_ref=request.context_ref,
            assessed_at=request.assessed_at,
            status=request.sufficiency_status,
            assessments=tuple(assessments),
            gaps=tuple(gaps),
            source_refs=lineage,
            valid_until=request.valid_until,
            trace_ref=request.trace_ref,
        )
        return ContextConstructionResult(
            request_ref=request.request_ref,
            context=context,
            sufficiency=sufficiency,
            trace=trace,
        )


def context_construction_request_payload(request: ContextConstructionRequest) -> dict[str, object]:
    """Serialize decision references/status without duplicating provider payload bytes."""
    return {
        "contract": CONTEXT_CONSTRUCTION_REQUEST_CONTRACT_ID,
        "contract_version": request.contract_version,
        "request_ref": request.request_ref,
        "context_ref": request.context_ref,
        "assessment_ref": request.assessment_ref,
        "trace_ref": request.trace_ref,
        "task_id": request.task_frame.task_id,
        "requirement_ids": [item.requirement_id for item in request.requirements],
        "items": [
            {
                "requirement_id": item.requirement_id,
                "assessment_status": item.assessment.status,
                "selected_candidate_ref": (
                    None if item.selected_candidate is None else item.selected_candidate.candidate_ref
                ),
                "gap_ref": None if item.gap is None else item.gap.gap_id,
            }
            for item in request.items
        ],
        "constructed_at": request.constructed_at,
        "assessed_at": request.assessed_at,
        "sufficiency_status": request.sufficiency_status,
        "valid_until": request.valid_until,
        "method": request.method,
        "version": request.version,
        "source_refs": list(request.source_refs),
    }


def context_construction_result_payload(result: ContextConstructionResult) -> dict[str, object]:
    """Serialize the complete closed bundle for integration/replay boundaries."""
    return {
        "contract": CONTEXT_CONSTRUCTION_RESULT_CONTRACT_ID,
        "contract_version": CONTEXT_CONTRACT_VERSION,
        "request_ref": result.request_ref,
        "context": task_context_payload(result.context),
        "sufficiency": sufficiency_assessment_payload(result.sufficiency),
        "trace": context_construction_trace_payload(result.trace),
    }
