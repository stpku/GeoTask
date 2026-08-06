"""Bounded object-graph change requests for approved identity-merge proposals.

GT41 binds exact GT39 proposal bytes and exact GT40 approval-record bytes. It
derives one closed subject-reference rewrite request, preserves alias history,
copies the inverse rollback plan, and declares preconditions and acceptance
criteria. A valid request is still only ready for application review: it never
applies the change, mutates an object graph or World State, releases production
output, authorizes action, or executes action.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TypeVar

from geotask_core.v1.identity_merge_approval_record import (
    IDENTITY_MERGE_APPROVAL_RECORD_ARTIFACT_ID,
    IdentityMergeApprovalRecord,
    IdentityMergeApprovalRecordError,
    load_identity_merge_approval_record,
    validate_identity_merge_approval_record_bindings,
)
from geotask_core.v1.identity_merge_proposal import (
    IDENTITY_MERGE_PROPOSAL_ARTIFACT_ID,
    IdentityMergeProposal,
    IdentityMergeProposalError,
    load_identity_merge_proposal,
)


OBJECT_GRAPH_CHANGE_REQUEST_ARTIFACT_ID = "geotask.object-graph-change-request"
OBJECT_GRAPH_CHANGE_REQUEST_SCHEMA_ID = (
    "https://stpku.github.io/GeoTask/schemas/"
    "geotask-object-graph-change-request-v0.1.schema.json"
)
OBJECT_GRAPH_CHANGE_REQUEST_SCHEMA_VERSION = "0.1"
OBJECT_GRAPH_CHANGE_REQUEST_FORMAT_VERSION = "0.1"

REQUEST_STATE = "ready_for_application_review"
REQUEST_REASON = (
    "approved_identity_merge_supports_bounded_object_graph_change_request"
)
NEXT_ACTION = "request_object_graph_change_application_approval"

PRECONDITIONS = (
    (
        "proposal_binding_verified",
        "The request must remain bound to the exact approved GT39 proposal bytes.",
        "verified",
    ),
    (
        "approval_record_binding_verified",
        "The request must remain bound to the exact GT40 approval record bytes.",
        "verified",
    ),
    (
        "approval_complete",
        "Every required approval role must have approved the source proposal.",
        "verified",
    ),
    (
        "canonical_subject_available",
        "The canonical subject must still exist when application is reviewed.",
        "requires_application_check",
    ),
    (
        "target_subject_binding_unchanged",
        "The target trajectory must still reference the declared merge subject.",
        "requires_application_check",
    ),
    (
        "no_withdrawal_condition_active",
        "No proposal withdrawal condition may be active at application time.",
        "requires_application_check",
    ),
    (
        "rollback_plan_available",
        "The inverse subject-reference rewrite must remain available.",
        "verified",
    ),
)

ACCEPTANCE_CRITERIA = (
    (
        "requested_subject_ref_rewrite_applied",
        "Only the declared trajectory subject_ref changes from the merge subject to the canonical subject.",
    ),
    (
        "retained_alias_preserved",
        "The merge subject remains recorded as an alias of the canonical subject.",
    ),
    (
        "no_undeclared_paths_changed",
        "No object-graph path outside the declared operation changes.",
    ),
    (
        "post_application_binding_validation_passed",
        "Post-application validation confirms exact source and target bindings.",
    ),
    (
        "rollback_plan_remains_available",
        "The inverse rollback operation remains complete after application.",
    ),
)

BLOCKED_OPERATIONS = (
    "unreviewed_change_application",
    "undeclared_path_mutation",
    "alias_deletion",
    "identity_creation",
    "world_state_update",
    "production_output_release",
    "action_execution",
)


class ObjectGraphChangeRequestError(ValueError):
    """Raised when an object-graph change request fails closed."""


def _fail(path: str, message: str) -> None:
    raise ObjectGraphChangeRequestError(f"{path}: {message}")


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        _fail(path, "must be an object")
    return value


def _exact_fields(
    value: Mapping[str, object],
    path: str,
    *,
    required: set[str] | frozenset[str],
) -> None:
    actual = set(value)
    missing = sorted(set(required) - actual)
    unknown = sorted(actual - set(required))
    if missing:
        _fail(path, "missing required fields: " + ", ".join(missing))
    if unknown:
        _fail(path, "contains unknown fields: " + ", ".join(unknown))


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(path, "must be a non-empty string")
    return value


def _boolean(value: object, path: str) -> bool:
    if type(value) is not bool:
        _fail(path, "must be boolean")
    return bool(value)


def _timestamp(value: object, path: str) -> str:
    text = _string(value, path)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ObjectGraphChangeRequestError(
            f"{path}: must be an ISO-8601 timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail(path, "must include a timezone")
    return text


def _sha256(value: object, path: str) -> str:
    text = _string(value, path)
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        _fail(path, "must be a lowercase 64-character SHA-256 digest")
    return text


def _string_tuple(
    value: object,
    path: str,
    *,
    minimum_items: int = 0,
) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array of strings")
    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        text = _string(item, f"{path}[{index}]")
        if text in seen:
            _fail(f"{path}[{index}]", f"duplicates {text!r}")
        seen.add(text)
        result.append(text)
    if len(result) < minimum_items:
        _fail(path, f"must contain at least {minimum_items} item(s)")
    return tuple(result)


def _hash_bytes(content: bytes, path: str) -> str:
    if not isinstance(content, bytes):
        _fail(path, "must be bytes")
    return hashlib.sha256(content).hexdigest()


def _json_mapping_from_bytes(content: bytes, path: str) -> Mapping[str, object]:
    if not isinstance(content, bytes):
        _fail(path, "must be bytes")
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ObjectGraphChangeRequestError(
            f"{path}: must contain UTF-8 JSON"
        ) from exc
    return _mapping(payload, path)


def _semantic_fingerprint(payload: Mapping[str, object]) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class SourceProposalRef:
    artifact_id: str
    proposal_id: str
    content_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "proposal_id": self.proposal_id,
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class SourceApprovalRecordRef:
    artifact_id: str
    approval_record_id: str
    content_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "approval_record_id": self.approval_record_id,
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class ObjectGraphChangeOperation:
    operation_id: str
    operation_kind: str
    target_object_kind: str
    target_ref: str
    target_path: str
    before_subject_ref: str
    after_subject_ref: str
    state: str

    def to_dict(self) -> dict[str, object]:
        return {
            "operation_id": self.operation_id,
            "operation_kind": self.operation_kind,
            "target_object_kind": self.target_object_kind,
            "target_ref": self.target_ref,
            "target_path": self.target_path,
            "before_subject_ref": self.before_subject_ref,
            "after_subject_ref": self.after_subject_ref,
            "state": self.state,
        }


@dataclass(frozen=True)
class RetainedAliasDeclaration:
    alias_subject_ref: str
    canonical_subject_ref: str
    source_trajectory_refs: tuple[str, ...]
    state: str

    def to_dict(self) -> dict[str, object]:
        return {
            "alias_subject_ref": self.alias_subject_ref,
            "canonical_subject_ref": self.canonical_subject_ref,
            "source_trajectory_refs": list(self.source_trajectory_refs),
            "state": self.state,
        }


@dataclass(frozen=True)
class ChangeRequestPrecondition:
    precondition_id: str
    requirement: str
    evaluation_state: str

    def to_dict(self) -> dict[str, object]:
        return {
            "precondition_id": self.precondition_id,
            "requirement": self.requirement,
            "evaluation_state": self.evaluation_state,
        }


@dataclass(frozen=True)
class ChangeRequestAcceptanceCriterion:
    criterion_id: str
    requirement: str
    evaluation_state: str

    def to_dict(self) -> dict[str, object]:
        return {
            "criterion_id": self.criterion_id,
            "requirement": self.requirement,
            "evaluation_state": self.evaluation_state,
        }


@dataclass(frozen=True)
class RollbackOperation:
    target_object_kind: str
    target_ref: str
    target_path: str
    restore_subject_ref: str
    state: str

    def to_dict(self) -> dict[str, object]:
        return {
            "target_object_kind": self.target_object_kind,
            "target_ref": self.target_ref,
            "target_path": self.target_path,
            "restore_subject_ref": self.restore_subject_ref,
            "state": self.state,
        }


@dataclass(frozen=True)
class ObjectGraphRollbackPlan:
    restore_operations: tuple[RollbackOperation, ...]
    preserve_alias_history: bool
    require_post_rollback_validation: bool
    rollback_authorization_required: bool
    rollback_executed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "restore_operations": [item.to_dict() for item in self.restore_operations],
            "preserve_alias_history": self.preserve_alias_history,
            "require_post_rollback_validation": self.require_post_rollback_validation,
            "rollback_authorization_required": self.rollback_authorization_required,
            "rollback_executed": self.rollback_executed,
        }


@dataclass(frozen=True)
class ObjectGraphChangeRequest:
    change_request_id: str
    created_at: str
    source_proposal_ref: SourceProposalRef
    source_approval_record_ref: SourceApprovalRecordRef
    request_state: str
    request_reason: str
    canonical_subject_ref: str
    merge_subject_ref: str
    object_class: str
    affected_trajectory_refs: tuple[str, ...]
    change_operations: tuple[ObjectGraphChangeOperation, ...]
    retained_aliases: tuple[RetainedAliasDeclaration, ...]
    preconditions: tuple[ChangeRequestPrecondition, ...]
    acceptance_criteria: tuple[ChangeRequestAcceptanceCriterion, ...]
    rollback_plan: ObjectGraphRollbackPlan
    proposal_binding_verified: bool
    approval_record_binding_verified: bool
    approved_scope_verified: bool
    request_scope_closed: bool
    retained_aliases_preserved: bool
    application_review_required: bool
    application_authorized: bool
    blocked_operations: tuple[str, ...]
    next_action: str
    change_applied: bool
    identity_merge_performed: bool
    subject_refs_mutated: bool
    object_graph_mutated: bool
    world_state_updated: bool
    production_output_released: bool
    action_authorized: bool
    action_executed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "object_graph_change_request": {
                "request_version": OBJECT_GRAPH_CHANGE_REQUEST_FORMAT_VERSION,
                "change_request_id": self.change_request_id,
                "created_at": self.created_at,
                "source_proposal_ref": self.source_proposal_ref.to_dict(),
                "source_approval_record_ref": self.source_approval_record_ref.to_dict(),
                "request_state": self.request_state,
                "request_reason": self.request_reason,
                "canonical_subject_ref": self.canonical_subject_ref,
                "merge_subject_ref": self.merge_subject_ref,
                "object_class": self.object_class,
                "affected_trajectory_refs": list(self.affected_trajectory_refs),
                "change_operations": [
                    item.to_dict() for item in self.change_operations
                ],
                "retained_aliases": [item.to_dict() for item in self.retained_aliases],
                "preconditions": [item.to_dict() for item in self.preconditions],
                "acceptance_criteria": [
                    item.to_dict() for item in self.acceptance_criteria
                ],
                "rollback_plan": self.rollback_plan.to_dict(),
                "proposal_binding_verified": self.proposal_binding_verified,
                "approval_record_binding_verified": self.approval_record_binding_verified,
                "approved_scope_verified": self.approved_scope_verified,
                "request_scope_closed": self.request_scope_closed,
                "retained_aliases_preserved": self.retained_aliases_preserved,
                "application_review_required": self.application_review_required,
                "application_authorized": self.application_authorized,
                "blocked_operations": list(self.blocked_operations),
                "next_action": self.next_action,
                "change_applied": self.change_applied,
                "identity_merge_performed": self.identity_merge_performed,
                "subject_refs_mutated": self.subject_refs_mutated,
                "object_graph_mutated": self.object_graph_mutated,
                "world_state_updated": self.world_state_updated,
                "production_output_released": self.production_output_released,
                "action_authorized": self.action_authorized,
                "action_executed": self.action_executed,
            }
        }

    def semantic_fingerprint(self) -> str:
        return _semantic_fingerprint(self.to_dict())


def _validate_sources(
    proposal: IdentityMergeProposal,
    approval: IdentityMergeApprovalRecord,
    *,
    proposal_bytes: bytes,
) -> None:
    if approval.aggregate_decision != "approved":
        _fail("source approval.aggregate_decision", "must be 'approved'")
    for field in (
        "proposal_binding_verified",
        "decision_scope_closed",
        "required_roles_covered",
        "proposal_approval_complete",
        "change_request_eligible",
    ):
        if not getattr(approval, field):
            _fail(f"source approval.{field}", "must be true")
    if approval.next_action != "prepare_identity_merge_change_request":
        _fail(
            "source approval.next_action",
            "must be 'prepare_identity_merge_change_request'",
        )
    for field in (
        "identity_merge_performed",
        "subject_refs_mutated",
        "object_graph_mutated",
        "world_state_updated",
        "production_output_released",
        "action_authorized",
        "action_executed",
    ):
        if getattr(approval, field):
            _fail(f"source approval.{field}", "must be false")
    if approval.source_proposal_ref.proposal_id != proposal.proposal_id:
        _fail("source approval.source_proposal_ref.proposal_id", "does not match proposal")
    if approval.source_proposal_ref.content_sha256 != _hash_bytes(
        proposal_bytes, "proposal_bytes"
    ):
        _fail(
            "source approval.source_proposal_ref.content_sha256",
            "does not match proposal bytes",
        )
    if approval.canonical_subject_ref != proposal.canonical_subject_ref:
        _fail("source approval.canonical_subject_ref", "does not match proposal")
    if approval.merge_subject_ref != proposal.merge_subject_ref:
        _fail("source approval.merge_subject_ref", "does not match proposal")
    if approval.affected_trajectory_refs != proposal.affected_trajectory_refs:
        _fail("source approval.affected_trajectory_refs", "does not match proposal")


def build_object_graph_change_request(
    *,
    change_request_id: str,
    created_at: str,
    proposal_bytes: bytes,
    approval_record_bytes: bytes,
) -> ObjectGraphChangeRequest:
    """Build one exact-bound, non-applying GT41 change request."""

    change_request_id = _string(change_request_id, "change_request_id")
    created_at = _timestamp(created_at, "created_at")
    proposal_payload = _json_mapping_from_bytes(proposal_bytes, "proposal_bytes")
    approval_payload = _json_mapping_from_bytes(
        approval_record_bytes, "approval_record_bytes"
    )
    try:
        proposal = load_identity_merge_proposal(proposal_payload)
    except IdentityMergeProposalError as exc:
        raise ObjectGraphChangeRequestError(str(exc)) from exc
    try:
        approval = load_identity_merge_approval_record(approval_payload)
        validate_identity_merge_approval_record_bindings(
            approval,
            proposal_bytes=proposal_bytes,
        )
    except IdentityMergeApprovalRecordError as exc:
        raise ObjectGraphChangeRequestError(str(exc)) from exc
    _validate_sources(proposal, approval, proposal_bytes=proposal_bytes)

    if len(proposal.proposed_subject_ref_rewrites) != 1:
        _fail(
            "source proposal.proposed_subject_ref_rewrites",
            "must contain exactly one rewrite",
        )
    rewrite = proposal.proposed_subject_ref_rewrites[0]
    if rewrite.state != "proposed":
        _fail(
            "source proposal.proposed_subject_ref_rewrites[0].state",
            "must be 'proposed'",
        )
    if rewrite.current_subject_ref != proposal.merge_subject_ref:
        _fail(
            "source proposal rewrite.current_subject_ref",
            "must equal merge_subject_ref",
        )
    if rewrite.proposed_subject_ref != proposal.canonical_subject_ref:
        _fail(
            "source proposal rewrite.proposed_subject_ref",
            "must equal canonical_subject_ref",
        )
    if len(proposal.retained_aliases) != 1:
        _fail("source proposal.retained_aliases", "must contain exactly one alias")
    if len(proposal.reversal_plan.restore_subject_refs) != 1:
        _fail(
            "source proposal.reversal_plan.restore_subject_refs",
            "must contain exactly one step",
        )
    reversal = proposal.reversal_plan.restore_subject_refs[0]
    if reversal.trajectory_ref != rewrite.trajectory_ref:
        _fail(
            "source proposal.reversal_plan",
            "must target the requested trajectory",
        )
    if reversal.restore_subject_ref != rewrite.current_subject_ref:
        _fail(
            "source proposal.reversal_plan",
            "must restore the original subject_ref",
        )

    operation = ObjectGraphChangeOperation(
        operation_id=f"rewrite-{rewrite.trajectory_ref}-subject-ref",
        operation_kind="replace_subject_ref",
        target_object_kind="trajectory",
        target_ref=rewrite.trajectory_ref,
        target_path="/subject_ref",
        before_subject_ref=rewrite.current_subject_ref,
        after_subject_ref=rewrite.proposed_subject_ref,
        state="requested",
    )
    aliases = tuple(
        RetainedAliasDeclaration(
            alias_subject_ref=item.alias_subject_ref,
            canonical_subject_ref=item.canonical_subject_ref,
            source_trajectory_refs=item.source_trajectory_refs,
            state=item.state,
        )
        for item in proposal.retained_aliases
    )
    preconditions = tuple(
        ChangeRequestPrecondition(
            precondition_id=identifier,
            requirement=requirement,
            evaluation_state=state,
        )
        for identifier, requirement, state in PRECONDITIONS
    )
    acceptance = tuple(
        ChangeRequestAcceptanceCriterion(
            criterion_id=identifier,
            requirement=requirement,
            evaluation_state="pending_application",
        )
        for identifier, requirement in ACCEPTANCE_CRITERIA
    )
    rollback = ObjectGraphRollbackPlan(
        restore_operations=(
            RollbackOperation(
                target_object_kind="trajectory",
                target_ref=reversal.trajectory_ref,
                target_path="/subject_ref",
                restore_subject_ref=reversal.restore_subject_ref,
                state="available",
            ),
        ),
        preserve_alias_history=proposal.reversal_plan.preserve_alias_history,
        require_post_rollback_validation=(
            proposal.reversal_plan.require_post_reversal_validation
        ),
        rollback_authorization_required=True,
        rollback_executed=False,
    )

    return ObjectGraphChangeRequest(
        change_request_id=change_request_id,
        created_at=created_at,
        source_proposal_ref=SourceProposalRef(
            artifact_id=IDENTITY_MERGE_PROPOSAL_ARTIFACT_ID,
            proposal_id=proposal.proposal_id,
            content_sha256=_hash_bytes(proposal_bytes, "proposal_bytes"),
        ),
        source_approval_record_ref=SourceApprovalRecordRef(
            artifact_id=IDENTITY_MERGE_APPROVAL_RECORD_ARTIFACT_ID,
            approval_record_id=approval.approval_record_id,
            content_sha256=_hash_bytes(
                approval_record_bytes, "approval_record_bytes"
            ),
        ),
        request_state=REQUEST_STATE,
        request_reason=REQUEST_REASON,
        canonical_subject_ref=proposal.canonical_subject_ref,
        merge_subject_ref=proposal.merge_subject_ref,
        object_class=proposal.object_class,
        affected_trajectory_refs=proposal.affected_trajectory_refs,
        change_operations=(operation,),
        retained_aliases=aliases,
        preconditions=preconditions,
        acceptance_criteria=acceptance,
        rollback_plan=rollback,
        proposal_binding_verified=True,
        approval_record_binding_verified=True,
        approved_scope_verified=True,
        request_scope_closed=True,
        retained_aliases_preserved=True,
        application_review_required=True,
        application_authorized=False,
        blocked_operations=BLOCKED_OPERATIONS,
        next_action=NEXT_ACTION,
        change_applied=False,
        identity_merge_performed=False,
        subject_refs_mutated=False,
        object_graph_mutated=False,
        world_state_updated=False,
        production_output_released=False,
        action_authorized=False,
        action_executed=False,
    )


def _load_source_proposal_ref(value: object, path: str) -> SourceProposalRef:
    body = _mapping(value, path)
    _exact_fields(
        body,
        path,
        required={"artifact_id", "proposal_id", "content_sha256"},
    )
    artifact_id = _string(body["artifact_id"], f"{path}.artifact_id")
    if artifact_id != IDENTITY_MERGE_PROPOSAL_ARTIFACT_ID:
        _fail(
            f"{path}.artifact_id",
            f"must be {IDENTITY_MERGE_PROPOSAL_ARTIFACT_ID!r}",
        )
    return SourceProposalRef(
        artifact_id=artifact_id,
        proposal_id=_string(body["proposal_id"], f"{path}.proposal_id"),
        content_sha256=_sha256(body["content_sha256"], f"{path}.content_sha256"),
    )


def _load_source_approval_ref(
    value: object, path: str
) -> SourceApprovalRecordRef:
    body = _mapping(value, path)
    _exact_fields(
        body,
        path,
        required={"artifact_id", "approval_record_id", "content_sha256"},
    )
    artifact_id = _string(body["artifact_id"], f"{path}.artifact_id")
    if artifact_id != IDENTITY_MERGE_APPROVAL_RECORD_ARTIFACT_ID:
        _fail(
            f"{path}.artifact_id",
            f"must be {IDENTITY_MERGE_APPROVAL_RECORD_ARTIFACT_ID!r}",
        )
    return SourceApprovalRecordRef(
        artifact_id=artifact_id,
        approval_record_id=_string(
            body["approval_record_id"], f"{path}.approval_record_id"
        ),
        content_sha256=_sha256(body["content_sha256"], f"{path}.content_sha256"),
    )


def _load_operation(value: object, path: str) -> ObjectGraphChangeOperation:
    body = _mapping(value, path)
    _exact_fields(
        body,
        path,
        required={
            "operation_id",
            "operation_kind",
            "target_object_kind",
            "target_ref",
            "target_path",
            "before_subject_ref",
            "after_subject_ref",
            "state",
        },
    )
    return ObjectGraphChangeOperation(
        operation_id=_string(body["operation_id"], f"{path}.operation_id"),
        operation_kind=_string(body["operation_kind"], f"{path}.operation_kind"),
        target_object_kind=_string(
            body["target_object_kind"], f"{path}.target_object_kind"
        ),
        target_ref=_string(body["target_ref"], f"{path}.target_ref"),
        target_path=_string(body["target_path"], f"{path}.target_path"),
        before_subject_ref=_string(
            body["before_subject_ref"], f"{path}.before_subject_ref"
        ),
        after_subject_ref=_string(
            body["after_subject_ref"], f"{path}.after_subject_ref"
        ),
        state=_string(body["state"], f"{path}.state"),
    )


def _load_alias(value: object, path: str) -> RetainedAliasDeclaration:
    body = _mapping(value, path)
    _exact_fields(
        body,
        path,
        required={
            "alias_subject_ref",
            "canonical_subject_ref",
            "source_trajectory_refs",
            "state",
        },
    )
    return RetainedAliasDeclaration(
        alias_subject_ref=_string(
            body["alias_subject_ref"], f"{path}.alias_subject_ref"
        ),
        canonical_subject_ref=_string(
            body["canonical_subject_ref"], f"{path}.canonical_subject_ref"
        ),
        source_trajectory_refs=_string_tuple(
            body["source_trajectory_refs"],
            f"{path}.source_trajectory_refs",
            minimum_items=1,
        ),
        state=_string(body["state"], f"{path}.state"),
    )


def _load_precondition(value: object, path: str) -> ChangeRequestPrecondition:
    body = _mapping(value, path)
    _exact_fields(
        body,
        path,
        required={"precondition_id", "requirement", "evaluation_state"},
    )
    return ChangeRequestPrecondition(
        precondition_id=_string(
            body["precondition_id"], f"{path}.precondition_id"
        ),
        requirement=_string(body["requirement"], f"{path}.requirement"),
        evaluation_state=_string(
            body["evaluation_state"], f"{path}.evaluation_state"
        ),
    )


def _load_criterion(
    value: object, path: str
) -> ChangeRequestAcceptanceCriterion:
    body = _mapping(value, path)
    _exact_fields(
        body,
        path,
        required={"criterion_id", "requirement", "evaluation_state"},
    )
    return ChangeRequestAcceptanceCriterion(
        criterion_id=_string(body["criterion_id"], f"{path}.criterion_id"),
        requirement=_string(body["requirement"], f"{path}.requirement"),
        evaluation_state=_string(
            body["evaluation_state"], f"{path}.evaluation_state"
        ),
    )


def _load_rollback_operation(value: object, path: str) -> RollbackOperation:
    body = _mapping(value, path)
    _exact_fields(
        body,
        path,
        required={
            "target_object_kind",
            "target_ref",
            "target_path",
            "restore_subject_ref",
            "state",
        },
    )
    return RollbackOperation(
        target_object_kind=_string(
            body["target_object_kind"], f"{path}.target_object_kind"
        ),
        target_ref=_string(body["target_ref"], f"{path}.target_ref"),
        target_path=_string(body["target_path"], f"{path}.target_path"),
        restore_subject_ref=_string(
            body["restore_subject_ref"], f"{path}.restore_subject_ref"
        ),
        state=_string(body["state"], f"{path}.state"),
    )


def _load_rollback_plan(value: object, path: str) -> ObjectGraphRollbackPlan:
    body = _mapping(value, path)
    _exact_fields(
        body,
        path,
        required={
            "restore_operations",
            "preserve_alias_history",
            "require_post_rollback_validation",
            "rollback_authorization_required",
            "rollback_executed",
        },
    )
    restore_raw = body["restore_operations"]
    if not isinstance(restore_raw, Sequence) or isinstance(
        restore_raw, (str, bytes, bytearray)
    ):
        _fail(f"{path}.restore_operations", "must be an array")
    restore = tuple(
        _load_rollback_operation(item, f"{path}.restore_operations[{index}]")
        for index, item in enumerate(restore_raw)
    )
    if len(restore) != 1:
        _fail(f"{path}.restore_operations", "must contain exactly one operation")
    return ObjectGraphRollbackPlan(
        restore_operations=restore,
        preserve_alias_history=_boolean(
            body["preserve_alias_history"], f"{path}.preserve_alias_history"
        ),
        require_post_rollback_validation=_boolean(
            body["require_post_rollback_validation"],
            f"{path}.require_post_rollback_validation",
        ),
        rollback_authorization_required=_boolean(
            body["rollback_authorization_required"],
            f"{path}.rollback_authorization_required",
        ),
        rollback_executed=_boolean(
            body["rollback_executed"], f"{path}.rollback_executed"
        ),
    )


T = TypeVar("T")


def _load_sequence(
    value: object,
    path: str,
    loader: Callable[[object, str], T],
) -> tuple[T, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array")
    return tuple(loader(item, f"{path}[{index}]") for index, item in enumerate(value))


def load_object_graph_change_request(
    payload: Mapping[str, object],
) -> ObjectGraphChangeRequest:
    """Strictly load one serialized GT41 request."""

    root = _mapping(payload, "Object Graph Change Request")
    _exact_fields(root, "artifact root", required={"object_graph_change_request"})
    body = _mapping(
        root["object_graph_change_request"], "object_graph_change_request"
    )
    required = {
        "request_version",
        "change_request_id",
        "created_at",
        "source_proposal_ref",
        "source_approval_record_ref",
        "request_state",
        "request_reason",
        "canonical_subject_ref",
        "merge_subject_ref",
        "object_class",
        "affected_trajectory_refs",
        "change_operations",
        "retained_aliases",
        "preconditions",
        "acceptance_criteria",
        "rollback_plan",
        "proposal_binding_verified",
        "approval_record_binding_verified",
        "approved_scope_verified",
        "request_scope_closed",
        "retained_aliases_preserved",
        "application_review_required",
        "application_authorized",
        "blocked_operations",
        "next_action",
        "change_applied",
        "identity_merge_performed",
        "subject_refs_mutated",
        "object_graph_mutated",
        "world_state_updated",
        "production_output_released",
        "action_authorized",
        "action_executed",
    }
    _exact_fields(body, "object_graph_change_request", required=required)
    if body["request_version"] != OBJECT_GRAPH_CHANGE_REQUEST_FORMAT_VERSION:
        _fail("object_graph_change_request.request_version", "must be '0.1'")

    result = ObjectGraphChangeRequest(
        change_request_id=_string(
            body["change_request_id"],
            "object_graph_change_request.change_request_id",
        ),
        created_at=_timestamp(
            body["created_at"], "object_graph_change_request.created_at"
        ),
        source_proposal_ref=_load_source_proposal_ref(
            body["source_proposal_ref"],
            "object_graph_change_request.source_proposal_ref",
        ),
        source_approval_record_ref=_load_source_approval_ref(
            body["source_approval_record_ref"],
            "object_graph_change_request.source_approval_record_ref",
        ),
        request_state=_string(
            body["request_state"], "object_graph_change_request.request_state"
        ),
        request_reason=_string(
            body["request_reason"], "object_graph_change_request.request_reason"
        ),
        canonical_subject_ref=_string(
            body["canonical_subject_ref"],
            "object_graph_change_request.canonical_subject_ref",
        ),
        merge_subject_ref=_string(
            body["merge_subject_ref"],
            "object_graph_change_request.merge_subject_ref",
        ),
        object_class=_string(
            body["object_class"], "object_graph_change_request.object_class"
        ),
        affected_trajectory_refs=_string_tuple(
            body["affected_trajectory_refs"],
            "object_graph_change_request.affected_trajectory_refs",
            minimum_items=2,
        ),
        change_operations=_load_sequence(
            body["change_operations"],
            "object_graph_change_request.change_operations",
            _load_operation,
        ),
        retained_aliases=_load_sequence(
            body["retained_aliases"],
            "object_graph_change_request.retained_aliases",
            _load_alias,
        ),
        preconditions=_load_sequence(
            body["preconditions"],
            "object_graph_change_request.preconditions",
            _load_precondition,
        ),
        acceptance_criteria=_load_sequence(
            body["acceptance_criteria"],
            "object_graph_change_request.acceptance_criteria",
            _load_criterion,
        ),
        rollback_plan=_load_rollback_plan(
            body["rollback_plan"], "object_graph_change_request.rollback_plan"
        ),
        proposal_binding_verified=_boolean(
            body["proposal_binding_verified"],
            "object_graph_change_request.proposal_binding_verified",
        ),
        approval_record_binding_verified=_boolean(
            body["approval_record_binding_verified"],
            "object_graph_change_request.approval_record_binding_verified",
        ),
        approved_scope_verified=_boolean(
            body["approved_scope_verified"],
            "object_graph_change_request.approved_scope_verified",
        ),
        request_scope_closed=_boolean(
            body["request_scope_closed"],
            "object_graph_change_request.request_scope_closed",
        ),
        retained_aliases_preserved=_boolean(
            body["retained_aliases_preserved"],
            "object_graph_change_request.retained_aliases_preserved",
        ),
        application_review_required=_boolean(
            body["application_review_required"],
            "object_graph_change_request.application_review_required",
        ),
        application_authorized=_boolean(
            body["application_authorized"],
            "object_graph_change_request.application_authorized",
        ),
        blocked_operations=_string_tuple(
            body["blocked_operations"],
            "object_graph_change_request.blocked_operations",
            minimum_items=1,
        ),
        next_action=_string(
            body["next_action"], "object_graph_change_request.next_action"
        ),
        change_applied=_boolean(
            body["change_applied"], "object_graph_change_request.change_applied"
        ),
        identity_merge_performed=_boolean(
            body["identity_merge_performed"],
            "object_graph_change_request.identity_merge_performed",
        ),
        subject_refs_mutated=_boolean(
            body["subject_refs_mutated"],
            "object_graph_change_request.subject_refs_mutated",
        ),
        object_graph_mutated=_boolean(
            body["object_graph_mutated"],
            "object_graph_change_request.object_graph_mutated",
        ),
        world_state_updated=_boolean(
            body["world_state_updated"],
            "object_graph_change_request.world_state_updated",
        ),
        production_output_released=_boolean(
            body["production_output_released"],
            "object_graph_change_request.production_output_released",
        ),
        action_authorized=_boolean(
            body["action_authorized"],
            "object_graph_change_request.action_authorized",
        ),
        action_executed=_boolean(
            body["action_executed"],
            "object_graph_change_request.action_executed",
        ),
    )

    if result.request_state != REQUEST_STATE:
        _fail(
            "object_graph_change_request.request_state",
            f"must be {REQUEST_STATE!r}",
        )
    if result.request_reason != REQUEST_REASON:
        _fail(
            "object_graph_change_request.request_reason",
            f"must be {REQUEST_REASON!r}",
        )
    if result.next_action != NEXT_ACTION:
        _fail(
            "object_graph_change_request.next_action",
            f"must be {NEXT_ACTION!r}",
        )
    if result.canonical_subject_ref == result.merge_subject_ref:
        _fail(
            "object_graph_change_request",
            "canonical and merge subject refs must differ",
        )
    if len(result.affected_trajectory_refs) != 2:
        _fail(
            "object_graph_change_request.affected_trajectory_refs",
            "must contain exactly two refs",
        )
    if len(result.change_operations) != 1:
        _fail(
            "object_graph_change_request.change_operations",
            "must contain exactly one operation",
        )
    operation = result.change_operations[0]
    if operation.operation_kind != "replace_subject_ref":
        _fail(
            "object_graph_change_request.change_operations[0].operation_kind",
            "must be 'replace_subject_ref'",
        )
    if (
        operation.target_object_kind != "trajectory"
        or operation.target_path != "/subject_ref"
    ):
        _fail(
            "object_graph_change_request.change_operations[0]",
            "must target one trajectory /subject_ref",
        )
    if operation.before_subject_ref != result.merge_subject_ref:
        _fail(
            "object_graph_change_request.change_operations[0].before_subject_ref",
            "must equal merge_subject_ref",
        )
    if operation.after_subject_ref != result.canonical_subject_ref:
        _fail(
            "object_graph_change_request.change_operations[0].after_subject_ref",
            "must equal canonical_subject_ref",
        )
    if operation.state != "requested":
        _fail(
            "object_graph_change_request.change_operations[0].state",
            "must be 'requested'",
        )
    if operation.operation_id != f"rewrite-{operation.target_ref}-subject-ref":
        _fail(
            "object_graph_change_request.change_operations[0].operation_id",
            "does not match target_ref",
        )
    if len(result.retained_aliases) != 1:
        _fail(
            "object_graph_change_request.retained_aliases",
            "must contain exactly one alias",
        )
    alias = result.retained_aliases[0]
    if (
        alias.alias_subject_ref != result.merge_subject_ref
        or alias.canonical_subject_ref != result.canonical_subject_ref
    ):
        _fail(
            "object_graph_change_request.retained_aliases[0]",
            "must preserve merge subject as canonical alias",
        )
    if alias.state != "retain_as_alias":
        _fail(
            "object_graph_change_request.retained_aliases[0].state",
            "must be 'retain_as_alias'",
        )
    expected_preconditions = tuple(
        ChangeRequestPrecondition(identifier, requirement, state)
        for identifier, requirement, state in PRECONDITIONS
    )
    if result.preconditions != expected_preconditions:
        _fail(
            "object_graph_change_request.preconditions",
            "must match the required closed set",
        )
    expected_criteria = tuple(
        ChangeRequestAcceptanceCriterion(
            identifier, requirement, "pending_application"
        )
        for identifier, requirement in ACCEPTANCE_CRITERIA
    )
    if result.acceptance_criteria != expected_criteria:
        _fail(
            "object_graph_change_request.acceptance_criteria",
            "must match the required closed set",
        )
    restore = result.rollback_plan.restore_operations[0]
    if restore.target_ref != operation.target_ref:
        _fail(
            "object_graph_change_request.rollback_plan",
            "must target the requested trajectory",
        )
    if restore.restore_subject_ref != operation.before_subject_ref:
        _fail(
            "object_graph_change_request.rollback_plan",
            "must restore the original subject_ref",
        )
    if restore.target_object_kind != "trajectory" or restore.target_path != "/subject_ref":
        _fail(
            "object_graph_change_request.rollback_plan.restore_operations[0]",
            "must target one trajectory /subject_ref",
        )
    if restore.state != "available":
        _fail(
            "object_graph_change_request.rollback_plan.restore_operations[0].state",
            "must be 'available'",
        )
    for field in (
        "preserve_alias_history",
        "require_post_rollback_validation",
        "rollback_authorization_required",
    ):
        if not getattr(result.rollback_plan, field):
            _fail(
                f"object_graph_change_request.rollback_plan.{field}",
                "must be true",
            )
    if result.rollback_plan.rollback_executed:
        _fail(
            "object_graph_change_request.rollback_plan.rollback_executed",
            "must be false",
        )
    for field in (
        "proposal_binding_verified",
        "approval_record_binding_verified",
        "approved_scope_verified",
        "request_scope_closed",
        "retained_aliases_preserved",
        "application_review_required",
    ):
        if not getattr(result, field):
            _fail(f"object_graph_change_request.{field}", "must be true")
    if result.blocked_operations != BLOCKED_OPERATIONS:
        _fail(
            "object_graph_change_request.blocked_operations",
            "must match the required closed set",
        )
    for field in (
        "application_authorized",
        "change_applied",
        "identity_merge_performed",
        "subject_refs_mutated",
        "object_graph_mutated",
        "world_state_updated",
        "production_output_released",
        "action_authorized",
        "action_executed",
    ):
        if getattr(result, field):
            _fail(f"object_graph_change_request.{field}", "must be false")
    return result


def validate_object_graph_change_request_bindings(
    request: ObjectGraphChangeRequest,
    *,
    proposal_bytes: bytes,
    approval_record_bytes: bytes,
) -> None:
    """Rebuild from exact GT39/GT40 bytes and require semantic equality."""

    rebuilt = build_object_graph_change_request(
        change_request_id=request.change_request_id,
        created_at=request.created_at,
        proposal_bytes=proposal_bytes,
        approval_record_bytes=approval_record_bytes,
    )
    if rebuilt.to_dict() != request.to_dict():
        _fail(
            "object_graph_change_request",
            "does not match the request rebuilt from exact bound source bytes",
        )


__all__ = [
    "OBJECT_GRAPH_CHANGE_REQUEST_ARTIFACT_ID",
    "OBJECT_GRAPH_CHANGE_REQUEST_SCHEMA_ID",
    "OBJECT_GRAPH_CHANGE_REQUEST_SCHEMA_VERSION",
    "OBJECT_GRAPH_CHANGE_REQUEST_FORMAT_VERSION",
    "REQUEST_STATE",
    "REQUEST_REASON",
    "NEXT_ACTION",
    "PRECONDITIONS",
    "ACCEPTANCE_CRITERIA",
    "BLOCKED_OPERATIONS",
    "ObjectGraphChangeRequestError",
    "SourceProposalRef",
    "SourceApprovalRecordRef",
    "ObjectGraphChangeOperation",
    "RetainedAliasDeclaration",
    "ChangeRequestPrecondition",
    "ChangeRequestAcceptanceCriterion",
    "RollbackOperation",
    "ObjectGraphRollbackPlan",
    "ObjectGraphChangeRequest",
    "build_object_graph_change_request",
    "load_object_graph_change_request",
    "validate_object_graph_change_request_bindings",
]
