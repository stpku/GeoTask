"""Explicit task-relative assessment composition seams for GeoTask v2.1.

GT-C3b keeps independent cognition results observable without turning them into a
mandatory linear pipeline. Relevance, applicability, and resolution adequacy may be
present independently in a requirement evidence bundle. An explicit method owns the
policy that maps those inputs to ``ContextAssessment``.

Aggregate task sufficiency is likewise method-owned. Core validates exact requirement
coverage, binding, time coherence, and result lineage; it does not derive sufficiency
from requirement statuses.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Sequence, runtime_checkable

from geotask_core.v1.context_construction import AssessedContextItem
from geotask_core.v1.context_provider import (
    ApplicabilityResult,
    ContextCandidate,
    RelevanceResult,
)
from geotask_core.v1.resolution_adequacy import ResolutionAdequacyResult
from geotask_core.v1.task_context import (
    CONTEXT_CONTRACT_VERSION,
    ContextAssessment,
    ContextGap,
    ContextRequirement,
    SufficiencyAssessment,
    TaskContextContractError,
    TaskFrame,
)

REQUIREMENT_ASSESSMENT_EVIDENCE_CONTRACT_ID = "geotask.requirement-assessment-evidence"


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


def _unique_texts(values: Sequence[str], name: str = "source_refs") -> tuple[str, ...]:
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


@dataclass(frozen=True, slots=True)
class RequirementAssessmentEvidence:
    """Coherent, inspectable evidence for one candidate/requirement assessment.

    Each cognition result is optional. Their absence remains explicit and no missing
    result is manufactured by this contract. When multiple results are supplied they
    must refer to the same requirement, candidate, and assessment instant.
    """

    evidence_ref: str
    requirement_id: str
    candidate_ref: str
    assembled_at: str
    relevance: RelevanceResult | None = None
    applicability: ApplicabilityResult | None = None
    resolution_adequacy: ResolutionAdequacyResult | None = None
    source_refs: tuple[str, ...] = ()
    contract_version: str = CONTEXT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _require_text(self.evidence_ref, "evidence_ref")
        _require_text(self.requirement_id, "requirement_id")
        _require_text(self.candidate_ref, "candidate_ref")
        _require_timestamp(self.assembled_at, "assembled_at")
        if self.contract_version != CONTEXT_CONTRACT_VERSION:
            raise TaskContextContractError(
                f"contract_version must equal {CONTEXT_CONTRACT_VERSION!r}"
            )
        if self.relevance is None and self.applicability is None and self.resolution_adequacy is None:
            raise TaskContextContractError(
                "RequirementAssessmentEvidence must contain at least one explicit cognition result"
            )
        _validate_cognition_bindings(self)
        object.__setattr__(self, "source_refs", _unique_texts(self.source_refs))


@runtime_checkable
class RequirementAssessmentMethod(Protocol):
    """Explicit policy seam for mapping cognition evidence to ContextAssessment."""

    @property
    def method_ref(self) -> str:
        ...

    def assess_requirement(
        self,
        task_frame: TaskFrame,
        requirement: ContextRequirement,
        candidate: ContextCandidate,
        evidence: RequirementAssessmentEvidence,
        *,
        as_of: str,
    ) -> ContextAssessment:
        ...


@runtime_checkable
class SufficiencyCompositionMethod(Protocol):
    """Explicit policy seam for composing requirement assessments into sufficiency."""

    @property
    def method_ref(self) -> str:
        ...

    def compose_sufficiency(
        self,
        *,
        context_ref: str,
        requirements: tuple[ContextRequirement, ...],
        assessments: tuple[ContextAssessment, ...],
        gaps: tuple[ContextGap, ...],
        as_of: str,
        valid_until: str | None,
        trace_ref: str | None,
    ) -> SufficiencyAssessment:
        ...


def assess_requirement_from_evidence(
    method: RequirementAssessmentMethod,
    task_frame: TaskFrame,
    requirement: ContextRequirement,
    candidate: ContextCandidate,
    evidence: RequirementAssessmentEvidence,
    *,
    as_of: str,
) -> AssessedContextItem:
    """Apply one explicit requirement method without inferring policy in Core."""
    _require_text(method.method_ref, "RequirementAssessmentMethod.method_ref")
    _require_timestamp(as_of, "as_of")
    _validate_requirement_candidate_evidence(requirement, candidate, evidence, as_of=as_of)

    assessment = method.assess_requirement(
        task_frame,
        requirement,
        candidate,
        evidence,
        as_of=as_of,
    )
    _validate_requirement_assessment_result(
        method.method_ref,
        requirement,
        evidence,
        assessment,
        as_of=as_of,
    )

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
        source_refs=_dedupe_texts(
            (
                method.method_ref,
                evidence.evidence_ref,
                candidate.candidate_ref,
                candidate.provider_ref,
                *candidate.source_refs,
                *evidence.source_refs,
                *assessment.source_refs,
            )
        ),
    )
    return AssessedContextItem(
        requirement_id=requirement.requirement_id,
        assessment=assessment,
        gap=gap,
    )


def compose_sufficiency_assessment(
    method: SufficiencyCompositionMethod,
    *,
    context_ref: str,
    requirements: Sequence[ContextRequirement],
    assessments: Sequence[ContextAssessment],
    gaps: Sequence[ContextGap],
    as_of: str,
    valid_until: str | None = None,
    trace_ref: str | None = None,
) -> SufficiencyAssessment:
    """Invoke an explicit sufficiency policy and validate exact input/result closure.

    Core intentionally does not calculate the aggregate status. Different explicit
    methods may produce different valid conclusions from the same positive inputs,
    while impossible combinations remain rejected by ``SufficiencyAssessment``.
    """
    _require_text(method.method_ref, "SufficiencyCompositionMethod.method_ref")
    _require_text(context_ref, "context_ref")
    _require_timestamp(as_of, "as_of")
    requirement_tuple = tuple(requirements)
    assessment_tuple = tuple(assessments)
    gap_tuple = tuple(gaps)
    _validate_sufficiency_inputs(requirement_tuple, assessment_tuple, gap_tuple, as_of=as_of)

    result = method.compose_sufficiency(
        context_ref=context_ref,
        requirements=requirement_tuple,
        assessments=assessment_tuple,
        gaps=gap_tuple,
        as_of=as_of,
        valid_until=valid_until,
        trace_ref=trace_ref,
    )
    _validate_sufficiency_result(
        method.method_ref,
        context_ref,
        assessment_tuple,
        gap_tuple,
        result,
        as_of=as_of,
        valid_until=valid_until,
        trace_ref=trace_ref,
    )
    return result


def requirement_assessment_evidence_payload(
    evidence: RequirementAssessmentEvidence,
) -> dict[str, object]:
    """Serialize references/statuses without duplicating provider payload bytes."""
    return {
        "contract": REQUIREMENT_ASSESSMENT_EVIDENCE_CONTRACT_ID,
        "contract_version": evidence.contract_version,
        "evidence_ref": evidence.evidence_ref,
        "requirement_id": evidence.requirement_id,
        "candidate_ref": evidence.candidate_ref,
        "assembled_at": evidence.assembled_at,
        "relevance": _cognition_ref_status(evidence.relevance, "relevance_ref"),
        "applicability": _cognition_ref_status(evidence.applicability, "applicability_ref"),
        "resolution_adequacy": _cognition_ref_status(
            evidence.resolution_adequacy,
            "adequacy_ref",
        ),
        "source_refs": list(evidence.source_refs),
    }


def _cognition_ref_status(result: object | None, ref_field: str) -> dict[str, object] | None:
    if result is None:
        return None
    return {
        "ref": getattr(result, ref_field),
        "status": getattr(result, "status"),
        "assessed_at": getattr(result, "assessed_at"),
    }


def _validate_cognition_bindings(evidence: RequirementAssessmentEvidence) -> None:
    for name, result in (
        ("relevance", evidence.relevance),
        ("applicability", evidence.applicability),
        ("resolution_adequacy", evidence.resolution_adequacy),
    ):
        if result is None:
            continue
        if result.requirement_id != evidence.requirement_id:
            raise TaskContextContractError(
                f"{name}.requirement_id must match RequirementAssessmentEvidence.requirement_id"
            )
        if result.candidate_ref != evidence.candidate_ref:
            raise TaskContextContractError(
                f"{name}.candidate_ref must match RequirementAssessmentEvidence.candidate_ref"
            )
        if result.assessed_at != evidence.assembled_at:
            raise TaskContextContractError(
                f"{name}.assessed_at must match RequirementAssessmentEvidence.assembled_at"
            )


def _validate_requirement_candidate_evidence(
    requirement: ContextRequirement,
    candidate: ContextCandidate,
    evidence: RequirementAssessmentEvidence,
    *,
    as_of: str,
) -> None:
    if candidate.requirement_id != requirement.requirement_id:
        raise TaskContextContractError(
            "candidate.requirement_id must match ContextRequirement.requirement_id"
        )
    if evidence.requirement_id != requirement.requirement_id:
        raise TaskContextContractError(
            "evidence.requirement_id must match ContextRequirement.requirement_id"
        )
    if evidence.candidate_ref != candidate.candidate_ref:
        raise TaskContextContractError(
            "evidence.candidate_ref must match ContextCandidate.candidate_ref"
        )
    if evidence.assembled_at != as_of:
        raise TaskContextContractError("evidence.assembled_at must equal explicit assessment as_of")


def _validate_requirement_assessment_result(
    method_ref: str,
    requirement: ContextRequirement,
    evidence: RequirementAssessmentEvidence,
    assessment: ContextAssessment,
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
        raise TaskContextContractError("assessment.assessed_at must equal explicit assessment as_of")
    if method_ref not in assessment.source_refs:
        raise TaskContextContractError(
            "assessment.source_refs must include RequirementAssessmentMethod.method_ref"
        )
    if evidence.evidence_ref not in assessment.source_refs:
        raise TaskContextContractError(
            "assessment.source_refs must include RequirementAssessmentEvidence.evidence_ref"
        )


def _validate_sufficiency_inputs(
    requirements: tuple[ContextRequirement, ...],
    assessments: tuple[ContextAssessment, ...],
    gaps: tuple[ContextGap, ...],
    *,
    as_of: str,
) -> None:
    requirement_ids = [item.requirement_id for item in requirements]
    if len(requirement_ids) != len(set(requirement_ids)):
        raise TaskContextContractError("requirements must have unique requirement_id values")
    assessment_ids = [item.requirement_id for item in assessments]
    if len(assessment_ids) != len(set(assessment_ids)):
        raise TaskContextContractError("assessments must contain exactly one result per requirement_id")
    if set(assessment_ids) != set(requirement_ids):
        raise TaskContextContractError("assessments must cover requirements exactly")

    requirement_by_id = {item.requirement_id: item for item in requirements}
    for assessment in assessments:
        requirement = requirement_by_id[assessment.requirement_id]
        if assessment.critical != requirement.critical:
            raise TaskContextContractError(
                f"assessment criticality differs from requirement {assessment.requirement_id!r}"
            )
        if assessment.assessed_at != as_of:
            raise TaskContextContractError("all assessments must equal explicit sufficiency as_of")

    gap_ids: set[str] = set()
    for gap in gaps:
        if gap.gap_id in gap_ids:
            raise TaskContextContractError("gaps must have unique gap_id values")
        gap_ids.add(gap.gap_id)
        if gap.requirement_id not in requirement_by_id:
            raise TaskContextContractError("gaps must reference declared requirements")
        if gap.critical != requirement_by_id[gap.requirement_id].critical:
            raise TaskContextContractError(
                f"gap criticality differs from requirement {gap.requirement_id!r}"
            )


def _validate_sufficiency_result(
    method_ref: str,
    context_ref: str,
    assessments: tuple[ContextAssessment, ...],
    gaps: tuple[ContextGap, ...],
    result: SufficiencyAssessment,
    *,
    as_of: str,
    valid_until: str | None,
    trace_ref: str | None,
) -> None:
    if result.context_ref != context_ref:
        raise TaskContextContractError("result.context_ref must match explicit context_ref")
    if result.assessed_at != as_of:
        raise TaskContextContractError("result.assessed_at must equal explicit sufficiency as_of")
    if result.assessments != assessments:
        raise TaskContextContractError("result.assessments must preserve explicit assessment inputs")
    if result.gaps != gaps:
        raise TaskContextContractError("result.gaps must preserve explicit gap inputs")
    if result.valid_until != valid_until:
        raise TaskContextContractError("result.valid_until must match explicit valid_until")
    if result.trace_ref != trace_ref:
        raise TaskContextContractError("result.trace_ref must match explicit trace_ref")
    if method_ref not in result.source_refs:
        raise TaskContextContractError(
            "result.source_refs must include SufficiencyCompositionMethod.method_ref"
        )


def _gap_id(requirement_id: str, status: str) -> str:
    safe_requirement = requirement_id.replace("/", "%2F")
    safe_status = status.replace("/", "%2F").replace(" ", "-")
    return f"geotask://context-gap/assessment-composition/{safe_requirement}/{safe_status}"
