"""GT41 object-graph change-request contract tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from geotask_core import validate_artifact_payload
from geotask_core.v1.object_graph_change_request import (
    OBJECT_GRAPH_CHANGE_REQUEST_ARTIFACT_ID,
    OBJECT_GRAPH_CHANGE_REQUEST_SCHEMA_ID,
    OBJECT_GRAPH_CHANGE_REQUEST_SCHEMA_VERSION,
    ObjectGraphChangeRequestError,
    build_object_graph_change_request,
    load_object_graph_change_request,
    validate_object_graph_change_request_bindings,
)


ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / "examples/core/identity_merge_proposal_gt39.json"
APPROVAL = ROOT / "examples/core/identity_merge_approval_record_gt40.json"
REQUEST = ROOT / "examples/core/object_graph_change_request_gt41.json"
SCHEMA = ROOT / "schemas/geotask-object-graph-change-request-v0.1.schema.json"


def _build():
    return build_object_graph_change_request(
        change_request_id="gt41-provisional-subject-object-graph-change",
        created_at="2026-08-06T09:30:00+08:00",
        proposal_bytes=PROPOSAL.read_bytes(),
        approval_record_bytes=APPROVAL.read_bytes(),
    )


def test_public_constants_are_stable() -> None:
    assert OBJECT_GRAPH_CHANGE_REQUEST_ARTIFACT_ID == "geotask.object-graph-change-request"
    assert OBJECT_GRAPH_CHANGE_REQUEST_SCHEMA_ID.endswith(
        "geotask-object-graph-change-request-v0.1.schema.json"
    )
    assert OBJECT_GRAPH_CHANGE_REQUEST_SCHEMA_VERSION == "0.1"


def test_approved_sources_create_one_closed_non_applying_request() -> None:
    request = _build()
    assert request.request_state == "ready_for_application_review"
    assert request.next_action == "request_object_graph_change_application_approval"
    assert len(request.change_operations) == 1
    operation = request.change_operations[0]
    assert operation.target_ref == "track_beta"
    assert operation.target_path == "/subject_ref"
    assert operation.before_subject_ref == "provisional_beta"
    assert operation.after_subject_ref == "provisional_alpha"
    assert len(request.preconditions) == 7
    assert len(request.acceptance_criteria) == 5
    assert request.application_review_required is True
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
        assert getattr(request, field) is False


def test_builder_rejects_nonapproved_approval_record() -> None:
    payload = json.loads(APPROVAL.read_text(encoding="utf-8"))
    body = payload["identity_merge_approval_record"]
    body["aggregate_decision"] = "rejected"
    body["decision_reason"] = "one_or_more_required_approval_roles_rejected"
    body["approval_decisions"][0]["decision"] = "rejected"
    body["approved_roles"] = ["world_state_maintainer"]
    body["rejected_roles"] = ["identity_governance_reviewer"]
    body["proposal_approval_complete"] = False
    body["change_request_eligible"] = False
    body["next_action"] = "close_identity_merge_proposal"
    changed = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode()
    with pytest.raises(ObjectGraphChangeRequestError, match="must be 'approved'"):
        build_object_graph_change_request(
            change_request_id="rejected-request",
            created_at="2026-08-06T09:30:00+08:00",
            proposal_bytes=PROPOSAL.read_bytes(),
            approval_record_bytes=changed,
        )


def test_builder_rejects_approval_record_bound_to_other_proposal_bytes() -> None:
    changed_proposal = PROPOSAL.read_bytes().replace(b"{\n", b"{  \n", 1)
    with pytest.raises(ObjectGraphChangeRequestError, match="exact bound"):
        build_object_graph_change_request(
            change_request_id="mismatch-request",
            created_at="2026-08-06T09:30:00+08:00",
            proposal_bytes=changed_proposal,
            approval_record_bytes=APPROVAL.read_bytes(),
        )


def test_strict_loader_rejects_scope_expansion_and_execution_claims() -> None:
    payload = _build().to_dict()
    expanded = copy.deepcopy(payload)
    expanded["object_graph_change_request"]["change_operations"].append(
        copy.deepcopy(expanded["object_graph_change_request"]["change_operations"][0])
    )
    with pytest.raises(ObjectGraphChangeRequestError, match="exactly one"):
        load_object_graph_change_request(expanded)

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
        tampered["object_graph_change_request"][field] = True
        with pytest.raises(ObjectGraphChangeRequestError, match="must be false"):
            load_object_graph_change_request(tampered)


def test_strict_loader_rejects_changed_path_alias_or_rollback() -> None:
    payload = _build().to_dict()
    wrong_path = copy.deepcopy(payload)
    wrong_path["object_graph_change_request"]["change_operations"][0]["target_path"] = "/identity"
    with pytest.raises(ObjectGraphChangeRequestError, match="trajectory /subject_ref"):
        load_object_graph_change_request(wrong_path)

    wrong_alias = copy.deepcopy(payload)
    wrong_alias["object_graph_change_request"]["retained_aliases"][0]["state"] = "deleted"
    with pytest.raises(ObjectGraphChangeRequestError, match="retain_as_alias"):
        load_object_graph_change_request(wrong_alias)

    wrong_rollback = copy.deepcopy(payload)
    wrong_rollback["object_graph_change_request"]["rollback_plan"]["restore_operations"][0]["restore_subject_ref"] = "other"
    with pytest.raises(ObjectGraphChangeRequestError, match="restore the original"):
        load_object_graph_change_request(wrong_rollback)


def test_exact_binding_detects_source_byte_changes() -> None:
    request = _build()
    changed_approval = APPROVAL.read_bytes().replace(b"{\n", b"{  \n", 1)
    with pytest.raises(ObjectGraphChangeRequestError, match="exact bound"):
        validate_object_graph_change_request_bindings(
            request,
            proposal_bytes=PROPOSAL.read_bytes(),
            approval_record_bytes=changed_approval,
        )


def test_fixed_artifact_matches_schema_and_exact_binding() -> None:
    payload = json.loads(REQUEST.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    request = load_object_graph_change_request(payload)
    validate_object_graph_change_request_bindings(
        request,
        proposal_bytes=PROPOSAL.read_bytes(),
        approval_record_bytes=APPROVAL.read_bytes(),
    )


def test_generic_artifact_validation_is_structural_not_exact_replay() -> None:
    payload = json.loads(REQUEST.read_text(encoding="utf-8"))
    report = validate_artifact_payload(
        OBJECT_GRAPH_CHANGE_REQUEST_ARTIFACT_ID,
        payload,
        file=REQUEST.as_posix(),
    )
    assert report.valid is True
    assert report.summary["request_state"] == "ready_for_application_review"
    assert report.summary["change_operation_count"] == 1
    assert report.summary["proposal_binding_verified"] is False
    assert report.summary["approval_record_binding_verified"] is False
    assert report.summary["application_authorized"] is False
    assert report.summary["change_applied"] is False
    assert report.summary["object_graph_mutated"] is False


def test_fixed_artifact_is_deterministic() -> None:
    assert _build().to_dict() == json.loads(REQUEST.read_text(encoding="utf-8"))
