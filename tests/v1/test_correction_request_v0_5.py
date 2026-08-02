"""Contract tests for GeoTask Correction Request v0.1."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import geotask_core
import geotask_core.v1 as v1
from geotask_core.v1.correction_request import (
    CORRECTION_REQUEST_SCHEMA_ID,
    CORRECTION_REQUEST_SCHEMA_VERSION,
    CorrectionRequestFormatError,
    load_correction_request,
    validate_correction_request_bindings,
)
from geotask_core.v1.artifact_validation import validate_artifact_payload
from geotask_core.v1.discrepancy_report import load_discrepancy_report
from geotask_core.v1.world_state import load_world_state


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "examples" / "core"
EXAMPLE = CORE / "correction_request_uav_recheck.json"
WORLD_STATE = CORE / "world_state_uav_separation_recheck.json"
DISCREPANCY_REPORT = CORE / "discrepancy_report_uav_recheck.json"
TASK = CORE / "uav_route_crossing_temporal_separation.yaml"
SCHEMA = ROOT / "schemas" / "geotask-correction-request-v0.1.schema.json"
EXPECTED_FINGERPRINT = "b180cd17b6c243bbde7327fe2348fa8e307a0aa11075eb512c42dc802a9d92d7"


def _payload() -> dict[str, object]:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def _world_state():
    return load_world_state(json.loads(WORLD_STATE.read_text(encoding="utf-8")))


def _report():
    return load_discrepancy_report(
        json.loads(DISCREPANCY_REPORT.read_text(encoding="utf-8"))
    )


def _reports():
    return {"discrepancy-uav-recheck": _report()}


def _artifact_contents() -> dict[str, bytes]:
    return {
        "base-world-state": WORLD_STATE.read_bytes(),
        "discrepancy-uav-recheck": DISCREPANCY_REPORT.read_bytes(),
        "task-gt16": TASK.read_bytes(),
    }


def test_correction_request_example_loads_round_trips_and_binds() -> None:
    request = load_correction_request(_payload())

    assert request.request_id == "fictional-uav-separation-correction-request"
    assert request.state == "required"
    assert request.next_action == "materialize_successor_state"
    assert request.base_world_state.revision == 2
    assert request.output_contract.minimum_revision == 3
    assert len(request.discrepancy_refs) == 1
    assert len(request.changes) == 2
    assert len(request.acceptance_criteria) == 5
    assert request.semantic_fingerprint() == EXPECTED_FINGERPRINT
    assert load_correction_request(request.to_dict()) == request

    validate_correction_request_bindings(
        request,
        _world_state(),
        _reports(),
        _artifact_contents(),
    )


def test_correction_request_schema_is_valid_and_accepts_example() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    payload = _payload()

    Draft202012Validator.check_schema(schema)
    assert schema["$id"] == CORRECTION_REQUEST_SCHEMA_ID
    assert schema["properties"]["correction_request"]["$ref"] == (
        "#/$defs/correctionRequest"
    )
    assert list(Draft202012Validator(schema).iter_errors(payload)) == []
    assert payload["correction_request"]["schema_version"] == (
        CORRECTION_REQUEST_SCHEMA_VERSION
    )


def test_correction_request_unified_validation_preserves_execution_boundaries() -> None:
    validation = validate_artifact_payload(
        "geotask.correction-request",
        _payload(),
        file=EXAMPLE.as_posix(),
    )

    assert validation.valid is True
    assert validation.schema_verified is True
    summary = validation.summary
    assert summary["request_id"] == "fictional-uav-separation-correction-request"
    assert summary["state"] == "required"
    assert summary["base_world_state_revision"] == 2
    assert summary["minimum_successor_revision"] == 3
    assert summary["change_count"] == 2
    assert summary["acceptance_criterion_count"] == 5
    assert summary["semantic_fingerprint"] == EXPECTED_FINGERPRINT
    for key in (
        "base_world_state_binding_verified",
        "discrepancy_report_bindings_verified",
        "artifact_bindings_verified",
        "correction_scope_verified",
        "changes_applied",
        "successor_world_state_materialized",
        "acceptance_criteria_evaluated",
        "discrepancies_resolved",
        "rechecks_executed",
        "outputs_released",
        "external_truth_verified",
        "action_authorized",
    ):
        assert summary[key] is False


def test_correction_request_fingerprint_is_collection_order_invariant() -> None:
    original = _payload()
    reordered = copy.deepcopy(original)
    body = reordered["correction_request"]
    body["discrepancy_report_refs"].reverse()
    body["supporting_artifact_refs"].reverse()
    body["observation_refs"].reverse()
    body["evidence_refs"].reverse()
    body["discrepancy_refs"].reverse()
    body["changes"].reverse()
    body["acceptance_criteria"].reverse()
    body["blocked_outputs"].reverse()
    body["blocked_actions"].reverse()
    for item in body["changes"]:
        item["basis_refs"].reverse()
        item["observation_refs"].reverse()
        item["evidence_refs"].reverse()
        item["input_fields"].reverse()
        item["acceptance_criterion_refs"].reverse()

    assert load_correction_request(original).semantic_fingerprint() == (
        load_correction_request(reordered).semantic_fingerprint()
    )


def test_correction_request_rejects_time_identity_and_output_contract_errors() -> None:
    payload = _payload()
    payload["correction_request"]["created_at"] = "2026-07-16T10:00:59+08:00"
    with pytest.raises(CorrectionRequestFormatError, match="must not be earlier"):
        load_correction_request(payload)

    payload = _payload()
    payload["correction_request"]["base_world_state"]["artifact_id"] = (
        "geotask.document"
    )
    with pytest.raises(CorrectionRequestFormatError, match="geotask.world-state"):
        load_correction_request(payload)

    payload = _payload()
    payload["correction_request"]["output_contract"]["minimum_revision"] = 2
    with pytest.raises(CorrectionRequestFormatError, match="must be greater"):
        load_correction_request(payload)

    payload = _payload()
    payload["correction_request"]["output_contract"][
        "preserve_immutable_paths"
    ] = False
    with pytest.raises(CorrectionRequestFormatError, match="must be true"):
        load_correction_request(payload)


def test_correction_request_enforces_operation_value_rules() -> None:
    payload = _payload()
    del payload["correction_request"]["changes"][0]["before"]
    with pytest.raises(CorrectionRequestFormatError, match="recompute.*requires before"):
        load_correction_request(payload)

    payload = _payload()
    payload["correction_request"]["changes"][0]["after"] = 60
    with pytest.raises(CorrectionRequestFormatError, match="recompute.*forbids after"):
        load_correction_request(payload)

    payload = _payload()
    change = payload["correction_request"]["changes"][0]
    change["operation"] = "replace"
    change["after"] = 60
    change["input_fields"] = []
    with pytest.raises(CorrectionRequestFormatError, match="different before/after"):
        load_correction_request(payload)


def test_correction_request_enforces_operation_acceptance_criteria() -> None:
    payload = _payload()
    payload["correction_request"]["changes"][0]["acceptance_criterion_refs"] = [
        "successor-world-state-valid"
    ]
    with pytest.raises(CorrectionRequestFormatError, match="path_recomputed"):
        load_correction_request(payload)

    payload = _payload()
    criterion = payload["correction_request"]["acceptance_criteria"][0]
    criterion["kind"] = "path_equals"
    with pytest.raises(CorrectionRequestFormatError, match="requires target_path and expected"):
        load_correction_request(payload)

    payload = _payload()
    criterion = payload["correction_request"]["acceptance_criteria"][4]
    criterion["output_refs"] = []
    with pytest.raises(CorrectionRequestFormatError, match="requires at least one output_ref"):
        load_correction_request(payload)


def test_correction_request_enforces_reference_closure_and_uniqueness() -> None:
    payload = _payload()
    payload["correction_request"]["changes"][0]["basis_refs"].append("missing")
    with pytest.raises(CorrectionRequestFormatError, match="must be declared"):
        load_correction_request(payload)

    payload = _payload()
    payload["correction_request"]["supporting_artifact_refs"][0]["ref_id"] = (
        "base-world-state"
    )
    with pytest.raises(CorrectionRequestFormatError, match="duplicates ref_id"):
        load_correction_request(payload)

    payload = _payload()
    duplicate = copy.deepcopy(payload["correction_request"]["changes"][0])
    payload["correction_request"]["changes"].append(duplicate)
    with pytest.raises(CorrectionRequestFormatError, match="duplicates id"):
        load_correction_request(payload)


def test_correction_request_enforces_required_state_shape() -> None:
    payload = _payload()
    payload["correction_request"]["changes"] = []
    with pytest.raises(CorrectionRequestFormatError, match="state 'required' requires changes"):
        load_correction_request(payload)

    payload = _payload()
    payload["correction_request"]["next_action"] = "none"
    with pytest.raises(CorrectionRequestFormatError, match="materialize_successor_state"):
        load_correction_request(payload)

    payload = _payload()
    payload["correction_request"]["blocked_outputs"] = []
    payload["correction_request"]["blocked_actions"] = []
    with pytest.raises(CorrectionRequestFormatError, match="must block at least one"):
        load_correction_request(payload)


def test_correction_request_supports_need_review_and_blocked_shapes() -> None:
    payload = _payload()
    body = payload["correction_request"]
    body["state"] = "need_review"
    body["changes"] = []
    body["next_action"] = "human_review"
    body["review_requirements"] = [
        {
            "id": "review-separation-correction",
            "discrepancy_refs": ["separation-mismatch"],
            "reviewer_role": "authorized_safety_reviewer",
            "reason": "Confirm whether the successor-state correction may proceed.",
            "affected_paths": ["/relations/uav-temporal-separation/value"],
            "basis_refs": ["discrepancy-uav-recheck"],
        }
    ]
    body["acceptance_criteria"] = [
        {
            "id": "review-completed",
            "kind": "human_reviewed",
            "reason": "An authorized safety reviewer must record the decision.",
            "output_refs": [],
            "reviewer_role": "authorized_safety_reviewer",
        }
    ]
    request = load_correction_request(payload)
    assert request.state == "need_review"

    payload = _payload()
    body = payload["correction_request"]
    body["state"] = "blocked"
    body["next_action"] = "none"
    body["changes"] = []
    body["review_requirements"] = []
    body["acceptance_criteria"] = []
    body["discrepancy_refs"][0]["discrepancy_id"] = "initial-temporal-result-stale"
    request = load_correction_request(payload)
    validate_correction_request_bindings(
        request,
        _world_state(),
        _reports(),
        _artifact_contents(),
    )
    assert request.state == "blocked"


def test_correction_request_binding_rejects_world_state_and_report_mismatch() -> None:
    payload = _payload()
    payload["correction_request"]["base_world_state"]["semantic_fingerprint"] = "0" * 64
    request = load_correction_request(payload)
    with pytest.raises(CorrectionRequestFormatError, match="does not match bound"):
        validate_correction_request_bindings(
            request,
            _world_state(),
            _reports(),
            _artifact_contents(),
        )

    request = load_correction_request(_payload())
    with pytest.raises(CorrectionRequestFormatError, match="missing report_ref"):
        validate_correction_request_bindings(
            request,
            _world_state(),
            {},
            _artifact_contents(),
        )


def test_correction_request_binding_rejects_missing_unknown_and_modified_bytes() -> None:
    request = load_correction_request(_payload())

    contents = _artifact_contents()
    del contents["task-gt16"]
    with pytest.raises(CorrectionRequestFormatError, match="missing ref_id"):
        validate_correction_request_bindings(
            request, _world_state(), _reports(), contents
        )

    contents = _artifact_contents()
    contents["extra"] = b"{}"
    with pytest.raises(CorrectionRequestFormatError, match="unknown ref_id"):
        validate_correction_request_bindings(
            request, _world_state(), _reports(), contents
        )

    contents = _artifact_contents()
    contents["base-world-state"] += b"\n"
    with pytest.raises(CorrectionRequestFormatError, match="SHA-256 mismatch"):
        validate_correction_request_bindings(
            request, _world_state(), _reports(), contents
        )


def test_correction_request_binding_rejects_paths_outside_mutable_scope() -> None:
    payload = _payload()
    payload["correction_request"]["changes"][0]["subject_kind"] = "attribute"
    payload["correction_request"]["changes"][0]["target_path"] = (
        "/objects/uav-a/attributes/route_id/value"
    )
    payload["correction_request"]["acceptance_criteria"][0]["target_path"] = (
        "/objects/uav-a/attributes/route_id/value"
    )
    request = load_correction_request(payload)
    with pytest.raises(CorrectionRequestFormatError, match="outside.*mutable_paths"):
        validate_correction_request_bindings(
            request,
            _world_state(),
            _reports(),
            _artifact_contents(),
        )


def test_correction_request_binding_rejects_wrong_observed_before_value() -> None:
    payload = _payload()
    payload["correction_request"]["changes"][1]["before"] = 80
    request = load_correction_request(payload)
    with pytest.raises(CorrectionRequestFormatError, match="observed value"):
        validate_correction_request_bindings(
            request,
            _world_state(),
            _reports(),
            _artifact_contents(),
        )


def test_correction_request_binding_rejects_unbound_observation_or_evidence() -> None:
    payload = _payload()
    payload["correction_request"]["observation_refs"].append("obs-not-bound")
    payload["correction_request"]["changes"][0]["observation_refs"].append(
        "obs-not-bound"
    )
    request = load_correction_request(payload)
    with pytest.raises(CorrectionRequestFormatError, match="not declared by bound"):
        validate_correction_request_bindings(
            request,
            _world_state(),
            _reports(),
            _artifact_contents(),
        )

    payload = _payload()
    payload["correction_request"]["evidence_refs"].append("evidence:not-bound")
    payload["correction_request"]["changes"][0]["evidence_refs"].append(
        "evidence:not-bound"
    )
    request = load_correction_request(payload)
    with pytest.raises(CorrectionRequestFormatError, match="not declared by bound"):
        validate_correction_request_bindings(
            request,
            _world_state(),
            _reports(),
            _artifact_contents(),
        )


def test_correction_request_forbids_identity_provenance_and_overlapping_changes() -> None:
    payload = _payload()
    payload["correction_request"]["changes"][0]["target_path"] = (
        "/objects/uav-b/attributes/delay_seconds/name"
    )
    payload["correction_request"]["acceptance_criteria"][0]["target_path"] = (
        "/objects/uav-b/attributes/delay_seconds/name"
    )
    with pytest.raises(CorrectionRequestFormatError, match="intrinsically immutable"):
        load_correction_request(payload)

    payload = _payload()
    duplicate = copy.deepcopy(payload["correction_request"]["changes"][0])
    duplicate["id"] = "duplicate-delay-correction"
    payload["correction_request"]["changes"].append(duplicate)
    with pytest.raises(CorrectionRequestFormatError, match="duplicate or overlap"):
        load_correction_request(payload)


def test_correction_request_binding_anchors_before_to_base_world_state() -> None:
    payload = _payload()
    payload["correction_request"]["changes"][0]["before"] = 30
    request = load_correction_request(payload)

    with pytest.raises(CorrectionRequestFormatError, match="base World State"):
        validate_correction_request_bindings(
            request,
            _world_state(),
            _reports(),
            _artifact_contents(),
        )


def test_correction_request_requires_complete_acceptance_closure() -> None:
    payload = _payload()
    body = payload["correction_request"]
    body["acceptance_criteria"] = [
        item
        for item in body["acceptance_criteria"]
        if item["id"] != "separation-discrepancy-resolved"
    ]
    body["changes"][1]["acceptance_criterion_refs"].remove(
        "separation-discrepancy-resolved"
    )
    with pytest.raises(CorrectionRequestFormatError, match="discrepancy_resolved"):
        load_correction_request(payload)

    payload = _payload()
    body = payload["correction_request"]
    body["acceptance_criteria"] = [
        item
        for item in body["acceptance_criteria"]
        if item["id"] != "successor-world-state-valid"
    ]
    for change in body["changes"]:
        change["acceptance_criterion_refs"].remove("successor-world-state-valid")
    with pytest.raises(CorrectionRequestFormatError, match="artifact_valid"):
        load_correction_request(payload)

    payload = _payload()
    body = payload["correction_request"]
    body["acceptance_criteria"] = [
        item
        for item in body["acceptance_criteria"]
        if item["id"] != "temporal-output-rechecked"
    ]
    with pytest.raises(CorrectionRequestFormatError, match="every blocked_output"):
        load_correction_request(payload)


def test_correction_request_need_review_requires_role_coverage() -> None:
    payload = _payload()
    body = payload["correction_request"]
    body["state"] = "need_review"
    body["changes"] = []
    body["next_action"] = "human_review"
    body["review_requirements"] = [
        {
            "id": "review-separation-correction",
            "discrepancy_refs": ["separation-mismatch"],
            "reviewer_role": "authorized_safety_reviewer",
            "reason": "Confirm whether the successor-state correction may proceed.",
            "affected_paths": ["/relations/uav-temporal-separation/value"],
            "basis_refs": ["discrepancy-uav-recheck"],
        }
    ]
    body["acceptance_criteria"] = [
        {
            "id": "review-completed",
            "kind": "human_reviewed",
            "reason": "A different reviewer role must not satisfy this requirement.",
            "output_refs": [],
            "reviewer_role": "unrelated_reviewer",
        }
    ]
    with pytest.raises(CorrectionRequestFormatError, match="reviewer_role"):
        load_correction_request(payload)


def test_correction_request_public_python_namespaces_export_contract() -> None:
    for namespace in (geotask_core, v1):
        assert namespace.CORRECTION_REQUEST_ARTIFACT_ID == "geotask.correction-request"
        assert namespace.CORRECTION_REQUEST_SCHEMA_ID == CORRECTION_REQUEST_SCHEMA_ID
        assert namespace.CORRECTION_REQUEST_SCHEMA_VERSION == "0.1"
        assert namespace.CORRECTION_REQUEST_FORMAT_VERSION == "0.1"
        assert namespace.load_correction_request is load_correction_request
        assert (
            namespace.validate_correction_request_bindings
            is validate_correction_request_bindings
        )
        assert namespace.CorrectionRequest.__name__ == "CorrectionRequest"
