"""Auditable approval records for bounded identity-merge proposals.

The public Artifact binds exact GT39 proposal bytes to one decision for every
required approval role. It can record approval, rejection, or a request for more
evidence. Even a fully approved record only makes a later change request
eligible; it never applies the merge, rewrites references, mutates an object
graph or World State, releases production output, authorizes action, or executes
action.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from geotask_core.v1.identity_merge_proposal import (
    IDENTITY_MERGE_PROPOSAL_ARTIFACT_ID,
    IdentityMergeProposal,
    IdentityMergeProposalError,
    load_identity_merge_proposal,
)


IDENTITY_MERGE_APPROVAL_RECORD_ARTIFACT_ID = (
    "geotask.identity-merge-approval-record"
)
IDENTITY_MERGE_APPROVAL_RECORD_SCHEMA_ID = (
    "https://stpku.github.io/GeoTask/schemas/"
    "geotask-identity-merge-approval-record-v0.1.schema.json"
)
IDENTITY_MERGE_APPROVAL_RECORD_SCHEMA_VERSION = "0.1"
IDENTITY_MERGE_APPROVAL_RECORD_FORMAT_VERSION = "0.1"

RECORD_STATE = "decision_recorded"
APPROVAL_DECISIONS = ("approved", "rejected", "evidence_required")
DECISION_REASON_BY_STATE = {
    "approved": "all_required_approval_roles_approved",
    "rejected": "one_or_more_required_approval_roles_rejected",
    "evidence_required": (
        "one_or_more_required_approval_roles_requested_evidence"
    ),
}
NEXT_ACTION_BY_STATE = {
    "approved": "prepare_identity_merge_change_request",
    "rejected": "close_identity_merge_proposal",
    "evidence_required": "request_identity_merge_evidence",
}
BLOCKED_OPERATIONS = (
    "identity_merge_execution",
    "subject_ref_mutation",
    "object_graph_mutation",
    "world_state_update",
    "production_output_release",
    "action_execution",
)


class IdentityMergeApprovalRecordError(ValueError):
    """Raised when an identity-merge approval record fails closed."""


def _fail(path: str, message: str) -> None:
    raise IdentityMergeApprovalRecordError(f"{path}: {message}")


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
        raise IdentityMergeApprovalRecordError(
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


def _hash_bytes(content: bytes) -> str:
    if not isinstance(content, bytes):
        _fail("proposal_bytes", "must be bytes")
    return hashlib.sha256(content).hexdigest()


def _json_mapping_from_bytes(content: bytes, path: str) -> Mapping[str, object]:
    if not isinstance(content, bytes):
        _fail(path, "must be bytes")
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IdentityMergeApprovalRecordError(
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
class IdentityMergeProposalRef:
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
class IdentityMergeApprovalDecision:
    approval_role: str
    reviewer_ref: str
    decision: str
    rationale: str
    decided_at: str
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "approval_role": self.approval_role,
            "reviewer_ref": self.reviewer_ref,
            "decision": self.decision,
            "rationale": self.rationale,
            "decided_at": self.decided_at,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class IdentityMergeApprovalRecord:
    approval_record_id: str
    created_at: str
    source_proposal_ref: IdentityMergeProposalRef
    record_state: str
    aggregate_decision: str
    decision_reason: str
    canonical_subject_ref: str
    merge_subject_ref: str
    affected_trajectory_refs: tuple[str, ...]
    required_approval_roles: tuple[str, ...]
    approval_decisions: tuple[IdentityMergeApprovalDecision, ...]
    approved_roles: tuple[str, ...]
    rejected_roles: tuple[str, ...]
    evidence_required_roles: tuple[str, ...]
    proposal_binding_verified: bool
    decision_scope_closed: bool
    required_roles_covered: bool
    proposal_approval_complete: bool
    change_request_eligible: bool
    blocked_operations: tuple[str, ...]
    next_action: str
    identity_merge_performed: bool
    subject_refs_mutated: bool
    object_graph_mutated: bool
    world_state_updated: bool
    production_output_released: bool
    action_authorized: bool
    action_executed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "identity_merge_approval_record": {
                "approval_version": IDENTITY_MERGE_APPROVAL_RECORD_FORMAT_VERSION,
                "approval_record_id": self.approval_record_id,
                "created_at": self.created_at,
                "source_proposal_ref": self.source_proposal_ref.to_dict(),
                "record_state": self.record_state,
                "aggregate_decision": self.aggregate_decision,
                "decision_reason": self.decision_reason,
                "canonical_subject_ref": self.canonical_subject_ref,
                "merge_subject_ref": self.merge_subject_ref,
                "affected_trajectory_refs": list(self.affected_trajectory_refs),
                "required_approval_roles": list(self.required_approval_roles),
                "approval_decisions": [
                    item.to_dict() for item in self.approval_decisions
                ],
                "approved_roles": list(self.approved_roles),
                "rejected_roles": list(self.rejected_roles),
                "evidence_required_roles": list(self.evidence_required_roles),
                "proposal_binding_verified": self.proposal_binding_verified,
                "decision_scope_closed": self.decision_scope_closed,
                "required_roles_covered": self.required_roles_covered,
                "proposal_approval_complete": self.proposal_approval_complete,
                "change_request_eligible": self.change_request_eligible,
                "blocked_operations": list(self.blocked_operations),
                "next_action": self.next_action,
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


def _validate_source_proposal(proposal: IdentityMergeProposal) -> None:
    if proposal.proposal_state != "ready_for_review":
        _fail("source proposal.proposal_state", "must be 'ready_for_review'")
    if proposal.next_action != "request_identity_merge_approval":
        _fail(
            "source proposal.next_action",
            "must be 'request_identity_merge_approval'",
        )
    for field in ("source_binding_verified", "scope_closed", "aliases_preserved"):
        if not getattr(proposal, field):
            _fail(f"source proposal.{field}", "must be true")
    for field in (
        "new_identity_created",
        "alias_deleted",
        "proposal_approved",
        "object_graph_mutated",
        "identity_merge_performed",
        "subject_refs_mutated",
        "world_state_updated",
        "production_output_released",
        "action_authorized",
        "action_executed",
    ):
        if getattr(proposal, field):
            _fail(f"source proposal.{field}", "must be false")


def _load_decision_input(value: object, path: str) -> IdentityMergeApprovalDecision:
    body = _mapping(value, path)
    _exact_fields(
        body,
        path,
        required={
            "approval_role",
            "reviewer_ref",
            "decision",
            "rationale",
            "decided_at",
            "evidence_refs",
        },
    )
    decision = _string(body["decision"], f"{path}.decision")
    if decision not in APPROVAL_DECISIONS:
        _fail(
            f"{path}.decision",
            "must be one of " + ", ".join(repr(item) for item in APPROVAL_DECISIONS),
        )
    evidence_refs = _string_tuple(
        body["evidence_refs"], f"{path}.evidence_refs"
    )
    if decision == "evidence_required" and not evidence_refs:
        _fail(
            f"{path}.evidence_refs",
            "must contain at least one requested evidence reference",
        )
    return IdentityMergeApprovalDecision(
        approval_role=_string(body["approval_role"], f"{path}.approval_role"),
        reviewer_ref=_string(body["reviewer_ref"], f"{path}.reviewer_ref"),
        decision=decision,
        rationale=_string(body["rationale"], f"{path}.rationale"),
        decided_at=_timestamp(body["decided_at"], f"{path}.decided_at"),
        evidence_refs=evidence_refs,
    )


def _normalize_decisions(
    decisions: Sequence[Mapping[str, object]],
    *,
    required_roles: tuple[str, ...],
) -> tuple[IdentityMergeApprovalDecision, ...]:
    if not isinstance(decisions, Sequence) or isinstance(
        decisions, (str, bytes, bytearray)
    ):
        _fail("approval_decisions", "must be an array")
    by_role: dict[str, IdentityMergeApprovalDecision] = {}
    for index, item in enumerate(decisions):
        decision = _load_decision_input(item, f"approval_decisions[{index}]")
        if decision.approval_role not in required_roles:
            _fail(
                f"approval_decisions[{index}].approval_role",
                "must be one of the proposal required_approvals",
            )
        if decision.approval_role in by_role:
            _fail(
                f"approval_decisions[{index}].approval_role",
                f"duplicates {decision.approval_role!r}",
            )
        by_role[decision.approval_role] = decision
    missing = [role for role in required_roles if role not in by_role]
    if missing:
        _fail(
            "approval_decisions",
            "must cover every required approval role: " + ", ".join(missing),
        )
    if len(by_role) != len(required_roles):
        _fail("approval_decisions", "must cover each required role exactly once")
    return tuple(by_role[role] for role in required_roles)


def _aggregate_decision(
    decisions: tuple[IdentityMergeApprovalDecision, ...],
) -> str:
    states = {item.decision for item in decisions}
    if "rejected" in states:
        return "rejected"
    if "evidence_required" in states:
        return "evidence_required"
    return "approved"


def build_identity_merge_approval_record(
    *,
    approval_record_id: str,
    created_at: str,
    proposal_bytes: bytes,
    approval_decisions: Sequence[Mapping[str, object]],
) -> IdentityMergeApprovalRecord:
    """Build one exact-bound, non-executing GT40 approval record."""

    approval_record_id = _string(approval_record_id, "approval_record_id")
    created_at = _timestamp(created_at, "created_at")
    payload = _json_mapping_from_bytes(proposal_bytes, "proposal_bytes")
    try:
        proposal = load_identity_merge_proposal(payload)
    except IdentityMergeProposalError as exc:
        raise IdentityMergeApprovalRecordError(str(exc)) from exc
    _validate_source_proposal(proposal)

    required_roles = proposal.required_approvals
    decisions = _normalize_decisions(
        approval_decisions,
        required_roles=required_roles,
    )
    aggregate = _aggregate_decision(decisions)
    approved_roles = tuple(
        item.approval_role for item in decisions if item.decision == "approved"
    )
    rejected_roles = tuple(
        item.approval_role for item in decisions if item.decision == "rejected"
    )
    evidence_required_roles = tuple(
        item.approval_role
        for item in decisions
        if item.decision == "evidence_required"
    )
    complete = aggregate == "approved"

    return IdentityMergeApprovalRecord(
        approval_record_id=approval_record_id,
        created_at=created_at,
        source_proposal_ref=IdentityMergeProposalRef(
            artifact_id=IDENTITY_MERGE_PROPOSAL_ARTIFACT_ID,
            proposal_id=proposal.proposal_id,
            content_sha256=_hash_bytes(proposal_bytes),
        ),
        record_state=RECORD_STATE,
        aggregate_decision=aggregate,
        decision_reason=DECISION_REASON_BY_STATE[aggregate],
        canonical_subject_ref=proposal.canonical_subject_ref,
        merge_subject_ref=proposal.merge_subject_ref,
        affected_trajectory_refs=proposal.affected_trajectory_refs,
        required_approval_roles=required_roles,
        approval_decisions=decisions,
        approved_roles=approved_roles,
        rejected_roles=rejected_roles,
        evidence_required_roles=evidence_required_roles,
        proposal_binding_verified=True,
        decision_scope_closed=True,
        required_roles_covered=True,
        proposal_approval_complete=complete,
        change_request_eligible=complete,
        blocked_operations=BLOCKED_OPERATIONS,
        next_action=NEXT_ACTION_BY_STATE[aggregate],
        identity_merge_performed=False,
        subject_refs_mutated=False,
        object_graph_mutated=False,
        world_state_updated=False,
        production_output_released=False,
        action_authorized=False,
        action_executed=False,
    )


def _load_source_ref(value: object, path: str) -> IdentityMergeProposalRef:
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
    return IdentityMergeProposalRef(
        artifact_id=artifact_id,
        proposal_id=_string(body["proposal_id"], f"{path}.proposal_id"),
        content_sha256=_sha256(body["content_sha256"], f"{path}.content_sha256"),
    )


def _load_decisions(
    value: object,
    path: str,
) -> tuple[IdentityMergeApprovalDecision, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array")
    result = tuple(
        _load_decision_input(item, f"{path}[{index}]")
        for index, item in enumerate(value)
    )
    if not result:
        _fail(path, "must contain at least one decision")
    return result


def load_identity_merge_approval_record(
    payload: Mapping[str, object],
) -> IdentityMergeApprovalRecord:
    """Strictly load one serialized identity-merge approval record."""

    root = _mapping(payload, "Identity Merge Approval Record")
    _exact_fields(root, "artifact root", required={"identity_merge_approval_record"})
    body = _mapping(
        root["identity_merge_approval_record"],
        "identity_merge_approval_record",
    )
    required = {
        "approval_version",
        "approval_record_id",
        "created_at",
        "source_proposal_ref",
        "record_state",
        "aggregate_decision",
        "decision_reason",
        "canonical_subject_ref",
        "merge_subject_ref",
        "affected_trajectory_refs",
        "required_approval_roles",
        "approval_decisions",
        "approved_roles",
        "rejected_roles",
        "evidence_required_roles",
        "proposal_binding_verified",
        "decision_scope_closed",
        "required_roles_covered",
        "proposal_approval_complete",
        "change_request_eligible",
        "blocked_operations",
        "next_action",
        "identity_merge_performed",
        "subject_refs_mutated",
        "object_graph_mutated",
        "world_state_updated",
        "production_output_released",
        "action_authorized",
        "action_executed",
    }
    _exact_fields(body, "identity_merge_approval_record", required=required)
    if body["approval_version"] != IDENTITY_MERGE_APPROVAL_RECORD_FORMAT_VERSION:
        _fail(
            "identity_merge_approval_record.approval_version",
            f"must be {IDENTITY_MERGE_APPROVAL_RECORD_FORMAT_VERSION!r}",
        )

    result = IdentityMergeApprovalRecord(
        approval_record_id=_string(
            body["approval_record_id"],
            "identity_merge_approval_record.approval_record_id",
        ),
        created_at=_timestamp(
            body["created_at"], "identity_merge_approval_record.created_at"
        ),
        source_proposal_ref=_load_source_ref(
            body["source_proposal_ref"],
            "identity_merge_approval_record.source_proposal_ref",
        ),
        record_state=_string(
            body["record_state"], "identity_merge_approval_record.record_state"
        ),
        aggregate_decision=_string(
            body["aggregate_decision"],
            "identity_merge_approval_record.aggregate_decision",
        ),
        decision_reason=_string(
            body["decision_reason"],
            "identity_merge_approval_record.decision_reason",
        ),
        canonical_subject_ref=_string(
            body["canonical_subject_ref"],
            "identity_merge_approval_record.canonical_subject_ref",
        ),
        merge_subject_ref=_string(
            body["merge_subject_ref"],
            "identity_merge_approval_record.merge_subject_ref",
        ),
        affected_trajectory_refs=_string_tuple(
            body["affected_trajectory_refs"],
            "identity_merge_approval_record.affected_trajectory_refs",
            minimum_items=2,
        ),
        required_approval_roles=_string_tuple(
            body["required_approval_roles"],
            "identity_merge_approval_record.required_approval_roles",
            minimum_items=1,
        ),
        approval_decisions=_load_decisions(
            body["approval_decisions"],
            "identity_merge_approval_record.approval_decisions",
        ),
        approved_roles=_string_tuple(
            body["approved_roles"],
            "identity_merge_approval_record.approved_roles",
        ),
        rejected_roles=_string_tuple(
            body["rejected_roles"],
            "identity_merge_approval_record.rejected_roles",
        ),
        evidence_required_roles=_string_tuple(
            body["evidence_required_roles"],
            "identity_merge_approval_record.evidence_required_roles",
        ),
        proposal_binding_verified=_boolean(
            body["proposal_binding_verified"],
            "identity_merge_approval_record.proposal_binding_verified",
        ),
        decision_scope_closed=_boolean(
            body["decision_scope_closed"],
            "identity_merge_approval_record.decision_scope_closed",
        ),
        required_roles_covered=_boolean(
            body["required_roles_covered"],
            "identity_merge_approval_record.required_roles_covered",
        ),
        proposal_approval_complete=_boolean(
            body["proposal_approval_complete"],
            "identity_merge_approval_record.proposal_approval_complete",
        ),
        change_request_eligible=_boolean(
            body["change_request_eligible"],
            "identity_merge_approval_record.change_request_eligible",
        ),
        blocked_operations=_string_tuple(
            body["blocked_operations"],
            "identity_merge_approval_record.blocked_operations",
            minimum_items=1,
        ),
        next_action=_string(
            body["next_action"], "identity_merge_approval_record.next_action"
        ),
        identity_merge_performed=_boolean(
            body["identity_merge_performed"],
            "identity_merge_approval_record.identity_merge_performed",
        ),
        subject_refs_mutated=_boolean(
            body["subject_refs_mutated"],
            "identity_merge_approval_record.subject_refs_mutated",
        ),
        object_graph_mutated=_boolean(
            body["object_graph_mutated"],
            "identity_merge_approval_record.object_graph_mutated",
        ),
        world_state_updated=_boolean(
            body["world_state_updated"],
            "identity_merge_approval_record.world_state_updated",
        ),
        production_output_released=_boolean(
            body["production_output_released"],
            "identity_merge_approval_record.production_output_released",
        ),
        action_authorized=_boolean(
            body["action_authorized"],
            "identity_merge_approval_record.action_authorized",
        ),
        action_executed=_boolean(
            body["action_executed"],
            "identity_merge_approval_record.action_executed",
        ),
    )

    if result.record_state != RECORD_STATE:
        _fail(
            "identity_merge_approval_record.record_state",
            f"must be {RECORD_STATE!r}",
        )
    if result.aggregate_decision not in APPROVAL_DECISIONS:
        _fail(
            "identity_merge_approval_record.aggregate_decision",
            "must be a supported decision state",
        )
    if result.decision_reason != DECISION_REASON_BY_STATE[result.aggregate_decision]:
        _fail(
            "identity_merge_approval_record.decision_reason",
            "does not match aggregate_decision",
        )
    if result.next_action != NEXT_ACTION_BY_STATE[result.aggregate_decision]:
        _fail(
            "identity_merge_approval_record.next_action",
            "does not match aggregate_decision",
        )
    if result.canonical_subject_ref == result.merge_subject_ref:
        _fail(
            "identity_merge_approval_record",
            "canonical and merge subject refs must differ",
        )
    if len(result.affected_trajectory_refs) != 2:
        _fail(
            "identity_merge_approval_record.affected_trajectory_refs",
            "must contain exactly two refs",
        )
    decision_roles = tuple(item.approval_role for item in result.approval_decisions)
    if decision_roles != result.required_approval_roles:
        _fail(
            "identity_merge_approval_record.approval_decisions",
            "must cover required roles exactly once and in declared order",
        )
    derived_aggregate = _aggregate_decision(result.approval_decisions)
    if derived_aggregate != result.aggregate_decision:
        _fail(
            "identity_merge_approval_record.aggregate_decision",
            "does not match approval decisions",
        )
    derived_approved = tuple(
        item.approval_role
        for item in result.approval_decisions
        if item.decision == "approved"
    )
    derived_rejected = tuple(
        item.approval_role
        for item in result.approval_decisions
        if item.decision == "rejected"
    )
    derived_evidence = tuple(
        item.approval_role
        for item in result.approval_decisions
        if item.decision == "evidence_required"
    )
    if result.approved_roles != derived_approved:
        _fail("identity_merge_approval_record.approved_roles", "does not match decisions")
    if result.rejected_roles != derived_rejected:
        _fail("identity_merge_approval_record.rejected_roles", "does not match decisions")
    if result.evidence_required_roles != derived_evidence:
        _fail(
            "identity_merge_approval_record.evidence_required_roles",
            "does not match decisions",
        )
    for field in (
        "proposal_binding_verified",
        "decision_scope_closed",
        "required_roles_covered",
    ):
        if not getattr(result, field):
            _fail(f"identity_merge_approval_record.{field}", "must be true")
    expected_complete = result.aggregate_decision == "approved"
    if result.proposal_approval_complete is not expected_complete:
        _fail(
            "identity_merge_approval_record.proposal_approval_complete",
            "must be true only for approved aggregate decision",
        )
    if result.change_request_eligible is not expected_complete:
        _fail(
            "identity_merge_approval_record.change_request_eligible",
            "must be true only for approved aggregate decision",
        )
    if result.blocked_operations != BLOCKED_OPERATIONS:
        _fail(
            "identity_merge_approval_record.blocked_operations",
            "must match the required closed set",
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
        if getattr(result, field):
            _fail(f"identity_merge_approval_record.{field}", "must be false")
    return result


def validate_identity_merge_approval_record_bindings(
    record: IdentityMergeApprovalRecord,
    *,
    proposal_bytes: bytes,
) -> None:
    """Rebuild from exact GT39 bytes and require semantic equality."""

    decisions = tuple(item.to_dict() for item in record.approval_decisions)
    rebuilt = build_identity_merge_approval_record(
        approval_record_id=record.approval_record_id,
        created_at=record.created_at,
        proposal_bytes=proposal_bytes,
        approval_decisions=decisions,
    )
    if rebuilt.to_dict() != record.to_dict():
        _fail(
            "identity_merge_approval_record",
            "does not match the record rebuilt from exact bound proposal bytes",
        )


__all__ = [
    "IDENTITY_MERGE_APPROVAL_RECORD_ARTIFACT_ID",
    "IDENTITY_MERGE_APPROVAL_RECORD_SCHEMA_ID",
    "IDENTITY_MERGE_APPROVAL_RECORD_SCHEMA_VERSION",
    "IDENTITY_MERGE_APPROVAL_RECORD_FORMAT_VERSION",
    "APPROVAL_DECISIONS",
    "BLOCKED_OPERATIONS",
    "IdentityMergeApprovalRecordError",
    "IdentityMergeProposalRef",
    "IdentityMergeApprovalDecision",
    "IdentityMergeApprovalRecord",
    "build_identity_merge_approval_record",
    "load_identity_merge_approval_record",
    "validate_identity_merge_approval_record_bindings",
]
