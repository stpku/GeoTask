"""Task-relative reassessment planning for provider-owned reality changes.

GeoTask consumes a provider-neutral change payload and decides only which
ContextRequirements must be reassessed. It does not resolve world truth and does
not reinterpret the provider's change semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Literal, Mapping, Sequence

from geotask_core.v1.task_context import (
    SufficiencyAssessment,
    TaskContext,
    TaskContextContractError,
    validate_context_bundle,
)

TEMPORAL_REASSESSMENT_CONTRACT_VERSION = "0.1"
TEMPORAL_REASSESSMENT_PLAN_CONTRACT_ID = "geotask.temporal-reassessment-plan"
SUPPORTED_WORLD_DELTA_CONTRACT = "worldstate.delta"
SUPPORTED_WORLD_DELTA_VERSION = "0.1"

ReassessmentStatus = Literal[
    "no_reassessment_needed",
    "partial_reassessment_required",
    "critical_reassessment_required",
    "full_reassessment_required",
]


@dataclass(frozen=True, slots=True)
class TemporalReassessmentPlan:
    plan_ref: str
    context_ref: str
    prior_sufficiency_ref: str
    world_delta_ref: str
    status: ReassessmentStatus
    affected_requirement_ids: tuple[str, ...]
    unaffected_requirement_ids: tuple[str, ...]
    critical_affected_requirement_ids: tuple[str, ...]
    changed_dependency_refs: tuple[str, ...]
    unlocalized_dependency_refs: tuple[str, ...]
    rebuild_required: bool
    full_rebuild_required: bool
    prior_sufficiency_status: str
    contract_version: str = TEMPORAL_REASSESSMENT_CONTRACT_VERSION


class TemporalReassessmentError(TaskContextContractError):
    """Raised when a change payload cannot be safely routed to task context."""


def _require_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TemporalReassessmentError(f"{name} must be a non-empty string")
    return value


def _require_sequence(value: object, name: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise TemporalReassessmentError(f"{name} must be an array")
    return value


def _changed_dependency_refs(delta_payload: Mapping[str, object]) -> tuple[str, ...]:
    contract = _require_text(delta_payload.get("contract"), "delta.contract")
    version = _require_text(delta_payload.get("contract_version"), "delta.contract_version")
    if contract != SUPPORTED_WORLD_DELTA_CONTRACT:
        raise TemporalReassessmentError(
            f"unsupported world delta contract: {contract!r}"
        )
    if version != SUPPORTED_WORLD_DELTA_VERSION:
        raise TemporalReassessmentError(
            f"unsupported world delta contract version: {version!r}"
        )

    refs: set[str] = set()
    for index, raw_change in enumerate(_require_sequence(delta_payload.get("changes"), "delta.changes")):
        if not isinstance(raw_change, Mapping):
            raise TemporalReassessmentError(f"delta.changes[{index}] must be an object")
        for field in ("affected_state_refs", "source_refs"):
            raw_refs = _require_sequence(raw_change.get(field, ()), f"delta.changes[{index}].{field}")
            for ref_index, ref in enumerate(raw_refs):
                refs.add(_require_text(ref, f"delta.changes[{index}].{field}[{ref_index}]"))
    return tuple(sorted(refs))


def _stable_plan_ref(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "geotask://temporal-reassessment/" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def plan_temporal_reassessment(
    context: TaskContext,
    sufficiency: SufficiencyAssessment,
    world_delta_payload: Mapping[str, object],
) -> TemporalReassessmentPlan:
    """Determine the minimum ContextRequirement set affected by one world delta.

    Requirement localization uses the source references already recorded on each
    GeoTask ContextAssessment. If a changed dependency is known to the aggregate
    TaskContext but cannot be localized to a requirement, the function fails
    closed to a full reassessment rather than guessing which requirement is safe.
    """
    validate_context_bundle(context, sufficiency)
    delta_ref = _require_text(world_delta_payload.get("delta_id"), "delta.delta_id")
    changed_refs = _changed_dependency_refs(world_delta_payload)
    changed_set = set(changed_refs)

    requirement_ids = tuple(item.requirement_id for item in context.requirements)
    requirement_by_id = {item.requirement_id: item for item in context.requirements}
    assessments = {item.requirement_id: item for item in sufficiency.assessments}

    localized_dependency_refs: set[str] = set()
    affected: set[str] = set()
    for requirement_id in requirement_ids:
        assessment = assessments.get(requirement_id)
        if assessment is None:
            continue
        assessment_refs = set(assessment.source_refs)
        localized_dependency_refs.update(assessment_refs)
        if assessment_refs & changed_set:
            affected.add(requirement_id)

    aggregate_overlap = set(context.source_refs) & changed_set
    unlocalized = tuple(sorted(aggregate_overlap - localized_dependency_refs))
    full_rebuild = bool(unlocalized)
    if full_rebuild:
        affected = set(requirement_ids)

    affected_ids = tuple(sorted(affected))
    unaffected_ids = tuple(sorted(set(requirement_ids) - affected))
    critical_affected = tuple(
        requirement_id
        for requirement_id in affected_ids
        if requirement_by_id[requirement_id].critical
    )

    if full_rebuild:
        status: ReassessmentStatus = "full_reassessment_required"
    elif critical_affected:
        status = "critical_reassessment_required"
    elif affected_ids:
        status = "partial_reassessment_required"
    else:
        status = "no_reassessment_needed"

    identity_payload = {
        "context_ref": context.context_ref,
        "prior_sufficiency_ref": sufficiency.assessment_ref,
        "world_delta_ref": delta_ref,
        "affected_requirement_ids": affected_ids,
        "unlocalized_dependency_refs": unlocalized,
        "contract_version": TEMPORAL_REASSESSMENT_CONTRACT_VERSION,
    }
    return TemporalReassessmentPlan(
        plan_ref=_stable_plan_ref(identity_payload),
        context_ref=context.context_ref,
        prior_sufficiency_ref=sufficiency.assessment_ref,
        world_delta_ref=delta_ref,
        status=status,
        affected_requirement_ids=affected_ids,
        unaffected_requirement_ids=unaffected_ids,
        critical_affected_requirement_ids=critical_affected,
        changed_dependency_refs=changed_refs,
        unlocalized_dependency_refs=unlocalized,
        rebuild_required=bool(affected_ids),
        full_rebuild_required=full_rebuild,
        prior_sufficiency_status=sufficiency.status,
    )


def temporal_reassessment_plan_payload(plan: TemporalReassessmentPlan) -> dict[str, object]:
    return {
        "contract": TEMPORAL_REASSESSMENT_PLAN_CONTRACT_ID,
        "contract_version": plan.contract_version,
        "plan_ref": plan.plan_ref,
        "context_ref": plan.context_ref,
        "prior_sufficiency_ref": plan.prior_sufficiency_ref,
        "world_delta_ref": plan.world_delta_ref,
        "status": plan.status,
        "affected_requirement_ids": list(plan.affected_requirement_ids),
        "unaffected_requirement_ids": list(plan.unaffected_requirement_ids),
        "critical_affected_requirement_ids": list(plan.critical_affected_requirement_ids),
        "changed_dependency_refs": list(plan.changed_dependency_refs),
        "unlocalized_dependency_refs": list(plan.unlocalized_dependency_refs),
        "rebuild_required": plan.rebuild_required,
        "full_rebuild_required": plan.full_rebuild_required,
        "prior_sufficiency_status": plan.prior_sufficiency_status,
    }
