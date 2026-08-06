"""Auditable application-approval records for GT41 object-graph change requests.

GT42 binds exact GT41 request bytes to one explicit decision for every
caller-declared required application-approval role. A fully approved record only
makes a later bounded application Artifact eligible. It never authorizes or
applies the change, mutates references, the object graph, or World State,
releases production output, authorizes action, or executes action.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from geotask_core.v1.object_graph_change_request import (
    OBJECT_GRAPH_CHANGE_REQUEST_ARTIFACT_ID,
    ObjectGraphChangeRequest,
    ObjectGraphChangeRequestError,
    load_object_graph_change_request,
)


OBJECT_GRAPH_CHANGE_APPLICATION_APPROVAL_RECORD_ARTIFACT_ID = (
    "geotask.object-graph-change-application-approval-record"
)
OBJECT_GRAPH_CHANGE_APPLICATION_APPROVAL_RECORD_SCHEMA_ID = (
    "https://stpku.github.io/GeoTask/schemas/"
    "geotask-object-graph-change-application-approval-record-v0.1.schema.json"
)
OBJECT_GRAPH_CHANGE_APPLICATION_APPROVAL_RECORD_SCHEMA_VERSION = "0.1"
OBJECT_GRAPH_CHANGE_APPLICATION_APPROVAL_RECORD_FORMAT_VERSION = "0.1"

RECORD_STATE = "decision_recorded"
APPROVAL_DECISIONS = ("approved", "rejected", "evidence_required")
DECISION_REASON_BY_STATE = {
    "approved": "all_required_application_approval_roles_approved",
    "rejected": "one_or_more_application_approval_roles_rejected",
    "evidence_required": (
        "one_or_more_application_approval_roles_requested_evidence"
    ),
}
NEXT_ACTION_BY_STATE = {
    "approved": "prepare_bounded_object_graph_change_application",
    "rejected": "close_object_graph_change_request",
    "evidence_required": "request_object_graph_change_application_evidence",
}
BLOCKED_OPERATIONS = (
    "unapproved_change_application",
    "undeclared_path_mutation",
    "alias_deletion",
    "identity_creation",
    "world_state_update",
    "production_output_release",
    "action_execution",
)


class ObjectGraphChangeApplicationApprovalRecordError(ValueError):
    """Raised when a GT42 application-approval record fails closed."""


def _fail(path: str, message: str) -> None:
    raise ObjectGraphChangeApplicationApprovalRecordError(f"{path}: {message}")


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
        raise ObjectGraphChangeApplicationApprovalRecordError(
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
        _fail("change_request_bytes", "must be bytes")
    return hashlib.sha256(content).hexdigest()


def _json_mapping_from_bytes(content: bytes, path: str) -> Mapping[str, object]:
    if not isinstance(content, bytes):
        _fail(path, "must be bytes")
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ObjectGraphChangeApplicationApprovalRecordError(
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
class ObjectGraphChangeRequestRef:
    artifact_id: str
    change_request_id: str
    content_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "change_request_id": self.change_request_id,
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class ObjectGraphChangeApplicationApprovalDecision:
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
class ObjectGraphChangeApplicationApprovalRecord:
    approval_record_id: str
    created_at: str
    source_change_request_ref: ObjectGraphChangeRequestRef
    record_state: str
    aggregate_decision: str
    decision_reason: str
    canonical_subject_ref: str
    merge_subject_ref: str
    affected_trajectory_refs: tuple[str, ...]
    required_approval_roles: tuple[str, ...]
    approval_decisions: tuple[ObjectGraphChangeApplicationApprovalDecision, ...]
    approved_roles: tuple[str, ...]
    rejected_roles: tuple[str, ...]
    evidence_required_roles: tuple[str, ...]
    change_request_binding_verified: bool
    decision_scope_closed: bool
    required_roles_covered: bool
    application_approval_complete: bool
    change_application_eligible: bool
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
            "object_graph_change_application_approval_record": {
                "approval_version": (
                    OBJECT_GRAPH_CHANGE_APPLICATION_APPROVAL_RECORD_FORMAT_VERSION
                ),
                "approval_record_id": self.approval_record_id,
                "created_at": self.created_at,
                "source_change_request_ref": self.source_change_request_ref.to_dict(),
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
                "change_request_binding_verified": (
                    self.change_request_binding_verified
                ),
                "decision_scope_closed": self.decision_scope_closed,
                "required_roles_covered": self.required_roles_covered,
                "application_approval_complete": self.application_approval_complete,
                "change_application_eligible": self.change_application_eligible,
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


def _validate_source_request(request: ObjectGraphChangeRequest) -> None:
    if request.request_state != "ready_for_application_review":
        _fail("source request.request_state", "must be 'ready_for_application_review'")
    if request.next_action != "request_object_graph_change_application_approval":
        _fail(
            "source request.next_action",
            "must be 'request_object_graph_change_application_approval'",
        )
    for field in (
        "proposal_binding_verified",
        "approval_record_binding_verified",
        "approved_scope_verified",
        "request_scope_closed",
        "retained_aliases_preserved",
        "application_review_required",
    ):
        if not getattr(request, field):
            _fail(f"source request.{field}", "must be true")
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
        if getattr(request, field):
            _fail(f"source request.{field}", "must be false")


def _load_decision_input(
    value: object,
    path: str,
) -> ObjectGraphChangeApplicationApprovalDecision:
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
        _fail(f"{path}.decision", "must be approved, rejected, or evidence_required")
    evidence_refs = _string_tuple(body["evidence_refs"], f"{path}.evidence_refs")
    if decision == "evidence_required" and not evidence_refs:
        _fail(
            f"{path}.evidence_refs",
            "must contain at least one requested evidence reference",
        )
    return ObjectGraphChangeApplicationApprovalDecision(
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
) -> tuple[ObjectGraphChangeApplicationApprovalDecision, ...]:
    if not isinstance(decisions, Sequence) or isinstance(
        decisions, (str, bytes, bytearray)
    ):
        _fail("approval_decisions", "must be an array")
    by_role: dict[str, ObjectGraphChangeApplicationApprovalDecision] = {}
    for index, item in enumerate(decisions):
        decision = _load_decision_input(item, f"approval_decisions[{index}]")
        if decision.approval_role not in required_roles:
            _fail(
                f"approval_decisions[{index}].approval_role",
                "must be one of the declared required approval roles",
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
    decisions: tuple[ObjectGraphChangeApplicationApprovalDecision, ...],
) -> str:
    states = {item.decision for item in decisions}
    if "rejected" in states:
        return "rejected"
    if "evidence_required" in states:
        return "evidence_required"
    return "approved"


def build_object_graph_change_application_approval_record(
    *,
    approval_record_id: str,
    created_at: str,
    change_request_bytes: bytes,
    required_approval_roles: Sequence[str],
    approval_decisions: Sequence[Mapping[str, object]],
) -> ObjectGraphChangeApplicationApprovalRecord:
    """Build one exact-bound, non-executing GT42 approval record."""

    approval_record_id = _string(approval_record_id, "approval_record_id")
    created_at = _timestamp(created_at, "created_at")
    roles = _string_tuple(
        required_approval_roles,
        "required_approval_roles",
        minimum_items=1,
    )
    payload = _json_mapping_from_bytes(change_request_bytes, "change_request_bytes")
    try:
        request = load_object_graph_change_request(payload)
    except ObjectGraphChangeRequestError as exc:
        raise ObjectGraphChangeApplicationApprovalRecordError(str(exc)) from exc
    _validate_source_request(request)

    decisions = _normalize_decisions(approval_decisions, required_roles=roles)
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

    return ObjectGraphChangeApplicationApprovalRecord(
        approval_record_id=approval_record_id,
        created_at=created_at,
        source_change_request_ref=ObjectGraphChangeRequestRef(
            artifact_id=OBJECT_GRAPH_CHANGE_REQUEST_ARTIFACT_ID,
            change_request_id=request.change_request_id,
            content_sha256=_hash_bytes(change_request_bytes),
        ),
        record_state=RECORD_STATE,
        aggregate_decision=aggregate,
        decision_reason=DECISION_REASON_BY_STATE[aggregate],
        canonical_subject_ref=request.canonical_subject_ref,
        merge_subject_ref=request.merge_subject_ref,
        affected_trajectory_refs=request.affected_trajectory_refs,
        required_approval_roles=roles,
        approval_decisions=decisions,
        approved_roles=approved_roles,
        rejected_roles=rejected_roles,
        evidence_required_roles=evidence_required_roles,
        change_request_binding_verified=True,
        decision_scope_closed=True,
        required_roles_covered=True,
        application_approval_complete=complete,
        change_application_eligible=complete,
        application_authorized=False,
        blocked_operations=BLOCKED_OPERATIONS,
        next_action=NEXT_ACTION_BY_STATE[aggregate],
        change_applied=False,
        identity_merge_performed=False,
        subject_refs_mutated=False,
        object_graph_mutated=False,
        world_state_updated=False,
        production_output_released=False,
        action_authorized=False,
        action_executed=False,
    )


def _load_source_ref(value: object, path: str) -> ObjectGraphChangeRequestRef:
    body = _mapping(value, path)
    _exact_fields(
        body,
        path,
        required={"artifact_id", "change_request_id", "content_sha256"},
    )
    artifact_id = _string(body["artifact_id"], f"{path}.artifact_id")
    if artifact_id != OBJECT_GRAPH_CHANGE_REQUEST_ARTIFACT_ID:
        _fail(
            f"{path}.artifact_id",
            f"must be {OBJECT_GRAPH_CHANGE_REQUEST_ARTIFACT_ID!r}",
        )
    return ObjectGraphChangeRequestRef(
        artifact_id=artifact_id,
        change_request_id=_string(
            body["change_request_id"], f"{path}.change_request_id"
        ),
        content_sha256=_sha256(body["content_sha256"], f"{path}.content_sha256"),
    )


def _load_decisions(
    value: object,
    path: str,
) -> tuple[ObjectGraphChangeApplicationApprovalDecision, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array")
    result = tuple(
        _load_decision_input(item, f"{path}[{index}]")
        for index, item in enumerate(value)
    )
    if not result:
        _fail(path, "must contain at least one decision")
    return result


def load_object_graph_change_application_approval_record(
    payload: Mapping[str, object],
) -> ObjectGraphChangeApplicationApprovalRecord:
    """Strictly load one serialized GT42 application-approval record."""

    root = _mapping(payload, "Object Graph Change Application Approval Record")
    _exact_fields(
        root,
        "artifact root",
        required={"object_graph_change_application_approval_record"},
    )
    body = _mapping(
        root["object_graph_change_application_approval_record"],
        "object_graph_change_application_approval_record",
    )
    required = {
        "approval_version",
        "approval_record_id",
        "created_at",
        "source_change_request_ref",
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
        "change_request_binding_verified",
        "decision_scope_closed",
        "required_roles_covered",
        "application_approval_complete",
        "change_application_eligible",
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
    _exact_fields(
        body,
        "object_graph_change_application_approval_record",
        required=required,
    )
    if body["approval_version"] != (
        OBJECT_GRAPH_CHANGE_APPLICATION_APPROVAL_RECORD_FORMAT_VERSION
    ):
        _fail(
            "object_graph_change_application_approval_record.approval_version",
            "must be '0.1'",
        )

    prefix = "object_graph_change_application_approval_record"
    result = ObjectGraphChangeApplicationApprovalRecord(
        approval_record_id=_string(
            body["approval_record_id"], f"{prefix}.approval_record_id"
        ),
        created_at=_timestamp(body["created_at"], f"{prefix}.created_at"),
        source_change_request_ref=_load_source_ref(
            body["source_change_request_ref"], f"{prefix}.source_change_request_ref"
        ),
        record_state=_string(body["record_state"], f"{prefix}.record_state"),
        aggregate_decision=_string(
            body["aggregate_decision"], f"{prefix}.aggregate_decision"
        ),
        decision_reason=_string(
            body["decision_reason"], f"{prefix}.decision_reason"
        ),
        canonical_subject_ref=_string(
            body["canonical_subject_ref"], f"{prefix}.canonical_subject_ref"
        ),
        merge_subject_ref=_string(
            body["merge_subject_ref"], f"{prefix}.merge_subject_ref"
        ),
        affected_trajectory_refs=_string_tuple(
            body["affected_trajectory_refs"],
            f"{prefix}.affected_trajectory_refs",
            minimum_items=2,
        ),
        required_approval_roles=_string_tuple(
            body["required_approval_roles"],
            f"{prefix}.required_approval_roles",
            minimum_items=1,
        ),
        approval_decisions=_load_decisions(
            body["approval_decisions"], f"{prefix}.approval_decisions"
        ),
        approved_roles=_string_tuple(
            body["approved_roles"], f"{prefix}.approved_roles"
        ),
        rejected_roles=_string_tuple(
            body["rejected_roles"], f"{prefix}.rejected_roles"
        ),
        evidence_required_roles=_string_tuple(
            body["evidence_required_roles"], f"{prefix}.evidence_required_roles"
        ),
        change_request_binding_verified=_boolean(
            body["change_request_binding_verified"],
            f"{prefix}.change_request_binding_verified",
        ),
        decision_scope_closed=_boolean(
            body["decision_scope_closed"], f"{prefix}.decision_scope_closed"
        ),
        required_roles_covered=_boolean(
            body["required_roles_covered"], f"{prefix}.required_roles_covered"
        ),
        application_approval_complete=_boolean(
            body["application_approval_complete"],
            f"{prefix}.application_approval_complete",
        ),
        change_application_eligible=_boolean(
            body["change_application_eligible"],
            f"{prefix}.change_application_eligible",
        ),
        application_authorized=_boolean(
            body["application_authorized"], f"{prefix}.application_authorized"
        ),
        blocked_operations=_string_tuple(
            body["blocked_operations"],
            f"{prefix}.blocked_operations",
            minimum_items=1,
        ),
        next_action=_string(body["next_action"], f"{prefix}.next_action"),
        change_applied=_boolean(body["change_applied"], f"{prefix}.change_applied"),
        identity_merge_performed=_boolean(
            body["identity_merge_performed"], f"{prefix}.identity_merge_performed"
        ),
        subject_refs_mutated=_boolean(
            body["subject_refs_mutated"], f"{prefix}.subject_refs_mutated"
        ),
        object_graph_mutated=_boolean(
            body["object_graph_mutated"], f"{prefix}.object_graph_mutated"
        ),
        world_state_updated=_boolean(
            body["world_state_updated"], f"{prefix}.world_state_updated"
        ),
        production_output_released=_boolean(
            body["production_output_released"],
            f"{prefix}.production_output_released",
        ),
        action_authorized=_boolean(
            body["action_authorized"], f"{prefix}.action_authorized"
        ),
        action_executed=_boolean(
            body["action_executed"], f"{prefix}.action_executed"
        ),
    )

    if result.record_state != RECORD_STATE:
        _fail(f"{prefix}.record_state", f"must be {RECORD_STATE!r}")
    if result.aggregate_decision not in APPROVAL_DECISIONS:
        _fail(f"{prefix}.aggregate_decision", "must be a supported decision state")
    if result.decision_reason != DECISION_REASON_BY_STATE[result.aggregate_decision]:
        _fail(f"{prefix}.decision_reason", "does not match aggregate_decision")
    if result.next_action != NEXT_ACTION_BY_STATE[result.aggregate_decision]:
        _fail(f"{prefix}.next_action", "does not match aggregate_decision")
    if result.canonical_subject_ref == result.merge_subject_ref:
        _fail(prefix, "canonical and merge subject refs must differ")
    if len(result.affected_trajectory_refs) != 2:
        _fail(f"{prefix}.affected_trajectory_refs", "must contain exactly two refs")
    decision_roles = tuple(item.approval_role for item in result.approval_decisions)
    if decision_roles != result.required_approval_roles:
        _fail(
            f"{prefix}.approval_decisions",
            "must cover required roles exactly once and in declared order",
        )
    derived_aggregate = _aggregate_decision(result.approval_decisions)
    if derived_aggregate != result.aggregate_decision:
        _fail(f"{prefix}.aggregate_decision", "does not match approval decisions")
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
        _fail(f"{prefix}.approved_roles", "does not match decisions")
    if result.rejected_roles != derived_rejected:
        _fail(f"{prefix}.rejected_roles", "does not match decisions")
    if result.evidence_required_roles != derived_evidence:
        _fail(f"{prefix}.evidence_required_roles", "does not match decisions")
    for field in (
        "change_request_binding_verified",
        "decision_scope_closed",
        "required_roles_covered",
    ):
        if not getattr(result, field):
            _fail(f"{prefix}.{field}", "must be true")
    expected_complete = result.aggregate_decision == "approved"
    if result.application_approval_complete is not expected_complete:
        _fail(
            f"{prefix}.application_approval_complete",
            "must be true only for approved aggregate decision",
        )
    if result.change_application_eligible is not expected_complete:
        _fail(
            f"{prefix}.change_application_eligible",
            "must be true only for approved aggregate decision",
        )
    if result.blocked_operations != BLOCKED_OPERATIONS:
        _fail(f"{prefix}.blocked_operations", "must match the required closed set")
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
            _fail(f"{prefix}.{field}", "must be false")
    return result


def validate_object_graph_change_application_approval_record_bindings(
    record: ObjectGraphChangeApplicationApprovalRecord,
    *,
    change_request_bytes: bytes,
) -> None:
    """Rebuild from exact GT41 bytes and require semantic equality."""

    rebuilt = build_object_graph_change_application_approval_record(
        approval_record_id=record.approval_record_id,
        created_at=record.created_at,
        change_request_bytes=change_request_bytes,
        required_approval_roles=record.required_approval_roles,
        approval_decisions=tuple(item.to_dict() for item in record.approval_decisions),
    )
    if rebuilt.to_dict() != record.to_dict():
        _fail(
            "object_graph_change_application_approval_record",
            "does not match the record rebuilt from exact bound GT41 bytes",
        )


__all__ = [
    "OBJECT_GRAPH_CHANGE_APPLICATION_APPROVAL_RECORD_ARTIFACT_ID",
    "OBJECT_GRAPH_CHANGE_APPLICATION_APPROVAL_RECORD_SCHEMA_ID",
    "OBJECT_GRAPH_CHANGE_APPLICATION_APPROVAL_RECORD_SCHEMA_VERSION",
    "OBJECT_GRAPH_CHANGE_APPLICATION_APPROVAL_RECORD_FORMAT_VERSION",
    "APPROVAL_DECISIONS",
    "BLOCKED_OPERATIONS",
    "ObjectGraphChangeApplicationApprovalRecordError",
    "ObjectGraphChangeRequestRef",
    "ObjectGraphChangeApplicationApprovalDecision",
    "ObjectGraphChangeApplicationApprovalRecord",
    "build_object_graph_change_application_approval_record",
    "load_object_graph_change_application_approval_record",
    "validate_object_graph_change_application_approval_record_bindings",
]
