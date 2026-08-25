"""Temporal continuity and minimal rebuild contracts for GeoTask GT-C5.

This module sits after ``TemporalReassessmentPlan``. It determines which carried
TaskContext values remain reusable, requires explicit refresh results for affected
requirements, and materializes a new TaskContext only from explicit reassessment
outputs plus an explicit target SufficiencyAssessment.

It does not resolve provider truth, recompute relevance/applicability/resolution,
infer sufficiency, rerun minimality, or make a domain decision.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Literal, Sequence

from geotask_core.v1.context_minimality import ContextMinimalityAssessment
from geotask_core.v1.task_context import (
    CONTEXT_CONTRACT_VERSION,
    JSONValue,
    ContextAssessment,
    ContextGap,
    SufficiencyAssessment,
    TaskContext,
    TaskContextContractError,
    validate_context_bundle,
)
from geotask_core.v1.temporal_reassessment import TemporalReassessmentPlan

TEMPORAL_CONTINUITY_CONTRACT_VERSION = "0.1"
TEMPORAL_CONTEXT_CONTINUITY_PLAN_CONTRACT_ID = "geotask.temporal-context-continuity-plan"
TEMPORAL_CONTEXT_REFRESH_RESULT_CONTRACT_ID = "geotask.temporal-context-refresh-result"

TemporalContinuityStatus = Literal[
    "no_refresh_needed",
    "bounded_refresh_required",
    "full_refresh_required",
]


def _require_text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise TaskContextContractError(f"{name} must be a non-empty string")


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


def _stable_ref(prefix: str, payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return prefix + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class TemporalRequirementRefresh:
    """Explicit reassessment result for one affected ContextRequirement."""

    refresh_ref: str
    requirement_id: str
    assessment: ContextAssessment
    value_present: bool
    value: JSONValue = None
    gap: ContextGap | None = None
    source_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.refresh_ref, "refresh_ref")
        _require_text(self.requirement_id, "requirement_id")
        if self.assessment.requirement_id != self.requirement_id:
            raise TaskContextContractError(
                "assessment.requirement_id must match TemporalRequirementRefresh.requirement_id"
            )
        if not isinstance(self.value_present, bool):
            raise TaskContextContractError("value_present must be boolean")
        positive = self.assessment.status in {"satisfied", "degraded"}
        if positive and not self.value_present:
            raise TaskContextContractError(
                f"assessment status {self.assessment.status!r} requires an explicit refreshed value"
            )
        if not positive and self.value_present:
            raise TaskContextContractError(
                f"assessment status {self.assessment.status!r} cannot expose a refreshed value"
            )
        if self.gap is not None:
            if self.gap.requirement_id != self.requirement_id:
                raise TaskContextContractError(
                    "gap.requirement_id must match TemporalRequirementRefresh.requirement_id"
                )
            if self.gap.critical != self.assessment.critical:
                raise TaskContextContractError("refresh gap criticality must match assessment criticality")
        object.__setattr__(self, "source_refs", _unique_texts(self.source_refs, "source_refs"))
        if self.refresh_ref not in self.source_refs:
            raise TaskContextContractError("source_refs must include refresh_ref")


@dataclass(frozen=True, slots=True)
class TemporalContextContinuityPlan:
    """Reuse/refresh partition after a TemporalReassessmentPlan."""

    continuity_ref: str
    context_ref: str
    prior_sufficiency_ref: str
    reassessment_plan_ref: str
    world_delta_ref: str
    status: TemporalContinuityStatus
    refresh_requirement_ids: tuple[str, ...]
    reusable_carried_requirement_ids: tuple[str, ...]
    stale_carried_requirement_ids: tuple[str, ...]
    affected_noncarried_requirement_ids: tuple[str, ...]
    critical_refresh_requirement_ids: tuple[str, ...]
    full_refresh_required: bool
    sufficiency_reassessment_required: bool
    minimality_reassessment_required: bool
    prior_minimality_ref: str | None
    source_refs: tuple[str, ...]
    contract_version: str = TEMPORAL_CONTINUITY_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name, value in (
            ("continuity_ref", self.continuity_ref),
            ("context_ref", self.context_ref),
            ("prior_sufficiency_ref", self.prior_sufficiency_ref),
            ("reassessment_plan_ref", self.reassessment_plan_ref),
            ("world_delta_ref", self.world_delta_ref),
        ):
            _require_text(value, name)
        if self.status not in {
            "no_refresh_needed",
            "bounded_refresh_required",
            "full_refresh_required",
        }:
            raise TaskContextContractError("unsupported temporal continuity status")
        for name in (
            "refresh_requirement_ids",
            "reusable_carried_requirement_ids",
            "stale_carried_requirement_ids",
            "affected_noncarried_requirement_ids",
            "critical_refresh_requirement_ids",
            "source_refs",
        ):
            object.__setattr__(self, name, _unique_texts(getattr(self, name), name))
        if self.prior_minimality_ref is not None:
            _require_text(self.prior_minimality_ref, "prior_minimality_ref")
        if self.contract_version != TEMPORAL_CONTINUITY_CONTRACT_VERSION:
            raise TaskContextContractError(
                f"contract_version must equal {TEMPORAL_CONTINUITY_CONTRACT_VERSION!r}"
            )
        if set(self.reusable_carried_requirement_ids) & set(self.stale_carried_requirement_ids):
            raise TaskContextContractError("reusable and stale carried requirement IDs must be disjoint")
        if set(self.stale_carried_requirement_ids) | set(self.affected_noncarried_requirement_ids) != set(
            self.refresh_requirement_ids
        ):
            raise TaskContextContractError(
                "stale carried plus affected noncarried IDs must cover refresh requirements exactly"
            )
        if not set(self.critical_refresh_requirement_ids) <= set(self.refresh_requirement_ids):
            raise TaskContextContractError("critical refresh IDs must be a subset of refresh IDs")
        if self.status == "no_refresh_needed" and self.refresh_requirement_ids:
            raise TaskContextContractError("no_refresh_needed cannot contain refresh requirements")
        if self.status != "no_refresh_needed" and not self.refresh_requirement_ids:
            raise TaskContextContractError("refresh-required status must contain refresh requirements")
        if self.full_refresh_required != (self.status == "full_refresh_required"):
            raise TaskContextContractError("full_refresh_required must match continuity status")
        if self.sufficiency_reassessment_required != bool(self.refresh_requirement_ids):
            raise TaskContextContractError(
                "sufficiency_reassessment_required must match whether refresh requirements exist"
            )
        if self.minimality_reassessment_required and self.prior_minimality_ref is None:
            raise TaskContextContractError(
                "minimality_reassessment_required requires prior_minimality_ref"
            )
        if self.continuity_ref not in self.source_refs:
            raise TaskContextContractError("source_refs must include continuity_ref")
        if self.reassessment_plan_ref not in self.source_refs:
            raise TaskContextContractError("source_refs must include reassessment_plan_ref")


@dataclass(frozen=True, slots=True)
class TemporalContextRefreshResult:
    """Materialized post-change context with explicit sufficiency and reuse evidence."""

    prior_context_ref: str
    continuity_ref: str
    context: TaskContext
    sufficiency: SufficiencyAssessment
    reassessed_requirement_ids: tuple[str, ...]
    reused_carried_requirement_ids: tuple[str, ...]
    refreshed_value_requirement_ids: tuple[str, ...]
    added_value_requirement_ids: tuple[str, ...]
    removed_value_requirement_ids: tuple[str, ...]
    minimality_reassessment_required: bool
    contract_version: str = CONTEXT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _require_text(self.prior_context_ref, "prior_context_ref")
        _require_text(self.continuity_ref, "continuity_ref")
        if self.contract_version != CONTEXT_CONTRACT_VERSION:
            raise TaskContextContractError(
                f"contract_version must equal {CONTEXT_CONTRACT_VERSION!r}"
            )
        for name in (
            "reassessed_requirement_ids",
            "reused_carried_requirement_ids",
            "refreshed_value_requirement_ids",
            "added_value_requirement_ids",
            "removed_value_requirement_ids",
        ):
            object.__setattr__(self, name, _unique_texts(getattr(self, name), name))
        validate_context_bundle(self.context, self.sufficiency)
        if self.context.trace_ref is not None or self.sufficiency.trace_ref is not None:
            raise TaskContextContractError(
                "temporal refresh creates continuity lineage rather than reusing a construction trace"
            )
        if self.continuity_ref not in self.context.source_refs:
            raise TaskContextContractError("refreshed TaskContext must carry continuity_ref lineage")
        if self.continuity_ref not in self.sufficiency.source_refs:
            raise TaskContextContractError(
                "refreshed SufficiencyAssessment must carry continuity_ref lineage"
            )


def plan_temporal_context_continuity(
    context: TaskContext,
    sufficiency: SufficiencyAssessment,
    reassessment: TemporalReassessmentPlan,
    *,
    prior_minimality: ContextMinimalityAssessment | None = None,
) -> TemporalContextContinuityPlan:
    """Partition current carried values into reusable vs refresh-required sets."""
    validate_context_bundle(context, sufficiency)
    if reassessment.context_ref != context.context_ref:
        raise TaskContextContractError("reassessment.context_ref must match context.context_ref")
    if reassessment.prior_sufficiency_ref != sufficiency.assessment_ref:
        raise TaskContextContractError(
            "reassessment.prior_sufficiency_ref must match sufficiency.assessment_ref"
        )

    requirement_ids = tuple(item.requirement_id for item in context.requirements)
    requirement_set = set(requirement_ids)
    affected = set(reassessment.affected_requirement_ids)
    unaffected = set(reassessment.unaffected_requirement_ids)
    if affected | unaffected != requirement_set or affected & unaffected:
        raise TaskContextContractError(
            "reassessment affected/unaffected IDs must partition context requirements exactly"
        )
    if set(reassessment.critical_affected_requirement_ids) - affected:
        raise TaskContextContractError("critical affected IDs must be a subset of affected IDs")
    if reassessment.full_rebuild_required and affected != requirement_set:
        raise TaskContextContractError(
            "full reassessment must cover every declared context requirement"
        )

    prior_minimality_ref: str | None = None
    if prior_minimality is not None:
        if prior_minimality.target_context_ref != context.context_ref:
            raise TaskContextContractError(
                "prior_minimality.target_context_ref must match current context.context_ref"
            )
        if prior_minimality.status != "minimal":
            raise TaskContextContractError(
                "prior_minimality must be an explicit status='minimal' proof"
            )
        prior_minimality_ref = prior_minimality.assessment_ref

    carried = set(context.values)
    reusable_carried = tuple(sorted(carried & unaffected))
    stale_carried = tuple(sorted(carried & affected))
    affected_noncarried = tuple(sorted(affected - carried))
    refresh_ids = tuple(sorted(affected))

    if reassessment.full_rebuild_required:
        status: TemporalContinuityStatus = "full_refresh_required"
    elif refresh_ids:
        status = "bounded_refresh_required"
    else:
        status = "no_refresh_needed"

    identity = {
        "context_ref": context.context_ref,
        "prior_sufficiency_ref": sufficiency.assessment_ref,
        "reassessment_plan_ref": reassessment.plan_ref,
        "prior_minimality_ref": prior_minimality_ref,
        "refresh_requirement_ids": refresh_ids,
        "contract_version": TEMPORAL_CONTINUITY_CONTRACT_VERSION,
    }
    continuity_ref = _stable_ref("geotask://temporal-continuity/", identity)
    source_refs = _dedupe_texts(
        (
            continuity_ref,
            reassessment.plan_ref,
            context.context_ref,
            sufficiency.assessment_ref,
            *( () if prior_minimality_ref is None else (prior_minimality_ref,) ),
        )
    )
    return TemporalContextContinuityPlan(
        continuity_ref=continuity_ref,
        context_ref=context.context_ref,
        prior_sufficiency_ref=sufficiency.assessment_ref,
        reassessment_plan_ref=reassessment.plan_ref,
        world_delta_ref=reassessment.world_delta_ref,
        status=status,
        refresh_requirement_ids=refresh_ids,
        reusable_carried_requirement_ids=reusable_carried,
        stale_carried_requirement_ids=stale_carried,
        affected_noncarried_requirement_ids=affected_noncarried,
        critical_refresh_requirement_ids=tuple(sorted(reassessment.critical_affected_requirement_ids)),
        full_refresh_required=reassessment.full_rebuild_required,
        sufficiency_reassessment_required=bool(refresh_ids),
        minimality_reassessment_required=bool(refresh_ids) and prior_minimality_ref is not None,
        prior_minimality_ref=prior_minimality_ref,
        source_refs=source_refs,
    )


def apply_temporal_context_refresh(
    prior_context: TaskContext,
    prior_sufficiency: SufficiencyAssessment,
    continuity: TemporalContextContinuityPlan,
    refreshes: Sequence[TemporalRequirementRefresh],
    target_sufficiency: SufficiencyAssessment,
    *,
    target_context_ref: str,
    refreshed_at: str,
) -> TemporalContextRefreshResult:
    """Materialize a bounded refresh without recomputing assessment or sufficiency."""
    validate_context_bundle(prior_context, prior_sufficiency)
    _require_text(target_context_ref, "target_context_ref")
    _require_text(refreshed_at, "refreshed_at")
    if continuity.context_ref != prior_context.context_ref:
        raise TaskContextContractError("continuity.context_ref must match prior_context.context_ref")
    if continuity.prior_sufficiency_ref != prior_sufficiency.assessment_ref:
        raise TaskContextContractError(
            "continuity.prior_sufficiency_ref must match prior_sufficiency.assessment_ref"
        )
    if continuity.status == "no_refresh_needed":
        raise TaskContextContractError("no refresh may be applied when continuity status is no_refresh_needed")

    requirement_ids = {item.requirement_id for item in prior_context.requirements}
    prior_value_ids = set(prior_context.values)
    refresh_ids = set(continuity.refresh_requirement_ids)
    reusable_ids = set(continuity.reusable_carried_requirement_ids)
    stale_ids = set(continuity.stale_carried_requirement_ids)
    noncarried_ids = set(continuity.affected_noncarried_requirement_ids)
    if refresh_ids - requirement_ids:
        raise TaskContextContractError("continuity refresh IDs must reference declared requirements")
    if reusable_ids | stale_ids != prior_value_ids or reusable_ids & stale_ids:
        raise TaskContextContractError(
            "continuity reusable/stale IDs must partition prior carried values exactly"
        )
    if stale_ids != refresh_ids & prior_value_ids:
        raise TaskContextContractError(
            "continuity stale carried IDs must equal affected prior carried values"
        )
    if noncarried_ids != refresh_ids - prior_value_ids:
        raise TaskContextContractError(
            "continuity affected noncarried IDs must equal affected requirements without prior values"
        )
    if continuity.full_refresh_required and refresh_ids != requirement_ids:
        raise TaskContextContractError("full temporal refresh must cover every declared requirement")

    refresh_by_id: dict[str, TemporalRequirementRefresh] = {}
    for refresh in refreshes:
        if refresh.requirement_id in refresh_by_id:
            raise TaskContextContractError("refreshes must contain at most one result per requirement_id")
        refresh_by_id[refresh.requirement_id] = refresh
    if set(refresh_by_id) != set(continuity.refresh_requirement_ids):
        raise TaskContextContractError("refreshes must cover continuity refresh requirements exactly")

    requirement_by_id = {item.requirement_id: item for item in prior_context.requirements}
    for requirement_id, refresh in refresh_by_id.items():
        requirement = requirement_by_id[requirement_id]
        if refresh.assessment.critical != requirement.critical:
            raise TaskContextContractError(
                f"refresh assessment criticality differs from requirement {requirement_id!r}"
            )
        if refresh.assessment.assessed_at != refreshed_at:
            raise TaskContextContractError(
                f"refresh assessment time for {requirement_id!r} must equal refreshed_at"
            )

    values: dict[str, JSONValue] = {
        requirement_id: prior_context.values[requirement_id]
        for requirement_id in continuity.reusable_carried_requirement_ids
    }
    for requirement_id in continuity.refresh_requirement_ids:
        refresh = refresh_by_id[requirement_id]
        if refresh.value_present:
            values[requirement_id] = refresh.value

    prior_assessment_by_id = {
        item.requirement_id: item for item in prior_sufficiency.assessments
    }
    merged_assessments: list[ContextAssessment] = []
    for requirement in prior_context.requirements:
        requirement_id = requirement.requirement_id
        if requirement_id in refresh_by_id:
            merged_assessments.append(refresh_by_id[requirement_id].assessment)
        elif requirement_id in prior_assessment_by_id:
            merged_assessments.append(prior_assessment_by_id[requirement_id])

    affected_set = set(continuity.refresh_requirement_ids)
    merged_gaps: list[ContextGap] = [
        gap for gap in prior_sufficiency.gaps if gap.requirement_id not in affected_set
    ]
    merged_gaps.extend(
        refresh_by_id[requirement_id].gap
        for requirement_id in continuity.refresh_requirement_ids
        if refresh_by_id[requirement_id].gap is not None
    )

    if target_sufficiency.context_ref != target_context_ref:
        raise TaskContextContractError(
            "target_sufficiency.context_ref must match target_context_ref"
        )
    if target_sufficiency.assessed_at != refreshed_at:
        raise TaskContextContractError(
            "target_sufficiency.assessed_at must match refreshed_at"
        )
    if target_sufficiency.trace_ref is not None:
        raise TaskContextContractError("target_sufficiency.trace_ref must be None for temporal refresh")
    if target_sufficiency.assessments != tuple(merged_assessments):
        raise TaskContextContractError(
            "target_sufficiency.assessments must equal reused plus refreshed assessments"
        )
    if target_sufficiency.gaps != tuple(merged_gaps):
        raise TaskContextContractError(
            "target_sufficiency.gaps must equal reused plus refreshed gaps"
        )
    if continuity.continuity_ref not in target_sufficiency.source_refs:
        raise TaskContextContractError(
            "target_sufficiency.source_refs must include continuity_ref"
        )
    for refresh in refreshes:
        if refresh.refresh_ref not in target_sufficiency.source_refs:
            raise TaskContextContractError(
                "target_sufficiency.source_refs must include every refresh_ref"
            )

    lineage = _dedupe_texts(
        (
            *prior_context.source_refs,
            prior_context.context_ref,
            *continuity.source_refs,
            *(refresh.refresh_ref for refresh in refreshes),
            *(ref for refresh in refreshes for ref in refresh.source_refs),
            *target_sufficiency.source_refs,
        )
    )
    context = TaskContext(
        context_ref=target_context_ref,
        task_frame=prior_context.task_frame,
        requirements=prior_context.requirements,
        constructed_at=refreshed_at,
        values=values,
        source_refs=lineage,
        valid_until=target_sufficiency.valid_until,
        trace_ref=None,
    )
    validate_context_bundle(context, target_sufficiency)

    prior_value_ids = set(prior_context.values)
    target_value_ids = set(context.values)
    refreshed_value_ids = tuple(
        sorted(set(continuity.refresh_requirement_ids) & target_value_ids)
    )
    return TemporalContextRefreshResult(
        prior_context_ref=prior_context.context_ref,
        continuity_ref=continuity.continuity_ref,
        context=context,
        sufficiency=target_sufficiency,
        reassessed_requirement_ids=continuity.refresh_requirement_ids,
        reused_carried_requirement_ids=continuity.reusable_carried_requirement_ids,
        refreshed_value_requirement_ids=refreshed_value_ids,
        added_value_requirement_ids=tuple(sorted(target_value_ids - prior_value_ids)),
        removed_value_requirement_ids=tuple(sorted(prior_value_ids - target_value_ids)),
        minimality_reassessment_required=continuity.minimality_reassessment_required,
    )


def temporal_context_continuity_plan_payload(
    plan: TemporalContextContinuityPlan,
) -> dict[str, object]:
    return {
        "contract": TEMPORAL_CONTEXT_CONTINUITY_PLAN_CONTRACT_ID,
        "contract_version": plan.contract_version,
        "continuity_ref": plan.continuity_ref,
        "context_ref": plan.context_ref,
        "prior_sufficiency_ref": plan.prior_sufficiency_ref,
        "reassessment_plan_ref": plan.reassessment_plan_ref,
        "world_delta_ref": plan.world_delta_ref,
        "status": plan.status,
        "refresh_requirement_ids": list(plan.refresh_requirement_ids),
        "reusable_carried_requirement_ids": list(plan.reusable_carried_requirement_ids),
        "stale_carried_requirement_ids": list(plan.stale_carried_requirement_ids),
        "affected_noncarried_requirement_ids": list(plan.affected_noncarried_requirement_ids),
        "critical_refresh_requirement_ids": list(plan.critical_refresh_requirement_ids),
        "full_refresh_required": plan.full_refresh_required,
        "sufficiency_reassessment_required": plan.sufficiency_reassessment_required,
        "minimality_reassessment_required": plan.minimality_reassessment_required,
        "prior_minimality_ref": plan.prior_minimality_ref,
        "source_refs": list(plan.source_refs),
    }


def temporal_context_refresh_result_payload(
    result: TemporalContextRefreshResult,
) -> dict[str, object]:
    return {
        "contract": TEMPORAL_CONTEXT_REFRESH_RESULT_CONTRACT_ID,
        "contract_version": result.contract_version,
        "prior_context_ref": result.prior_context_ref,
        "continuity_ref": result.continuity_ref,
        "context_ref": result.context.context_ref,
        "sufficiency_ref": result.sufficiency.assessment_ref,
        "sufficiency_status": result.sufficiency.status,
        "reassessed_requirement_ids": list(result.reassessed_requirement_ids),
        "reused_carried_requirement_ids": list(result.reused_carried_requirement_ids),
        "refreshed_value_requirement_ids": list(result.refreshed_value_requirement_ids),
        "added_value_requirement_ids": list(result.added_value_requirement_ids),
        "removed_value_requirement_ids": list(result.removed_value_requirement_ids),
        "minimality_reassessment_required": result.minimality_reassessment_required,
        "source_refs": list(result.context.source_refs),
    }
