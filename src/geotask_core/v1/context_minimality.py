"""Minimum-context-cost contracts for GeoTask v3.0 alignment.

GT-C4 optimizes carried TaskContext values only after task sufficiency is explicit.
Core does not decide which non-critical values are redundant and does not collapse
cost dimensions into one score. An explicit ContextMinimalityMethod owns that policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from types import MappingProxyType
from typing import Literal, Mapping, Protocol, Sequence, runtime_checkable

from geotask_core.v1.task_context import (
    CONTEXT_CONTRACT_VERSION,
    ContextRequirement,
    SufficiencyAssessment,
    TaskContext,
    TaskContextContractError,
)

CONTEXT_MINIMALITY_ASSESSMENT_CONTRACT_ID = "geotask.context-minimality-assessment"
MINIMUM_SUFFICIENT_TASK_CONTEXT_CONTRACT_ID = "geotask.minimum-sufficient-task-context"

ContextContributionStatus = Literal["required", "removable", "unknown"]
ContextMinimalityStatus = Literal["minimal", "reducible", "unknown"]
CONTEXT_CONTRIBUTION_STATUSES = frozenset({"required", "removable", "unknown"})
CONTEXT_MINIMALITY_STATUSES = frozenset({"minimal", "reducible", "unknown"})


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


def _unique_texts(values: Sequence[str], name: str) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for index, value in enumerate(values):
        _require_text(value, f"{name}[{index}]")
        if value in seen:
            raise TaskContextContractError(f"{name} must not contain duplicate {value!r}")
        seen.add(value)
        result.append(value)
    return tuple(result)


def _dedupe_texts(values: Sequence[str]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        _require_text(value, "source_ref")
        if value not in seen:
            seen.add(value)
            result.append(value)
    return tuple(result)


def _check_nonnegative(value: float | int | None, name: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TaskContextContractError(f"{name} must be a non-negative finite number or None")
    if not isfinite(float(value)) or float(value) < 0:
        raise TaskContextContractError(f"{name} must be a non-negative finite number or None")


@dataclass(frozen=True, slots=True)
class ContextCostVector:
    """Separate cost dimensions; ``None`` means explicitly unknown, not zero."""

    acquisition_units: float | None = None
    carried_bytes: int | None = None
    llm_units: int | None = None
    provider_latency_ms: float | None = None
    human_recovery_units: float | None = None

    def __post_init__(self) -> None:
        for name in (
            "acquisition_units",
            "carried_bytes",
            "llm_units",
            "provider_latency_ms",
            "human_recovery_units",
        ):
            _check_nonnegative(getattr(self, name), name)
        if self.carried_bytes is not None and not isinstance(self.carried_bytes, int):
            raise TaskContextContractError("carried_bytes must be an integer or None")
        if self.llm_units is not None and not isinstance(self.llm_units, int):
            raise TaskContextContractError("llm_units must be an integer or None")


@dataclass(frozen=True, slots=True)
class ContextContribution:
    """Method-owned conclusion about one currently carried context value."""

    contribution_ref: str
    context_ref: str
    requirement_id: str
    status: ContextContributionStatus
    reason: str
    cost: ContextCostVector
    source_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.contribution_ref, "contribution_ref")
        _require_text(self.context_ref, "context_ref")
        _require_text(self.requirement_id, "requirement_id")
        if self.status not in CONTEXT_CONTRIBUTION_STATUSES:
            raise TaskContextContractError(
                "status must be one of: " + ", ".join(sorted(CONTEXT_CONTRIBUTION_STATUSES))
            )
        _require_text(self.reason, "reason")
        object.__setattr__(self, "source_refs", _unique_texts(self.source_refs, "source_refs"))


@dataclass(frozen=True, slots=True)
class ContextMinimalityAssessment:
    """Explicit method-owned reduction plan for one sufficient source context."""

    assessment_ref: str
    source_context_ref: str
    target_context_ref: str
    method_ref: str
    assessed_at: str
    status: ContextMinimalityStatus
    contributions: tuple[ContextContribution, ...]
    retained_requirement_ids: tuple[str, ...]
    removed_requirement_ids: tuple[str, ...]
    source_refs: tuple[str, ...] = ()
    contract_version: str = CONTEXT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name, value in (
            ("assessment_ref", self.assessment_ref),
            ("source_context_ref", self.source_context_ref),
            ("target_context_ref", self.target_context_ref),
            ("method_ref", self.method_ref),
        ):
            _require_text(value, name)
        if self.source_context_ref == self.target_context_ref:
            raise TaskContextContractError("target_context_ref must differ from source_context_ref")
        _require_timestamp(self.assessed_at, "assessed_at")
        if self.status not in CONTEXT_MINIMALITY_STATUSES:
            raise TaskContextContractError(
                "status must be one of: " + ", ".join(sorted(CONTEXT_MINIMALITY_STATUSES))
            )
        if self.contract_version != CONTEXT_CONTRACT_VERSION:
            raise TaskContextContractError(
                f"contract_version must equal {CONTEXT_CONTRACT_VERSION!r}"
            )
        object.__setattr__(
            self,
            "retained_requirement_ids",
            _unique_texts(self.retained_requirement_ids, "retained_requirement_ids"),
        )
        object.__setattr__(
            self,
            "removed_requirement_ids",
            _unique_texts(self.removed_requirement_ids, "removed_requirement_ids"),
        )
        if set(self.retained_requirement_ids) & set(self.removed_requirement_ids):
            raise TaskContextContractError("retained and removed requirement IDs must be disjoint")
        contribution_ids = [item.requirement_id for item in self.contributions]
        if len(contribution_ids) != len(set(contribution_ids)):
            raise TaskContextContractError("contributions must contain at most one result per requirement_id")
        for contribution in self.contributions:
            if contribution.context_ref != self.source_context_ref:
                raise TaskContextContractError("contribution.context_ref must match source_context_ref")
        object.__setattr__(self, "source_refs", _unique_texts(self.source_refs, "source_refs"))
        if self.method_ref not in self.source_refs:
            raise TaskContextContractError("source_refs must include method_ref")


@runtime_checkable
class ContextMinimalityMethod(Protocol):
    """Explicit policy seam for minimum-context-cost reasoning."""

    @property
    def method_ref(self) -> str:
        ...

    def assess_minimality(
        self,
        context: TaskContext,
        sufficiency: SufficiencyAssessment,
        costs: Mapping[str, ContextCostVector],
        *,
        target_context_ref: str,
        as_of: str,
    ) -> ContextMinimalityAssessment:
        ...


@dataclass(frozen=True, slots=True)
class MinimumSufficientTaskContext:
    """Projected TaskContext with independently explicit target sufficiency."""

    source_context_ref: str
    context: TaskContext
    sufficiency: SufficiencyAssessment
    minimality: ContextMinimalityAssessment
    contract_version: str = CONTEXT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _require_text(self.source_context_ref, "source_context_ref")
        if self.contract_version != CONTEXT_CONTRACT_VERSION:
            raise TaskContextContractError(
                f"contract_version must equal {CONTEXT_CONTRACT_VERSION!r}"
            )
        if self.minimality.source_context_ref != self.source_context_ref:
            raise TaskContextContractError("minimality.source_context_ref must match source_context_ref")
        if self.context.context_ref != self.minimality.target_context_ref:
            raise TaskContextContractError("context.context_ref must match minimality.target_context_ref")
        if self.sufficiency.context_ref != self.context.context_ref:
            raise TaskContextContractError("sufficiency.context_ref must match projected context.context_ref")
        if self.sufficiency.status != "sufficient":
            raise TaskContextContractError(
                "MinimumSufficientTaskContext requires explicit target sufficiency status='sufficient'"
            )
        if self.minimality.status != "minimal":
            raise TaskContextContractError(
                "MinimumSufficientTaskContext requires explicit minimality status='minimal'"
            )
        if self.sufficiency.trace_ref is not None or self.context.trace_ref is not None:
            raise TaskContextContractError(
                "minimum-context projection uses minimality lineage rather than construction trace"
            )


def assess_context_minimality(
    method: ContextMinimalityMethod,
    context: TaskContext,
    sufficiency: SufficiencyAssessment,
    costs: Mapping[str, ContextCostVector],
    *,
    target_context_ref: str,
    as_of: str,
) -> ContextMinimalityAssessment:
    """Apply explicit reduction policy and validate fail-closed safety invariants."""
    _require_text(method.method_ref, "ContextMinimalityMethod.method_ref")
    _require_text(target_context_ref, "target_context_ref")
    _require_timestamp(as_of, "as_of")
    if sufficiency.context_ref != context.context_ref:
        raise TaskContextContractError("source sufficiency.context_ref must match context.context_ref")
    if sufficiency.status != "sufficient":
        raise TaskContextContractError("minimum-context assessment requires sufficient source context")
    carried_ids = tuple(context.values.keys())
    if set(costs) != set(carried_ids):
        raise TaskContextContractError("costs must cover carried TaskContext values exactly")

    result = method.assess_minimality(
        context,
        sufficiency,
        MappingProxyType(dict(costs)),
        target_context_ref=target_context_ref,
        as_of=as_of,
    )
    _validate_minimality_result(method.method_ref, context, sufficiency, result, as_of=as_of)
    return result


def build_minimum_sufficient_task_context(
    source_context: TaskContext,
    source_sufficiency: SufficiencyAssessment,
    minimality: ContextMinimalityAssessment,
    target_sufficiency: SufficiencyAssessment,
) -> MinimumSufficientTaskContext:
    """Build a value projection only after target sufficiency is independently explicit."""
    if source_sufficiency.context_ref != source_context.context_ref:
        raise TaskContextContractError("source_sufficiency.context_ref must match source_context.context_ref")
    if source_sufficiency.status != "sufficient":
        raise TaskContextContractError("source context must be explicitly sufficient")
    if minimality.source_context_ref != source_context.context_ref:
        raise TaskContextContractError("minimality source_context_ref must match source context")
    if minimality.status != "minimal":
        raise TaskContextContractError(
            "MinimumSufficientTaskContext requires explicit minimality status='minimal'"
        )
    _validate_minimality_result(
        minimality.method_ref,
        source_context,
        source_sufficiency,
        minimality,
        as_of=minimality.assessed_at,
    )
    if target_sufficiency.context_ref != minimality.target_context_ref:
        raise TaskContextContractError("target_sufficiency.context_ref must match target_context_ref")
    if target_sufficiency.status != "sufficient":
        raise TaskContextContractError("target_sufficiency must remain explicitly sufficient")
    if target_sufficiency.assessed_at != minimality.assessed_at:
        raise TaskContextContractError("target_sufficiency.assessed_at must match minimality.assessed_at")
    if target_sufficiency.trace_ref is not None:
        raise TaskContextContractError("target_sufficiency.trace_ref must be None for projection")
    if target_sufficiency.assessments != source_sufficiency.assessments:
        raise TaskContextContractError("target sufficiency must preserve source requirement assessments")
    if target_sufficiency.gaps != source_sufficiency.gaps:
        raise TaskContextContractError("target sufficiency must preserve source context gaps")

    retained = set(minimality.retained_requirement_ids)
    projected_values = {
        requirement_id: value
        for requirement_id, value in source_context.values.items()
        if requirement_id in retained
    }
    if set(projected_values) != retained:
        raise TaskContextContractError("retained IDs must all reference carried source values")

    lineage = _dedupe_texts(
        (
            *source_context.source_refs,
            source_context.context_ref,
            minimality.assessment_ref,
            minimality.method_ref,
            *minimality.source_refs,
            *(item.contribution_ref for item in minimality.contributions),
            *target_sufficiency.source_refs,
        )
    )
    projected = TaskContext(
        context_ref=minimality.target_context_ref,
        task_frame=source_context.task_frame,
        requirements=source_context.requirements,
        constructed_at=minimality.assessed_at,
        values=projected_values,
        source_refs=lineage,
        valid_until=target_sufficiency.valid_until,
        trace_ref=None,
    )
    return MinimumSufficientTaskContext(
        source_context_ref=source_context.context_ref,
        context=projected,
        sufficiency=target_sufficiency,
        minimality=minimality,
    )


def context_minimality_assessment_payload(assessment: ContextMinimalityAssessment) -> dict[str, object]:
    return {
        "contract": CONTEXT_MINIMALITY_ASSESSMENT_CONTRACT_ID,
        "contract_version": assessment.contract_version,
        "assessment_ref": assessment.assessment_ref,
        "source_context_ref": assessment.source_context_ref,
        "target_context_ref": assessment.target_context_ref,
        "method_ref": assessment.method_ref,
        "assessed_at": assessment.assessed_at,
        "status": assessment.status,
        "contributions": [
            {
                "contribution_ref": item.contribution_ref,
                "requirement_id": item.requirement_id,
                "status": item.status,
                "reason": item.reason,
                "cost": {
                    "acquisition_units": item.cost.acquisition_units,
                    "carried_bytes": item.cost.carried_bytes,
                    "llm_units": item.cost.llm_units,
                    "provider_latency_ms": item.cost.provider_latency_ms,
                    "human_recovery_units": item.cost.human_recovery_units,
                },
                "source_refs": list(item.source_refs),
            }
            for item in assessment.contributions
        ],
        "retained_requirement_ids": list(assessment.retained_requirement_ids),
        "removed_requirement_ids": list(assessment.removed_requirement_ids),
        "source_refs": list(assessment.source_refs),
    }


def minimum_sufficient_task_context_payload(result: MinimumSufficientTaskContext) -> dict[str, object]:
    return {
        "contract": MINIMUM_SUFFICIENT_TASK_CONTEXT_CONTRACT_ID,
        "contract_version": result.contract_version,
        "source_context_ref": result.source_context_ref,
        "context_ref": result.context.context_ref,
        "sufficiency_ref": result.sufficiency.assessment_ref,
        "minimality_ref": result.minimality.assessment_ref,
        "retained_requirement_ids": list(result.minimality.retained_requirement_ids),
        "removed_requirement_ids": list(result.minimality.removed_requirement_ids),
        "source_refs": list(result.context.source_refs),
    }


def _validate_minimality_result(
    method_ref: str,
    context: TaskContext,
    sufficiency: SufficiencyAssessment,
    result: ContextMinimalityAssessment,
    *,
    as_of: str,
) -> None:
    if result.source_context_ref != context.context_ref:
        raise TaskContextContractError("minimality source_context_ref must match context.context_ref")
    if result.method_ref != method_ref:
        raise TaskContextContractError("minimality method_ref must match method.method_ref")
    if result.assessed_at != as_of:
        raise TaskContextContractError("minimality assessed_at must equal explicit as_of")

    carried_ids = set(context.values)
    contribution_ids = {item.requirement_id for item in result.contributions}
    if contribution_ids != carried_ids:
        raise TaskContextContractError("contributions must cover carried TaskContext values exactly")
    retained = set(result.retained_requirement_ids)
    removed = set(result.removed_requirement_ids)
    if retained | removed != carried_ids:
        raise TaskContextContractError("retained and removed IDs must partition carried values")

    contribution_by_id = {item.requirement_id: item for item in result.contributions}
    for requirement_id in retained:
        if contribution_by_id[requirement_id].status == "removable":
            raise TaskContextContractError("removable contributions cannot remain retained")
    for requirement_id in removed:
        if contribution_by_id[requirement_id].status != "removable":
            raise TaskContextContractError("only explicitly removable contributions may be removed")

    requirement_by_id: dict[str, ContextRequirement] = {
        item.requirement_id: item for item in context.requirements
    }
    assessment_by_id = {item.requirement_id: item for item in sufficiency.assessments}
    critical_requirement_ids = {
        requirement_id
        for requirement_id, requirement in requirement_by_id.items()
        if requirement.critical
    }
    missing_source_values = sorted(critical_requirement_ids - carried_ids)
    if missing_source_values:
        raise TaskContextContractError(
            "sufficient source must carry each critical requirement value: "
            + ", ".join(missing_source_values)
        )
    missing_critical = sorted(critical_requirement_ids - retained)
    if missing_critical:
        raise TaskContextContractError(
            "critical carried context cannot be removed: " + ", ".join(missing_critical)
        )
    for requirement_id in critical_requirement_ids:
        assessment = assessment_by_id.get(requirement_id)
        if assessment is None or assessment.status != "satisfied":
            raise TaskContextContractError(
                "sufficient source must have satisfied assessment for each critical carried value"
            )
