"""Task-relative resolution adequacy contracts for GeoTask v2.1.

This module makes resolution adequacy an explicit, inspectable intermediate state
between candidate applicability and aggregate task-context sufficiency.

GeoTask Core does not hard-code domain thresholds here. A task/method supplies the
comparison policy and returns dimension-level evidence; Core validates reference
closure, deterministic aggregation, and wire safety only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Literal, Mapping, Protocol, Sequence, runtime_checkable

from geotask_core.v1.context_provider import (
    ContextCandidate,
    ResolutionRequirement,
)
from geotask_core.v1.task_context import (
    CONTEXT_CONTRACT_VERSION,
    JSONValue,
    TaskContextContractError,
)

RESOLUTION_ADEQUACY_RESULT_CONTRACT_ID = "geotask.resolution-adequacy-result"

ResolutionAdequacyStatus = Literal["adequate", "degraded", "inadequate", "unknown"]
RESOLUTION_ADEQUACY_STATUSES = frozenset({"adequate", "degraded", "inadequate", "unknown"})


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


def _freeze_json(value: object, name: str) -> JSONValue:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise TaskContextContractError(f"{name} must not contain non-finite numbers")
        return value
    if isinstance(value, Mapping):
        normalized: dict[str, JSONValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TaskContextContractError(f"{name} object keys must be strings")
            normalized[key] = _freeze_json(item, f"{name}.{key}")
        return MappingProxyType(normalized)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(_freeze_json(item, f"{name}[]") for item in value)
    raise TaskContextContractError(f"{name} must be JSON-compatible")


def _json_payload(value: JSONValue) -> object:
    if isinstance(value, Mapping):
        return {key: _json_payload(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_payload(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class ResolutionDimensionEvidence:
    """Evidence and conclusion for one declared resolution dimension.

    ``required`` mirrors the corresponding value in ``ResolutionRequirement``.
    ``observed`` is method-produced candidate evidence. Core does not interpret the
    units or threshold semantics of either value.
    """

    dimension: str
    status: ResolutionAdequacyStatus
    required: JSONValue
    observed: JSONValue
    reason: str
    source_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.dimension, "dimension")
        if self.status not in RESOLUTION_ADEQUACY_STATUSES:
            raise TaskContextContractError(
                "status must be one of: " + ", ".join(sorted(RESOLUTION_ADEQUACY_STATUSES))
            )
        object.__setattr__(self, "required", _freeze_json(self.required, "required"))
        object.__setattr__(self, "observed", _freeze_json(self.observed, "observed"))
        _require_text(self.reason, "reason")
        object.__setattr__(self, "source_refs", _unique_texts(self.source_refs, "source_refs"))


@dataclass(frozen=True, slots=True)
class ResolutionAdequacyResult:
    """GeoTask-owned task-relative resolution conclusion for one candidate.

    Adequacy is an intermediate context state only. Even ``status='adequate'`` does
    not imply that ``ContextAssessment`` is satisfied or that aggregate
    ``TaskContext`` is sufficient.
    """

    adequacy_ref: str
    resolution_ref: str
    requirement_id: str
    candidate_ref: str
    method_ref: str
    status: ResolutionAdequacyStatus
    assessed_at: str
    reason: str
    dimensions: tuple[ResolutionDimensionEvidence, ...]
    source_refs: tuple[str, ...] = ()
    contract_version: str = CONTEXT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _require_text(self.adequacy_ref, "adequacy_ref")
        _require_text(self.resolution_ref, "resolution_ref")
        _require_text(self.requirement_id, "requirement_id")
        _require_text(self.candidate_ref, "candidate_ref")
        _require_text(self.method_ref, "method_ref")
        if self.status not in RESOLUTION_ADEQUACY_STATUSES:
            raise TaskContextContractError(
                "status must be one of: " + ", ".join(sorted(RESOLUTION_ADEQUACY_STATUSES))
            )
        _require_timestamp(self.assessed_at, "assessed_at")
        _require_text(self.reason, "reason")
        if self.contract_version != CONTEXT_CONTRACT_VERSION:
            raise TaskContextContractError(
                f"contract_version must equal {CONTEXT_CONTRACT_VERSION!r}"
            )
        dimension_names = [item.dimension for item in self.dimensions]
        if len(dimension_names) != len(set(dimension_names)):
            raise TaskContextContractError("dimensions must have unique dimension names")
        object.__setattr__(self, "dimensions", tuple(self.dimensions))
        object.__setattr__(self, "source_refs", _unique_texts(self.source_refs, "source_refs"))


@runtime_checkable
class ResolutionAdequacyMethod(Protocol):
    """Method seam that keeps thresholds/policies outside GeoTask Core semantics."""

    @property
    def method_ref(self) -> str:
        """Stable method identity for replay and benchmark traceability."""
        ...

    def assess_resolution(
        self,
        requirement: ResolutionRequirement,
        candidate: ContextCandidate,
        *,
        as_of: str,
    ) -> ResolutionAdequacyResult:
        """Assess candidate resolution using task/method-supplied policy."""
        ...


def aggregate_resolution_adequacy_status(
    dimensions: Sequence[ResolutionDimensionEvidence],
) -> ResolutionAdequacyStatus:
    """Aggregate already-assessed dimensions without inventing domain thresholds.

    Known inadequacy is decisive. Otherwise unresolved dimensions remain unknown;
    degradation is preserved; only all-known-adequate dimensions yield adequate.
    An empty dimension set is unknown rather than fabricated adequacy.
    """
    if not dimensions:
        return "unknown"
    statuses = {item.status for item in dimensions}
    if "inadequate" in statuses:
        return "inadequate"
    if "unknown" in statuses:
        return "unknown"
    if "degraded" in statuses:
        return "degraded"
    return "adequate"


def validate_resolution_adequacy_result(
    requirement: ResolutionRequirement,
    candidate: ContextCandidate,
    result: ResolutionAdequacyResult,
    *,
    as_of: str | None = None,
    method_ref: str | None = None,
) -> None:
    """Validate reference closure and complete dimension-level evidence.

    The function deliberately does not compare thresholds itself. It verifies that
    every declared resolution dimension was assessed exactly once and that the
    result's overall status matches deterministic aggregation of those conclusions.
    """
    if candidate.requirement_id != requirement.requirement_id:
        raise TaskContextContractError(
            "candidate.requirement_id must match ResolutionRequirement.requirement_id"
        )

    if result.resolution_ref != requirement.resolution_ref:
        raise TaskContextContractError(
            "result.resolution_ref must match ResolutionRequirement.resolution_ref"
        )
    if result.requirement_id != requirement.requirement_id:
        raise TaskContextContractError(
            "result.requirement_id must match ResolutionRequirement.requirement_id"
        )
    if result.candidate_ref != candidate.candidate_ref:
        raise TaskContextContractError(
            "result.candidate_ref must match ContextCandidate.candidate_ref"
        )
    if as_of is not None and result.assessed_at != as_of:
        raise TaskContextContractError("result.assessed_at must equal the explicit assessment as_of")
    if method_ref is not None and result.method_ref != method_ref:
        raise TaskContextContractError("result.method_ref must match ResolutionAdequacyMethod.method_ref")

    evidence_by_dimension = {item.dimension: item for item in result.dimensions}
    expected_dimensions = set(requirement.dimensions)
    actual_dimensions = set(evidence_by_dimension)
    missing = sorted(expected_dimensions - actual_dimensions)
    extra = sorted(actual_dimensions - expected_dimensions)
    if missing or extra:
        details: list[str] = []
        if missing:
            details.append("missing=" + ",".join(missing))
        if extra:
            details.append("extra=" + ",".join(extra))
        raise TaskContextContractError(
            "resolution dimension evidence must exactly cover ResolutionRequirement.dimensions: "
            + "; ".join(details)
        )

    for dimension, required_value in requirement.dimensions.items():
        evidence = evidence_by_dimension[dimension]
        if evidence.required != required_value:
            raise TaskContextContractError(
                f"dimension {dimension!r} required value must match ResolutionRequirement.dimensions"
            )

    expected_status = aggregate_resolution_adequacy_status(result.dimensions)
    if result.status != expected_status:
        raise TaskContextContractError(
            f"result.status must equal aggregated dimension status {expected_status!r}"
        )


def assess_resolution_adequacy(
    method: ResolutionAdequacyMethod,
    requirement: ResolutionRequirement,
    candidate: ContextCandidate,
    *,
    as_of: str,
) -> ResolutionAdequacyResult:
    """Invoke an explicit method and validate its result without owning its thresholds."""
    _require_text(method.method_ref, "ResolutionAdequacyMethod.method_ref")
    _require_timestamp(as_of, "as_of")
    result = method.assess_resolution(requirement, candidate, as_of=as_of)
    validate_resolution_adequacy_result(
        requirement,
        candidate,
        result,
        as_of=as_of,
        method_ref=method.method_ref,
    )
    return result


def resolution_adequacy_result_payload(result: ResolutionAdequacyResult) -> dict[str, object]:
    """Serialize the stable resolution-adequacy wire contract."""
    return {
        "contract": RESOLUTION_ADEQUACY_RESULT_CONTRACT_ID,
        "contract_version": result.contract_version,
        "adequacy_ref": result.adequacy_ref,
        "resolution_ref": result.resolution_ref,
        "requirement_id": result.requirement_id,
        "candidate_ref": result.candidate_ref,
        "method_ref": result.method_ref,
        "status": result.status,
        "assessed_at": result.assessed_at,
        "reason": result.reason,
        "dimensions": [
            {
                "dimension": item.dimension,
                "status": item.status,
                "required": _json_payload(item.required),
                "observed": _json_payload(item.observed),
                "reason": item.reason,
                "source_refs": list(item.source_refs),
            }
            for item in result.dimensions
        ],
        "source_refs": list(result.source_refs),
    }
