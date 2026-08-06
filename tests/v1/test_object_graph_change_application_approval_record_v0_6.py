"""GT42 object-graph change application approval record tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from geotask_core import (
    OBJECT_GRAPH_CHANGE_APPLICATION_APPROVAL_RECORD_ARTIFACT_ID,
    OBJECT_GRAPH_CHANGE_APPLICATION_APPROVAL_RECORD_SCHEMA_ID,
    OBJECT_GRAPH_CHANGE_APPLICATION_APPROVAL_RECORD_SCHEMA_VERSION,
    ObjectGraphChangeApplicationApprovalRecordError,
    build_object_graph_change_application_approval_record,
    load_object_graph_change_application_approval_record,
    validate_artifact_payload,
    validate_object_graph_change_application_approval_record_bindings,
)


ROOT = Path(__file__).resolve().parents[2]
REQUEST = ROOT / "examples/core/object_graph_change_request_gt41.json"
APPROVAL = (
    ROOT / "examples/core/object_graph_change_application_approval_record_gt42.json"
)
SCHEMA = (
    ROOT
    / "schemas/geotask-object-graph-change-application-approval-record-v0.1.schema.json"
)
ROLES = ("object_graph_change_owner", "world_state_governance_reviewer")


def _decisions(
    *,
    owner: str = "approved",
    governance: str = "approved",
) -> tuple[dict[str, object], ...]:
    return (
        {
            "approval_role": ROLES[0],
            "reviewer_ref": "reviewer-owner",
            "decision": owner,
            "rationale": "Object-graph owner decision.",
            "decided_at": "2026-08-06T11:20:00+08:00",
            "evidence_refs": ["owner-evidence"] if owner == "evidence_required" else [],
        },
        {
            "approval_role": ROLES[1],
            "reviewer_ref": "reviewer-governance",
            "decision": governance,
            "rationale": "World-state governance decision.",
            "decided_at": "2026-08-06T11:25:00+08:00",
            "evidence_refs": (
                ["governance-evidence"]
                if governance == "evidence_required"
                else []
            ),
        },
    )


def _build(*, decisions=None, roles=ROLES):
    return build_object_graph_change_application_approval_record(
        approval_record_id="test-gt42-approval",
        created_at="2026-08-06T11:30:00+08:00",
        change_request_bytes=REQUEST.read_bytes(),
        required_approval_roles=roles,
        approval_decisions=decisions or _decisions(),
    )


def test_public_constants_are_stable() -> None:
    assert OBJECT_GRAPH_CHANGE_APPLICATION_APPROVAL_RECORD_ARTIFACT_ID == (
        "geotask.object-graph-change-application-approval-record"
    )
    assert OBJECT_GRAPH_CHANGE_APPLICATION_APPROVAL_RECORD_SCHEMA_ID.endswith(
        "geotask-object-graph-change-application-approval-record-v0.1.schema.json"
    )
    assert OBJECT_GRAPH_CHANGE_APPLICATION_APPROVAL_RECORD_SCHEMA_VERSION == "0.1"


def test_all_required_roles_approve_without_authorizing_or_applying_change() -> None:
    record = _build()
    assert record.aggregate_decision == "approved"
    assert record.approved_roles == ROLES
    assert record.application_approval_complete is True
    assert record.change_application_eligible is True
    assert record.next_action == "prepare_bounded_object_graph_change_application"
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
        assert getattr(record, field) is False


def test_rejection_takes_precedence() -> None:
    record = _build(decisions=_decisions(owner="rejected", governance="evidence_required"))
    assert record.aggregate_decision == "rejected"
    assert record.rejected_roles == (ROLES[0],)
    assert record.application_approval_complete is False
    assert record.change_application_eligible is False
    assert record.next_action == "close_object_graph_change_request"


def test_evidence_required_keeps_application_blocked() -> None:
    record = _build(decisions=_decisions(governance="evidence_required"))
    assert record.aggregate_decision == "evidence_required"
    assert record.evidence_required_roles == (ROLES[1],)
    assert record.application_approval_complete is False
    assert record.change_application_eligible is False
    assert record.next_action == "request_object_graph_change_application_evidence"


def test_builder_requires_unique_roles_and_exact_decision_coverage() -> None:
    with pytest.raises(
        ObjectGraphChangeApplicationApprovalRecordError,
        match="duplicates",
    ):
        _build(roles=(ROLES[0], ROLES[0]))
    with pytest.raises(
        ObjectGraphChangeApplicationApprovalRecordError,
        match="must cover every",
    ):
        _build(decisions=_decisions()[:1])


def test_evidence_required_requires_reference() -> None:
    decisions = list(_decisions(governance="evidence_required"))
    decisions[1]["evidence_refs"] = []
    with pytest.raises(
        ObjectGraphChangeApplicationApprovalRecordError,
        match="at least one",
    ):
        _build(decisions=tuple(decisions))


def test_loader_rejects_authorization_execution_and_derived_tampering() -> None:
    payload = _build().to_dict()
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
        tampered = copy.deepcopy(payload)
        tampered["object_graph_change_application_approval_record"][field] = True
        with pytest.raises(
            ObjectGraphChangeApplicationApprovalRecordError,
            match="must be false",
        ):
            load_object_graph_change_application_approval_record(tampered)

    wrong = copy.deepcopy(payload)
    wrong["object_graph_change_application_approval_record"][
        "aggregate_decision"
    ] = "rejected"
    with pytest.raises(
        ObjectGraphChangeApplicationApprovalRecordError,
        match="decision_reason",
    ):
        load_object_graph_change_application_approval_record(wrong)


def test_exact_binding_detects_insignificant_source_byte_change() -> None:
    record = _build()
    changed = REQUEST.read_bytes().replace(b"{\n", b"{  \n", 1)
    with pytest.raises(
        ObjectGraphChangeApplicationApprovalRecordError,
        match="exact bound",
    ):
        validate_object_graph_change_application_approval_record_bindings(
            record,
            change_request_bytes=changed,
        )


def test_fixed_artifact_matches_schema_and_exact_binding() -> None:
    payload = json.loads(APPROVAL.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    record = load_object_graph_change_application_approval_record(payload)
    validate_object_graph_change_application_approval_record_bindings(
        record,
        change_request_bytes=REQUEST.read_bytes(),
    )


def test_generic_validation_is_structural_not_exact_replay() -> None:
    payload = json.loads(APPROVAL.read_text(encoding="utf-8"))
    report = validate_artifact_payload(
        OBJECT_GRAPH_CHANGE_APPLICATION_APPROVAL_RECORD_ARTIFACT_ID,
        payload,
        file=APPROVAL.as_posix(),
    )
    assert report.valid is True
    assert report.summary["aggregate_decision"] == "approved"
    assert report.summary["change_request_binding_verified"] is False
    assert report.summary["application_approval_complete"] is True
    assert report.summary["change_application_eligible"] is True
    assert report.summary["application_authorized"] is False
    assert report.summary["change_applied"] is False
