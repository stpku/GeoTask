"""Minimal task-context contracts for GeoTask.

This module is the first additive engineering slice for the Task Context Engine
architecture direction. It deliberately does *not* discover context, infer
source authority, or make domain decisions. Callers declare a task frame,
context requirements, and candidate context items; Core performs explicit,
deterministic scope/resolution/sufficiency checks.

The module is intentionally dependency-free so it can remain a lightweight
part of GeoTask Core.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence


TASK_CONTEXT_STATUSES = {
    "sufficient",
    "sufficient_with_gaps",
    "insufficient",
    "over_budget",
}


def _require_nonempty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_nonnegative(value: float | None, field_name: str) -> None:
    if value is not None and value < 0:
        raise ValueError(f"{field_name} must be >= 0 when provided")


def _require_unique(values: Sequence[str], field_name: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must not contain duplicate ids")


@dataclass(frozen=True)
class TaskFrame:
    """Bounded physical-world task before context selection.

    ``spatial_scope`` and ``temporal_scope`` are explicit caller-declared
    references. Core v0.1 does not infer containment or overlap between scope
    identifiers. Domain packs may bind these references to richer geometry or
    temporal objects.

    ``context_budget`` is optional. When supplied, ``context_budget_unit`` is
    mandatory and selected candidates with non-zero acquisition cost must use
    the same unit. Core never converts cost units.
    """

    task_id: str
    goal: str
    subject_refs: tuple[str, ...] = ()
    spatial_scope: str | None = None
    temporal_scope: str | None = None
    outputs: tuple[str, ...] = ()
    context_budget: float | None = None
    context_budget_unit: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty(self.task_id, "task_id")
        _require_nonempty(self.goal, "goal")
        _require_unique(self.subject_refs, "subject_refs")
        _require_unique(self.outputs, "outputs")
        _require_nonnegative(self.context_budget, "context_budget")
        if self.context_budget is not None:
            if self.context_budget_unit is None:
                raise ValueError(
                    "context_budget_unit is required when context_budget is provided"
                )
            _require_nonempty(self.context_budget_unit, "context_budget_unit")
        elif self.context_budget_unit is not None:
            raise ValueError(
                "context_budget_unit must be omitted when context_budget is not provided"
            )


@dataclass(frozen=True)
class ContextRequirement:
    """One explicit piece of context required by a task.

    Spatial resolution values use a "smaller is finer" convention and must
    carry an explicit unit. Temporal resolution is expressed in seconds.
    Core performs no unit conversion.
    """

    requirement_id: str
    what: str
    reason: str
    critical: bool = True
    spatial_scope: str | None = None
    temporal_scope: str | None = None
    max_spatial_resolution: float | None = None
    spatial_resolution_unit: str | None = None
    max_temporal_resolution_seconds: float | None = None
    tolerance: float | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_nonempty(self.requirement_id, "requirement_id")
        _require_nonempty(self.what, "what")
        _require_nonempty(self.reason, "reason")
        _require_nonnegative(
            self.max_spatial_resolution, "max_spatial_resolution"
        )
        _require_nonnegative(
            self.max_temporal_resolution_seconds,
            "max_temporal_resolution_seconds",
        )
        _require_nonnegative(self.tolerance, "tolerance")
        if self.max_spatial_resolution is not None:
            if self.spatial_resolution_unit is None:
                raise ValueError(
                    "spatial_resolution_unit is required when "
                    "max_spatial_resolution is provided"
                )
            _require_nonempty(
                self.spatial_resolution_unit, "spatial_resolution_unit"
            )
        elif self.spatial_resolution_unit is not None:
            raise ValueError(
                "spatial_resolution_unit must be omitted when "
                "max_spatial_resolution is not provided"
            )


@dataclass(frozen=True)
class ContextCandidate:
    """One available context item proposed for the current task.

    ``requirement_ids`` is an explicit relevance binding supplied by the
    caller/provider. GeoTask Core does not infer relevance from text or source
    names in this first slice.

    Spatial resolution and acquisition cost must carry explicit units whenever
    they are non-null/non-zero. Core does not silently convert units.
    """

    candidate_id: str
    source: str
    requirement_ids: tuple[str, ...]
    spatial_scope: str | None = None
    temporal_scope: str | None = None
    spatial_resolution: float | None = None
    spatial_resolution_unit: str | None = None
    temporal_resolution_seconds: float | None = None
    acquisition_cost: float = 0.0
    cost_unit: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_nonempty(self.candidate_id, "candidate_id")
        _require_nonempty(self.source, "source")
        if not self.requirement_ids:
            raise ValueError("requirement_ids must contain at least one id")
        _require_unique(self.requirement_ids, "requirement_ids")
        _require_nonnegative(self.spatial_resolution, "spatial_resolution")
        _require_nonnegative(
            self.temporal_resolution_seconds, "temporal_resolution_seconds"
        )
        _require_nonnegative(self.acquisition_cost, "acquisition_cost")

        if self.spatial_resolution is not None:
            if self.spatial_resolution_unit is None:
                raise ValueError(
                    "spatial_resolution_unit is required when spatial_resolution "
                    "is provided"
                )
            _require_nonempty(
                self.spatial_resolution_unit, "spatial_resolution_unit"
            )
        elif self.spatial_resolution_unit is not None:
            raise ValueError(
                "spatial_resolution_unit must be omitted when spatial_resolution "
                "is not provided"
            )

        if self.acquisition_cost > 0:
            if self.cost_unit is None:
                raise ValueError(
                    "cost_unit is required when acquisition_cost is greater than 0"
                )
            _require_nonempty(self.cost_unit, "cost_unit")
        elif self.cost_unit is not None:
            _require_nonempty(self.cost_unit, "cost_unit")


@dataclass(frozen=True)
class CandidateContextAssessment:
    """Deterministic assessment of one candidate against one requirement."""

    requirement_id: str
    candidate_id: str
    relevant: bool
    applicable: bool
    resolution_sufficient: bool
    usable: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class ContextCoverage:
    """Usable candidate ids covering one requirement."""

    requirement_id: str
    candidate_ids: tuple[str, ...]


@dataclass(frozen=True)
class TaskContext:
    """Assessment result for a caller-selected bounded task context."""

    task_id: str
    status: str
    selected_candidate_ids: tuple[str, ...]
    coverage: tuple[ContextCoverage, ...]
    gap_requirement_ids: tuple[str, ...]
    refinement_requirement_ids: tuple[str, ...]
    total_acquisition_cost: float
    cost_unit: str | None
    budget_exceeded: bool

    def __post_init__(self) -> None:
        if self.status not in TASK_CONTEXT_STATUSES:
            raise ValueError(f"unsupported task context status: {self.status}")

    @property
    def sufficient(self) -> bool:
        """Whether all critical information requirements are covered.

        Budget is intentionally orthogonal: a context can be informationally
        sufficient and still be too expensive for the declared task budget.
        """

        return self.status != "insufficient"

    @property
    def within_budget(self) -> bool:
        """Whether declared acquisition cost is within the task budget."""

        return not self.budget_exceeded

    @property
    def ready(self) -> bool:
        """Whether the context is both informationally sufficient and affordable."""

        return self.sufficient and self.within_budget


def evaluate_context_candidate(
    task: TaskFrame,
    requirement: ContextRequirement,
    candidate: ContextCandidate,
) -> CandidateContextAssessment:
    """Evaluate explicit relevance, applicability, and resolution.

    The function intentionally uses exact scope-reference matching. It never
    assumes that two differently named spatial/temporal scopes overlap or that
    one contains the other. Rich scope reasoning belongs in a declared
    operator/domain pack and can feed normalized scope references into this
    baseline contract.
    """

    # ``task`` is part of the public assessment signature because future
    # declared task/scope operators may use it. The v0.1 baseline deliberately
    # avoids inferring relationships between opaque scope identifiers.
    _ = task

    reasons: list[str] = []

    relevant = requirement.requirement_id in candidate.requirement_ids
    if not relevant:
        reasons.append("requirement_not_declared")

    applicable = relevant
    if applicable and requirement.spatial_scope is not None:
        if candidate.spatial_scope != requirement.spatial_scope:
            applicable = False
            reasons.append("spatial_scope_mismatch")

    if applicable and requirement.temporal_scope is not None:
        if candidate.temporal_scope != requirement.temporal_scope:
            applicable = False
            reasons.append("temporal_scope_mismatch")

    resolution_sufficient = applicable
    if applicable and requirement.max_spatial_resolution is not None:
        if candidate.spatial_resolution is None:
            resolution_sufficient = False
            reasons.append("spatial_resolution_unknown")
        elif candidate.spatial_resolution_unit != requirement.spatial_resolution_unit:
            resolution_sufficient = False
            reasons.append("spatial_resolution_unit_mismatch")
        elif candidate.spatial_resolution > requirement.max_spatial_resolution:
            resolution_sufficient = False
            reasons.append("spatial_resolution_too_coarse")

    if applicable and requirement.max_temporal_resolution_seconds is not None:
        if candidate.temporal_resolution_seconds is None:
            resolution_sufficient = False
            reasons.append("temporal_resolution_unknown")
        elif (
            candidate.temporal_resolution_seconds
            > requirement.max_temporal_resolution_seconds
        ):
            resolution_sufficient = False
            reasons.append("temporal_resolution_too_coarse")

    return CandidateContextAssessment(
        requirement_id=requirement.requirement_id,
        candidate_id=candidate.candidate_id,
        relevant=relevant,
        applicable=applicable,
        resolution_sufficient=resolution_sufficient,
        usable=applicable and resolution_sufficient,
        reasons=tuple(reasons),
    )


def _resolve_cost_unit(
    task: TaskFrame,
    selected_candidates: Sequence[ContextCandidate],
) -> str | None:
    candidate_units = {
        candidate.cost_unit
        for candidate in selected_candidates
        if candidate.acquisition_cost > 0
    }
    if len(candidate_units) > 1:
        units = ", ".join(sorted(unit for unit in candidate_units if unit))
        raise ValueError(
            "selected candidate acquisition costs use incompatible units: "
            f"{units}"
        )

    candidate_unit = next(iter(candidate_units), None)
    if task.context_budget is not None:
        if candidate_unit is not None and candidate_unit != task.context_budget_unit:
            raise ValueError(
                "selected candidate acquisition cost unit does not match "
                "task context budget unit"
            )
        return task.context_budget_unit
    return candidate_unit


def assess_task_context(
    task: TaskFrame,
    requirements: Sequence[ContextRequirement],
    selected_candidates: Sequence[ContextCandidate],
) -> TaskContext:
    """Assess a bounded, caller-selected context for sufficiency.

    This function does not search for candidates and does not choose an
    "optimal" context. It answers the narrower v0.1 question: given this task,
    these explicit requirements, and these selected context items, are all
    critical requirements covered at the declared resolution, and does their
    declared acquisition cost fit the task budget?
    """

    requirement_ids = [item.requirement_id for item in requirements]
    candidate_ids = [item.candidate_id for item in selected_candidates]
    _require_unique(requirement_ids, "requirements")
    _require_unique(candidate_ids, "selected_candidates")

    known_requirements = set(requirement_ids)
    for candidate in selected_candidates:
        unknown = set(candidate.requirement_ids) - known_requirements
        if unknown:
            unknown_text = ", ".join(sorted(unknown))
            raise ValueError(
                f"candidate {candidate.candidate_id} references unknown "
                f"requirement ids: {unknown_text}"
            )

    coverage: list[ContextCoverage] = []
    gaps: list[str] = []
    refinement: list[str] = []
    critical_gap = False

    for requirement in requirements:
        assessments = [
            evaluate_context_candidate(task, requirement, candidate)
            for candidate in selected_candidates
            if requirement.requirement_id in candidate.requirement_ids
        ]
        usable_ids = tuple(
            sorted(item.candidate_id for item in assessments if item.usable)
        )
        coverage.append(
            ContextCoverage(
                requirement_id=requirement.requirement_id,
                candidate_ids=usable_ids,
            )
        )

        if not usable_ids:
            gaps.append(requirement.requirement_id)
            if requirement.critical:
                critical_gap = True
            if any(
                item.applicable and not item.resolution_sufficient
                for item in assessments
            ):
                refinement.append(requirement.requirement_id)

    cost_unit = _resolve_cost_unit(task, selected_candidates)
    total_cost = sum(item.acquisition_cost for item in selected_candidates)
    budget_exceeded = (
        task.context_budget is not None and total_cost > task.context_budget
    )

    if critical_gap:
        status = "insufficient"
    elif budget_exceeded:
        status = "over_budget"
    elif gaps:
        status = "sufficient_with_gaps"
    else:
        status = "sufficient"

    return TaskContext(
        task_id=task.task_id,
        status=status,
        selected_candidate_ids=tuple(sorted(candidate_ids)),
        coverage=tuple(coverage),
        gap_requirement_ids=tuple(sorted(gaps)),
        refinement_requirement_ids=tuple(sorted(set(refinement))),
        total_acquisition_cost=total_cost,
        cost_unit=cost_unit,
        budget_exceeded=budget_exceeded,
    )
