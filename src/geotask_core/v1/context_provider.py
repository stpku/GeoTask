"""Provider/candidate contracts for the GeoTask v2.1 task-context plane.

This module defines only the acquisition seam between an explicit GeoTask
``ContextRequirement`` and external candidate information. It does not discover
providers, rank candidates, resolve world truth, assess task sufficiency, or
construct a final ``TaskContext``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Literal, Mapping, Protocol, Sequence, runtime_checkable

from geotask_core.v1.task_context import (
    CONTEXT_CONTRACT_VERSION,
    ContextRequirement,
    JSONValue,
    TaskContextContractError,
    TaskFrame,
)

CONTEXT_CANDIDATE_CONTRACT_ID = "geotask.context-candidate"
RELEVANCE_RESULT_CONTRACT_ID = "geotask.relevance-result"
APPLICABILITY_RESULT_CONTRACT_ID = "geotask.applicability-result"
RESOLUTION_REQUIREMENT_CONTRACT_ID = "geotask.resolution-requirement"

RelevanceStatus = Literal["relevant", "not_relevant", "unknown"]
ApplicabilityStatus = Literal["applicable", "not_applicable", "unknown"]
RELEVANCE_STATUSES = frozenset({"relevant", "not_relevant", "unknown"})
APPLICABILITY_STATUSES = frozenset({"applicable", "not_applicable", "unknown"})


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


def _freeze_mapping(value: Mapping[str, object], name: str) -> Mapping[str, JSONValue]:
    frozen = _freeze_json(value, name)
    assert isinstance(frozen, Mapping)
    return frozen


def _json_payload(value: JSONValue) -> object:
    if isinstance(value, Mapping):
        return {key: _json_payload(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_payload(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class ContextCandidate:
    """Provider-owned candidate information for one explicit requirement.

    ``payload`` is intentionally opaque to GeoTask Core. A WorldState provider,
    database adapter, API, or another source may retain its own truth/status
    vocabulary inside the payload. Candidate existence does not imply relevance,
    applicability, adequate resolution, or task sufficiency.
    """

    candidate_ref: str
    requirement_id: str
    provider_ref: str
    payload: JSONValue
    source_refs: tuple[str, ...] = ()
    metadata: Mapping[str, JSONValue] = field(default_factory=dict)
    contract_version: str = CONTEXT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _require_text(self.candidate_ref, "candidate_ref")
        _require_text(self.requirement_id, "requirement_id")
        _require_text(self.provider_ref, "provider_ref")
        if self.contract_version != CONTEXT_CONTRACT_VERSION:
            raise TaskContextContractError(
                f"contract_version must equal {CONTEXT_CONTRACT_VERSION!r}"
            )
        object.__setattr__(self, "payload", _freeze_json(self.payload, "payload"))
        object.__setattr__(self, "source_refs", _unique_texts(self.source_refs, "source_refs"))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True)
class RelevanceResult:
    """GeoTask-owned relevance conclusion for one candidate and requirement.

    Relevance answers whether the candidate concerns the current task need. It is
    intentionally separate from applicability: a relevant fact may still be out
    of date, outside spatial scope, or otherwise not applicable to the task.
    """

    relevance_ref: str
    requirement_id: str
    candidate_ref: str
    status: RelevanceStatus
    assessed_at: str
    reason: str
    source_refs: tuple[str, ...] = ()
    contract_version: str = CONTEXT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _require_text(self.relevance_ref, "relevance_ref")
        _require_text(self.requirement_id, "requirement_id")
        _require_text(self.candidate_ref, "candidate_ref")
        if self.status not in RELEVANCE_STATUSES:
            raise TaskContextContractError(
                "status must be one of: " + ", ".join(sorted(RELEVANCE_STATUSES))
            )
        _require_timestamp(self.assessed_at, "assessed_at")
        _require_text(self.reason, "reason")
        if self.contract_version != CONTEXT_CONTRACT_VERSION:
            raise TaskContextContractError(
                f"contract_version must equal {CONTEXT_CONTRACT_VERSION!r}"
            )
        object.__setattr__(self, "source_refs", _unique_texts(self.source_refs, "source_refs"))


@dataclass(frozen=True, slots=True)
class ApplicabilityResult:
    """GeoTask-owned applicability conclusion for one provider candidate.

    Applicability is task-relative and therefore belongs to GeoTask. It does not
    rewrite or validate the provider-owned truth carried by ``ContextCandidate``.
    """

    applicability_ref: str
    requirement_id: str
    candidate_ref: str
    status: ApplicabilityStatus
    assessed_at: str
    reason: str
    source_refs: tuple[str, ...] = ()
    contract_version: str = CONTEXT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _require_text(self.applicability_ref, "applicability_ref")
        _require_text(self.requirement_id, "requirement_id")
        _require_text(self.candidate_ref, "candidate_ref")
        if self.status not in APPLICABILITY_STATUSES:
            raise TaskContextContractError(
                "status must be one of: " + ", ".join(sorted(APPLICABILITY_STATUSES))
            )
        _require_timestamp(self.assessed_at, "assessed_at")
        _require_text(self.reason, "reason")
        if self.contract_version != CONTEXT_CONTRACT_VERSION:
            raise TaskContextContractError(
                f"contract_version must equal {CONTEXT_CONTRACT_VERSION!r}"
            )
        object.__setattr__(self, "source_refs", _unique_texts(self.source_refs, "source_refs"))


@dataclass(frozen=True, slots=True)
class ResolutionRequirement:
    """Explicit task-relative resolution requirement for one context need.

    ``dimensions`` stays domain-neutral and may describe spatial, temporal,
    semantic, precision, field-coverage, or other resolution constraints. This
    object states what resolution is required; it does not judge a candidate.
    """

    resolution_ref: str
    requirement_id: str
    critical: bool
    dimensions: Mapping[str, JSONValue]
    reason: str
    source_refs: tuple[str, ...] = ()
    contract_version: str = CONTEXT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _require_text(self.resolution_ref, "resolution_ref")
        _require_text(self.requirement_id, "requirement_id")
        if not isinstance(self.critical, bool):
            raise TaskContextContractError("critical must be boolean")
        object.__setattr__(self, "dimensions", _freeze_mapping(self.dimensions, "dimensions"))
        _require_text(self.reason, "reason")
        object.__setattr__(self, "source_refs", _unique_texts(self.source_refs, "source_refs"))
        if self.contract_version != CONTEXT_CONTRACT_VERSION:
            raise TaskContextContractError(
                f"contract_version must equal {CONTEXT_CONTRACT_VERSION!r}"
            )


@runtime_checkable
class ContextProvider(Protocol):
    """Harness-neutral candidate acquisition seam.

    Callers supply both the task and an already-derived requirement. Providers
    return candidate information only. They do not derive requirements or emit a
    ``SufficiencyAssessment`` as part of this protocol.
    """

    @property
    def provider_ref(self) -> str:
        """Stable provider identity/reference used for lineage and conformance."""
        ...

    def get_candidates(
        self,
        task_frame: TaskFrame,
        requirement: ContextRequirement,
        *,
        as_of: str,
    ) -> tuple[ContextCandidate, ...]:
        """Return candidates for one explicit requirement at an explicit time."""
        ...


def validate_candidate_binding(
    candidate: ContextCandidate,
    requirement: ContextRequirement,
) -> None:
    """Validate reference closure without judging candidate suitability."""
    if candidate.requirement_id != requirement.requirement_id:
        raise TaskContextContractError(
            "candidate.requirement_id must match ContextRequirement.requirement_id"
        )


def validate_provider_candidates(
    provider: ContextProvider,
    requirement: ContextRequirement,
    candidates: Sequence[ContextCandidate],
) -> None:
    """Validate provider identity and candidate reference closure only."""
    _require_text(provider.provider_ref, "provider.provider_ref")
    candidate_refs: set[str] = set()
    for candidate in candidates:
        validate_candidate_binding(candidate, requirement)
        if candidate.provider_ref != provider.provider_ref:
            raise TaskContextContractError(
                "candidate.provider_ref must match ContextProvider.provider_ref"
            )
        if candidate.candidate_ref in candidate_refs:
            raise TaskContextContractError("provider candidates must have unique candidate_ref values")
        candidate_refs.add(candidate.candidate_ref)


def context_candidate_payload(candidate: ContextCandidate) -> dict[str, object]:
    """Serialize the stable candidate wire contract."""
    return {
        "contract": CONTEXT_CANDIDATE_CONTRACT_ID,
        "contract_version": candidate.contract_version,
        "candidate_ref": candidate.candidate_ref,
        "requirement_id": candidate.requirement_id,
        "provider_ref": candidate.provider_ref,
        "payload": _json_payload(candidate.payload),
        "source_refs": list(candidate.source_refs),
        "metadata": _json_payload(candidate.metadata),
    }


def relevance_result_payload(result: RelevanceResult) -> dict[str, object]:
    """Serialize the stable relevance-result wire contract."""
    return {
        "contract": RELEVANCE_RESULT_CONTRACT_ID,
        "contract_version": result.contract_version,
        "relevance_ref": result.relevance_ref,
        "requirement_id": result.requirement_id,
        "candidate_ref": result.candidate_ref,
        "status": result.status,
        "assessed_at": result.assessed_at,
        "reason": result.reason,
        "source_refs": list(result.source_refs),
    }


def applicability_result_payload(result: ApplicabilityResult) -> dict[str, object]:
    """Serialize the stable applicability-result wire contract."""
    return {
        "contract": APPLICABILITY_RESULT_CONTRACT_ID,
        "contract_version": result.contract_version,
        "applicability_ref": result.applicability_ref,
        "requirement_id": result.requirement_id,
        "candidate_ref": result.candidate_ref,
        "status": result.status,
        "assessed_at": result.assessed_at,
        "reason": result.reason,
        "source_refs": list(result.source_refs),
    }


def validate_relevance_applicability_pair(
    relevance: RelevanceResult,
    applicability: ApplicabilityResult,
) -> None:
    """Validate shared candidate references without coupling the conclusions.

    ``relevant`` + ``not_applicable`` is valid: the candidate concerns the task
    need but cannot be used for the current task scope/time/resolution.
    """
    if relevance.requirement_id != applicability.requirement_id:
        raise TaskContextContractError(
            "relevance.requirement_id must match applicability.requirement_id"
        )
    if relevance.candidate_ref != applicability.candidate_ref:
        raise TaskContextContractError(
            "relevance.candidate_ref must match applicability.candidate_ref"
        )
    if relevance.assessed_at != applicability.assessed_at:
        raise TaskContextContractError(
            "relevance.assessed_at must match applicability.assessed_at"
        )


def resolution_requirement_payload(requirement: ResolutionRequirement) -> dict[str, object]:
    """Serialize the stable resolution-requirement wire contract."""
    return {
        "contract": RESOLUTION_REQUIREMENT_CONTRACT_ID,
        "contract_version": requirement.contract_version,
        "resolution_ref": requirement.resolution_ref,
        "requirement_id": requirement.requirement_id,
        "critical": requirement.critical,
        "dimensions": _json_payload(requirement.dimensions),
        "reason": requirement.reason,
        "source_refs": list(requirement.source_refs),
    }
