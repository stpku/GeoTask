"""Minimal task-context contracts for GeoTask.

This module is the first additive engineering slice for the Task Context Engine
architecture direction.  It deliberately does *not* discover context, infer
source authority, or make domain decisions.  Callers declare a task frame,
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
    references.  Core v0.1 does not infer containment or overlap between scope
    identifiers.  Domain packs may bind these references to richer geometry or
    temporal objects.
    """

    task_id: str
    goal: str
    subject_refs: tuple[str, ...] = ()
    spatial_scope: str | None = None
    temporal_scope: str | None = None
    outputs: tuple[str, ...] = ()
    context_budget: float | None = None

    def __post_init__(self) -> None:
        _require_nonempty(self.task_id, "task_id")
        _require_nonempty(self.goal, "goal")
        _require_unique(self.subject_refs, "subject_refs")
        _require_unique(self.outputs, "outputs")
        _require_nonnegative(self.context_budget, "context_budget")


@dataclass(frozen=True)
class ContextRequirement:
    """One explicit piece of context required by a task.

    Resolution values use a "smaller is finer" convention.  Their physical
    meaning and units must be declared by the surrounding domain/profile; Core
    only performs numeric ordering.
    """

    requirement_id: str
    what: str
    reason: str
    critical: bool = True
    spatial_scope: str | None = None
    temporal_scope: str | None = None
    max_spatial_resolution: float | None = None
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


@dataclass(frozen=True)
class ContextCandidate:
    """One available context item proposed for the current task.

    ``requirement_ids`` is an explicit relevance binding supplied by the
    caller/provider.  GeoTask Core does not infer relevance from text or source
    names in this first slice.
    """

    candidate_id: str
    source: str
    requirement_ids: tuple[str, ...]
    spatial_scope: str | None = None
    temporal_scope: str | None = None
    spatial_resolution: float | None = None
    temporal_resolution_seconds: float | None = None
    acquisition_cost: float = 0.0
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
    budget_exceeded: bool

    def __post_init__(self) -> None:
        if self.status not in TASK_CONTEXT_STATUSES:
            raise ValueError(f"unsupported task context status: {self.status}")

    @property
    def sufficient(self) -> bool:
        """Whether all critical requirements are covered at required resolution."""

        return self.status in {"sufficient", "sufficient_with_gaps"}


def evaluate_context_candidate(
    task: TaskFrame,
    requirement: ContextRequirement,
    candidate: ContextCandidate,
) -> CandidateContextAssessment:
    """Evaluate explicit relevance, applicability, and resolution.

    The function intentionally uses exact scope-reference matching.  It never
    assumes that two differently named spatial/temporal scopes overlap or that
    one contains the other.  Rich scope reasoning belongs in a declared
    operator/domain pack and can feed normalized scope references into this
    baseline contract.
    """

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


def assess_task_context(
    task: TaskFrame,
    requirements: Sequence[ContextRequirement],
    selected_candidates: Sequence[ContextCandidate],
) -> TaskContext:
    """Assess a bounded, caller-selected context for sufficiency.

    This function does not search for candidates and does not choose an
    "optimal" context.  It answers the narrower v0.1 question: given this task,
    these explicit requirements, and these selected context items, are all
    critical requirements covered at the declared resolution and within the
    declared acquisition budget?
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
        budget_exceeded=budget_exceeded,
    )
