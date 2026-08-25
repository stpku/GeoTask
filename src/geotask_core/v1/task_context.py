"""Harness-neutral GeoTask task-context contracts for Stack v2.1.

This module owns only the *task-context* semantic surface: what the task
requires, which context was selected, explicit gaps, and GeoTask's explicit
sufficiency conclusion. It does not resolve world truth, run an Agent, perform
domain assessment, or infer sufficiency from legacy runtime containers.

The contracts are additive. Existing ``geotask_runtime.TaskContext`` remains a
legacy runtime container and is intentionally not imported or upgraded here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import math
from types import MappingProxyType
from typing import Literal, Mapping, Sequence, TypeAlias

JSONScalar: TypeAlias = None | bool | int | float | str
JSONValue: TypeAlias = JSONScalar | tuple["JSONValue", ...] | Mapping[str, "JSONValue"]

CONTEXT_CONTRACT_VERSION = "0.1"
TASK_CONTEXT_CONTRACT_ID = "geotask.task-context"
SUFFICIENCY_ASSESSMENT_CONTRACT_ID = "geotask.sufficiency-assessment"
CONTEXT_CONSTRUCTION_TRACE_CONTRACT_ID = "geotask.context-construction-trace"

ContextAssessmentStatus: TypeAlias = Literal[
    "satisfied",
    "degraded",
    "insufficient",
    "blocked",
    "unknown",
    "not_applicable",
]
SufficiencyStatus: TypeAlias = Literal[
    "sufficient",
    "degraded",
    "insufficient",
    "blocked",
    "unknown",
]

CONTEXT_ASSESSMENT_STATUSES = frozenset(
    {"satisfied", "degraded", "insufficient", "blocked", "unknown", "not_applicable"}
)
SUFFICIENCY_STATUSES = frozenset(
    {"sufficient", "degraded", "insufficient", "blocked", "unknown"}
)


class TaskContextContractError(ValueError):
    """Raised when a task-context contract violates deterministic invariants."""


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
    """Return ordinary dict/list containers suitable for json.dumps()."""
    if isinstance(value, Mapping):
        return {key: _json_payload(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_payload(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class TaskFrame:
    """Stable task identity and scope used to derive context requirements."""

    task_id: str
    task_type: str
    goal: str
    scope_refs: tuple[str, ...] = ()
    metadata: Mapping[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_text(self.task_id, "task_id")
        _require_text(self.task_type, "task_type")
        _require_text(self.goal, "goal")
        object.__setattr__(self, "scope_refs", _unique_texts(self.scope_refs, "scope_refs"))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True)
class ContextRequirement:
    """One explicit statement of context the task requires.

    ``constraints`` is deliberately domain-neutral. A domain adapter may express
    spatial/temporal resolution, applicability, required fields, or other
    machine-readable requirements without moving those domain vocabularies into
    GeoTask Core.
    """

    requirement_id: str
    kind: str
    description: str
    critical: bool
    constraints: Mapping[str, JSONValue] = field(default_factory=dict)
    scope_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.requirement_id, "requirement_id")
        _require_text(self.kind, "kind")
        _require_text(self.description, "description")
        if not isinstance(self.critical, bool):
            raise TaskContextContractError("critical must be boolean")
        object.__setattr__(
            self, "constraints", _freeze_mapping(self.constraints, "constraints")
        )
        object.__setattr__(self, "scope_refs", _unique_texts(self.scope_refs, "scope_refs"))


@dataclass(frozen=True, slots=True)
class ContextAssessment:
    """GeoTask-owned assessment for one ContextRequirement."""

    requirement_id: str
    critical: bool
    status: ContextAssessmentStatus
    assessed_at: str
    reason: str
    source_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.requirement_id, "requirement_id")
        if not isinstance(self.critical, bool):
            raise TaskContextContractError("critical must be boolean")
        if self.status not in CONTEXT_ASSESSMENT_STATUSES:
            raise TaskContextContractError(
                "status must be one of: " + ", ".join(sorted(CONTEXT_ASSESSMENT_STATUSES))
            )
        _require_timestamp(self.assessed_at, "assessed_at")
        _require_text(self.reason, "reason")
        object.__setattr__(self, "source_refs", _unique_texts(self.source_refs, "source_refs"))


@dataclass(frozen=True, slots=True)
class ContextGap:
    """Explicit missing/insufficient context; never equivalent to False."""

    gap_id: str
    requirement_id: str
    critical: bool
    reason: str
    recoverable: bool
    source_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.gap_id, "gap_id")
        _require_text(self.requirement_id, "requirement_id")
        if not isinstance(self.critical, bool):
            raise TaskContextContractError("critical must be boolean")
        _require_text(self.reason, "reason")
        if not isinstance(self.recoverable, bool):
            raise TaskContextContractError("recoverable must be boolean")
        object.__setattr__(self, "source_refs", _unique_texts(self.source_refs, "source_refs"))


@dataclass(frozen=True, slots=True)
class TaskContext:
    """Versioned, provider-referenced context selected for one TaskFrame.

    Values are keyed by ``requirement_id``. Their truth remains owned by their
    providers; ``source_refs`` preserves provider lineage for replay.
    """

    context_ref: str
    task_frame: TaskFrame
    requirements: tuple[ContextRequirement, ...]
    constructed_at: str
    values: Mapping[str, JSONValue] = field(default_factory=dict)
    source_refs: tuple[str, ...] = ()
    valid_until: str | None = None
    trace_ref: str | None = None
    contract_version: str = CONTEXT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _require_text(self.context_ref, "context_ref")
        _require_timestamp(self.constructed_at, "constructed_at")
        if self.valid_until is not None:
            constructed = _require_timestamp(self.constructed_at, "constructed_at")
            valid_until = _require_timestamp(self.valid_until, "valid_until")
            if valid_until < constructed:
                raise TaskContextContractError("valid_until must not be earlier than constructed_at")
        if self.trace_ref is not None:
            _require_text(self.trace_ref, "trace_ref")
        if self.contract_version != CONTEXT_CONTRACT_VERSION:
            raise TaskContextContractError(
                f"contract_version must equal {CONTEXT_CONTRACT_VERSION!r}"
            )

        requirement_ids = [item.requirement_id for item in self.requirements]
        if len(requirement_ids) != len(set(requirement_ids)):
            raise TaskContextContractError("requirements must have unique requirement_id values")

        frozen_values = _freeze_mapping(self.values, "values")
        unknown_value_keys = sorted(set(frozen_values) - set(requirement_ids))
        if unknown_value_keys:
            raise TaskContextContractError(
                "values reference undeclared requirements: " + ", ".join(unknown_value_keys)
            )
        object.__setattr__(self, "values", frozen_values)
        object.__setattr__(self, "source_refs", _unique_texts(self.source_refs, "source_refs"))


@dataclass(frozen=True, slots=True)
class ContextConstructionTrace:
    """Replay-oriented trace of a TaskContext construction decision."""

    trace_ref: str
    context_ref: str
    constructed_at: str
    requirement_ids: tuple[str, ...]
    selected_requirement_ids: tuple[str, ...]
    gap_refs: tuple[str, ...]
    source_refs: tuple[str, ...]
    method: str
    version: str

    def __post_init__(self) -> None:
        _require_text(self.trace_ref, "trace_ref")
        _require_text(self.context_ref, "context_ref")
        _require_timestamp(self.constructed_at, "constructed_at")
        object.__setattr__(
            self, "requirement_ids", _unique_texts(self.requirement_ids, "requirement_ids")
        )
        object.__setattr__(
            self,
            "selected_requirement_ids",
            _unique_texts(self.selected_requirement_ids, "selected_requirement_ids"),
        )
        undeclared = sorted(set(self.selected_requirement_ids) - set(self.requirement_ids))
        if undeclared:
            raise TaskContextContractError(
                "selected_requirement_ids reference undeclared requirements: "
                + ", ".join(undeclared)
            )
        object.__setattr__(self, "gap_refs", _unique_texts(self.gap_refs, "gap_refs"))
        object.__setattr__(self, "source_refs", _unique_texts(self.source_refs, "source_refs"))
        _require_text(self.method, "method")
        _require_text(self.version, "version")


@dataclass(frozen=True, slots=True)
class SufficiencyAssessment:
    """Explicit GeoTask-owned aggregate conclusion for one TaskContext.

    Consumers such as AgentReality may map ``status`` but must not derive a new
    sufficiency conclusion from the gap list or context payload.
    """

    assessment_ref: str
    context_ref: str
    assessed_at: str
    status: SufficiencyStatus
    assessments: tuple[ContextAssessment, ...]
    gaps: tuple[ContextGap, ...]
    source_refs: tuple[str, ...] = ()
    valid_until: str | None = None
    trace_ref: str | None = None
    contract_version: str = CONTEXT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _require_text(self.assessment_ref, "assessment_ref")
        _require_text(self.context_ref, "context_ref")
        assessed = _require_timestamp(self.assessed_at, "assessed_at")
        if self.status not in SUFFICIENCY_STATUSES:
            raise TaskContextContractError(
                "status must be one of: " + ", ".join(sorted(SUFFICIENCY_STATUSES))
            )
        if self.valid_until is not None:
            valid_until = _require_timestamp(self.valid_until, "valid_until")
            if valid_until < assessed:
                raise TaskContextContractError("valid_until must not be earlier than assessed_at")
        if self.trace_ref is not None:
            _require_text(self.trace_ref, "trace_ref")
        if self.contract_version != CONTEXT_CONTRACT_VERSION:
            raise TaskContextContractError(
                f"contract_version must equal {CONTEXT_CONTRACT_VERSION!r}"
            )

        assessment_ids = [item.requirement_id for item in self.assessments]
        if len(assessment_ids) != len(set(assessment_ids)):
            raise TaskContextContractError(
                "assessments must contain at most one result per requirement_id"
            )
        gap_ids = [item.gap_id for item in self.gaps]
        if len(gap_ids) != len(set(gap_ids)):
            raise TaskContextContractError("gaps must have unique gap_id values")

        if self.status == "sufficient":
            critical_non_satisfied = [
                item.requirement_id
                for item in self.assessments
                if item.critical and item.status != "satisfied"
            ]
            critical_gaps = [item.gap_id for item in self.gaps if item.critical]
            if critical_non_satisfied or critical_gaps:
                raise TaskContextContractError(
                    "sufficient cannot coexist with unsatisfied critical requirements or critical gaps"
                )

        object.__setattr__(self, "source_refs", _unique_texts(self.source_refs, "source_refs"))


def task_context_payload(context: TaskContext) -> dict[str, object]:
    """Serialize the stable v0.1 TaskContext wire contract."""
    return {
        "contract": TASK_CONTEXT_CONTRACT_ID,
        "contract_version": context.contract_version,
        "context_ref": context.context_ref,
        "task_frame": {
            "task_id": context.task_frame.task_id,
            "task_type": context.task_frame.task_type,
            "goal": context.task_frame.goal,
            "scope_refs": list(context.task_frame.scope_refs),
            "metadata": _json_payload(context.task_frame.metadata),
        },
        "requirements": [
            {
                "requirement_id": item.requirement_id,
                "kind": item.kind,
                "description": item.description,
                "critical": item.critical,
                "constraints": _json_payload(item.constraints),
                "scope_refs": list(item.scope_refs),
            }
            for item in context.requirements
        ],
        "constructed_at": context.constructed_at,
        "valid_until": context.valid_until,
        "values": _json_payload(context.values),
        "source_refs": list(context.source_refs),
        "trace_ref": context.trace_ref,
    }


def sufficiency_assessment_payload(assessment: SufficiencyAssessment) -> dict[str, object]:
    """Serialize the stable v0.1 SufficiencyAssessment wire contract."""
    return {
        "contract": SUFFICIENCY_ASSESSMENT_CONTRACT_ID,
        "contract_version": assessment.contract_version,
        "assessment_ref": assessment.assessment_ref,
        "context_ref": assessment.context_ref,
        "assessed_at": assessment.assessed_at,
        "valid_until": assessment.valid_until,
        "status": assessment.status,
        "assessments": [
            {
                "requirement_id": item.requirement_id,
                "critical": item.critical,
                "status": item.status,
                "assessed_at": item.assessed_at,
                "reason": item.reason,
                "source_refs": list(item.source_refs),
            }
            for item in assessment.assessments
        ],
        "gaps": [
            {
                "gap_id": item.gap_id,
                "requirement_id": item.requirement_id,
                "critical": item.critical,
                "reason": item.reason,
                "recoverable": item.recoverable,
                "source_refs": list(item.source_refs),
            }
            for item in assessment.gaps
        ],
        "source_refs": list(assessment.source_refs),
        "trace_ref": assessment.trace_ref,
    }


def context_construction_trace_payload(trace: ContextConstructionTrace) -> dict[str, object]:
    """Serialize the stable v0.1 ContextConstructionTrace wire contract."""
    return {
        "contract": CONTEXT_CONSTRUCTION_TRACE_CONTRACT_ID,
        "contract_version": CONTEXT_CONTRACT_VERSION,
        "trace_ref": trace.trace_ref,
        "context_ref": trace.context_ref,
        "constructed_at": trace.constructed_at,
        "requirement_ids": list(trace.requirement_ids),
        "selected_requirement_ids": list(trace.selected_requirement_ids),
        "gap_refs": list(trace.gap_refs),
        "source_refs": list(trace.source_refs),
        "method": trace.method,
        "version": trace.version,
    }


def validate_context_bundle(
    context: TaskContext,
    sufficiency: SufficiencyAssessment,
    trace: ContextConstructionTrace | None = None,
) -> None:
    """Validate cross-object reference closure without recomputing sufficiency."""

    if sufficiency.context_ref != context.context_ref:
        raise TaskContextContractError("sufficiency.context_ref must match context.context_ref")

    requirement_by_id = {item.requirement_id: item for item in context.requirements}
    for assessment in sufficiency.assessments:
        requirement = requirement_by_id.get(assessment.requirement_id)
        if requirement is None:
            raise TaskContextContractError(
                f"assessment references undeclared requirement {assessment.requirement_id!r}"
            )
        if assessment.critical != requirement.critical:
            raise TaskContextContractError(
                f"assessment criticality differs from requirement {assessment.requirement_id!r}"
            )

    for gap in sufficiency.gaps:
        requirement = requirement_by_id.get(gap.requirement_id)
        if requirement is None:
            raise TaskContextContractError(
                f"gap references undeclared requirement {gap.requirement_id!r}"
            )
        if gap.critical != requirement.critical:
            raise TaskContextContractError(
                f"gap criticality differs from requirement {gap.requirement_id!r}"
            )

    if trace is None:
        if context.trace_ref is not None or sufficiency.trace_ref is not None:
            raise TaskContextContractError("referenced ContextConstructionTrace was not supplied")
        return

    if trace.context_ref != context.context_ref:
        raise TaskContextContractError("trace.context_ref must match context.context_ref")
    if context.trace_ref != trace.trace_ref:
        raise TaskContextContractError("context.trace_ref must match trace.trace_ref")
    if sufficiency.trace_ref != trace.trace_ref:
        raise TaskContextContractError("sufficiency.trace_ref must match trace.trace_ref")

    declared_ids = tuple(item.requirement_id for item in context.requirements)
    if set(trace.requirement_ids) != set(declared_ids):
        raise TaskContextContractError("trace.requirement_ids must cover context requirements exactly")
    if set(trace.selected_requirement_ids) != set(context.values):
        raise TaskContextContractError(
            "trace.selected_requirement_ids must match TaskContext value keys"
        )
    if set(trace.gap_refs) != {gap.gap_id for gap in sufficiency.gaps}:
        raise TaskContextContractError("trace.gap_refs must match SufficiencyAssessment gaps")
