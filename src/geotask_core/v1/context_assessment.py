"""Task-relative candidate assessment seam for GeoTask v2.1.

This module adds behavior, not a new wire/schema family. It reuses the existing
``ContextAssessment``, ``ContextGap``, ``ContextCandidate`` and
``AssessedContextItem`` contracts.

The reference selector is intentionally conservative: it will only expose a
candidate when exactly one candidate exists and the configured GeoTask-owned
assessment method marks that candidate ``satisfied`` or ``degraded``. Multiple
candidates are not ranked implicitly.
"""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from geotask_core.v1.context_construction import AssessedContextItem
from geotask_core.v1.context_provider import ContextCandidate, validate_candidate_binding
from geotask_core.v1.task_context import (
    ContextAssessment,
    ContextGap,
    ContextRequirement,
    TaskContextContractError,
    TaskFrame,
)


@runtime_checkable
class CandidateAssessmentMethod(Protocol):
    """GeoTask-owned method seam for judging one candidate relative to one task need.

    Implementations may combine relevance, applicability, resolution adequacy,
    field coverage, temporal constraints, or other task-relative checks in any
    method-appropriate structure. This protocol deliberately does not prescribe a
    fixed linear stage order and does not let the method rewrite provider truth.
    """

    @property
    def method_ref(self) -> str:
        """Stable method identity used for traceability."""
        ...

    def assess_candidate(
        self,
        task_frame: TaskFrame,
        requirement: ContextRequirement,
        candidate: ContextCandidate,
        *,
        as_of: str,
    ) -> ContextAssessment:
        """Return one explicit task-relative assessment for the supplied candidate."""
        ...


def assess_requirement_candidates(
    method: CandidateAssessmentMethod,
    task_frame: TaskFrame,
    requirement: ContextRequirement,
    candidates: Sequence[ContextCandidate],
    *,
    as_of: str,
) -> AssessedContextItem:
    """Apply one assessment method with fail-closed, non-ranking selection.

    This reference behavior intentionally solves only an unambiguous case:

    - zero candidates -> explicit unknown + ContextGap;
    - exactly one candidate -> method assessment determines whether it may be selected;
    - multiple candidates -> explicit unknown + ContextGap; no latest/source/confidence
      ranking is invented here.

    Aggregate task sufficiency remains a separate GeoTask decision supplied to the
    ``ContextConstructor``; this function does not infer it.
    """
    _require_method_ref(method.method_ref)

    if len(candidates) == 0:
        return _unknown_item(
            method.method_ref,
            requirement,
            as_of=as_of,
            reason="no_candidate_available",
            source_refs=(),
        )

    for candidate in candidates:
        validate_candidate_binding(candidate, requirement)

    if len(candidates) != 1:
        refs = tuple(
            dict.fromkeys(
                ref
                for candidate in candidates
                for ref in (candidate.candidate_ref, candidate.provider_ref, *candidate.source_refs)
            )
        )
        return _unknown_item(
            method.method_ref,
            requirement,
            as_of=as_of,
            reason="multiple_candidates_require_explicit_selection",
            source_refs=refs,
        )

    candidate = candidates[0]
    assessment = method.assess_candidate(
        task_frame,
        requirement,
        candidate,
        as_of=as_of,
    )
    _validate_assessment(assessment, requirement, as_of=as_of)

    if assessment.status in {"satisfied", "degraded"}:
        return AssessedContextItem(
            requirement_id=requirement.requirement_id,
            assessment=assessment,
            selected_candidate=candidate,
        )

    gap = ContextGap(
        gap_id=_gap_id(requirement.requirement_id, assessment.status),
        requirement_id=requirement.requirement_id,
        critical=requirement.critical,
        reason=assessment.reason,
        recoverable=assessment.status not in {"blocked", "not_applicable"},
        source_refs=tuple(
            dict.fromkeys(
                (
                    method.method_ref,
                    candidate.candidate_ref,
                    candidate.provider_ref,
                    *candidate.source_refs,
                    *assessment.source_refs,
                )
            )
        ),
    )
    return AssessedContextItem(
        requirement_id=requirement.requirement_id,
        assessment=assessment,
        gap=gap,
    )


def _unknown_item(
    method_ref: str,
    requirement: ContextRequirement,
    *,
    as_of: str,
    reason: str,
    source_refs: Sequence[str],
) -> AssessedContextItem:
    refs = tuple(dict.fromkeys((method_ref, *source_refs)))
    assessment = ContextAssessment(
        requirement_id=requirement.requirement_id,
        critical=requirement.critical,
        status="unknown",
        assessed_at=as_of,
        reason=reason,
        source_refs=refs,
    )
    gap = ContextGap(
        gap_id=_gap_id(requirement.requirement_id, reason),
        requirement_id=requirement.requirement_id,
        critical=requirement.critical,
        reason=reason,
        recoverable=True,
        source_refs=refs,
    )
    return AssessedContextItem(
        requirement_id=requirement.requirement_id,
        assessment=assessment,
        gap=gap,
    )


def _validate_assessment(
    assessment: ContextAssessment,
    requirement: ContextRequirement,
    *,
    as_of: str,
) -> None:
    if assessment.requirement_id != requirement.requirement_id:
        raise TaskContextContractError(
            "assessment.requirement_id must match ContextRequirement.requirement_id"
        )
    if assessment.critical != requirement.critical:
        raise TaskContextContractError(
            "assessment.critical must match ContextRequirement.critical"
        )
    if assessment.assessed_at != as_of:
        raise TaskContextContractError(
            "assessment.assessed_at must equal the explicit assessment as_of"
        )


def _require_method_ref(method_ref: str) -> None:
    if not isinstance(method_ref, str) or not method_ref.strip():
        raise TaskContextContractError("CandidateAssessmentMethod.method_ref must be non-empty")


def _gap_id(requirement_id: str, reason: str) -> str:
    safe_requirement = requirement_id.replace("/", "%2F")
    safe_reason = reason.replace("/", "%2F").replace(" ", "-")
    return f"geotask://context-gap/assessment/{safe_requirement}/{safe_reason}"
