"""Contract tests for GeoTask Discrepancy Report v0.1."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from geotask_core.v1.discrepancy_report import (
    DISCREPANCY_REPORT_SCHEMA_ID,
    DISCREPANCY_REPORT_SCHEMA_VERSION,
    DiscrepancyReportFormatError,
    load_discrepancy_report,
    validate_discrepancy_report_bindings,
)
from geotask_core.v1.artifact_validation import validate_artifact_payload
from geotask_core.v1.world_state import load_world_state


ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "core" / "discrepancy_report_uav_recheck.json"
WORLD_STATE = ROOT / "examples" / "core" / "world_state_uav_separation_recheck.json"
SCHEMA = ROOT / "schemas" / "geotask-discrepancy-report-v0.1.schema.json"
EXAMPLE_ROOT = ROOT / "examples" / "core"
EXPECTED_FINGERPRINT = "2a3ba961082b4bc550858449c4cb0f059f3c2e330898478580d6bf94abfd7612"


def _payload() -> dict[str, object]:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def _world_state_payload() -> dict[str, object]:
    return json.loads(WORLD_STATE.read_text(encoding="utf-8"))


def _artifact_contents() -> dict[str, bytes]:
    return {
        "task-gt16": (
            EXAMPLE_ROOT / "uav_route_crossing_temporal_separation.yaml"
        ).read_bytes(),
        "result-gt16-initial": (
            EXAMPLE_ROOT / "verification_session_uav_execution_result.json"
        ).read_bytes(),
        "transition-uav-recheck": (
            EXAMPLE_ROOT / "state_transition_uav_separation_recheck.json"
        ).read_bytes(),
        "session-uav-recheck": (
            EXAMPLE_ROOT / "verification_session_uav_recheck.json"
        ).read_bytes(),
    }


def test_discrepancy_report_example_loads_round_trips_and_binds() -> None:
    report = load_discrepancy_report(_payload())
    world_state = load_world_state(_world_state_payload())

    assert report.report_id == "fictional-uav-separation-discrepancy-report"
    assert report.state == "confirmed"
    assert report.severity == "high"
    assert len(report.artifact_refs) == 4
    assert len(report.discrepancies) == 2
    assert report.discrepancies[0].id == "initial-temporal-result-stale"
    assert report.discrepancies[1].id == "temporal-separation-value-mismatch"
    assert report.semantic_fingerprint() == EXPECTED_FINGERPRINT
    assert load_discrepancy_report(report.to_dict()) == report

    validate_discrepancy_report_bindings(report, world_state, _artifact_contents())


def test_discrepancy_report_schema_is_valid_and_accepts_example() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    payload = _payload()

    Draft202012Validator.check_schema(schema)
    assert schema["$id"] == DISCREPANCY_REPORT_SCHEMA_ID
    assert schema["properties"]["discrepancy_report"]["$ref"] == (
        "#/$defs/discrepancyReport"
    )
    assert list(Draft202012Validator(schema).iter_errors(payload)) == []
    assert payload["discrepancy_report"]["schema_version"] == (
        DISCREPANCY_REPORT_SCHEMA_VERSION
    )


def test_discrepancy_report_unified_validation_summary_preserves_boundaries() -> None:
    validation = validate_artifact_payload(
        "geotask.discrepancy-report",
        _payload(),
        file=str(EXAMPLE),
    )

    assert validation.valid is True
    assert validation.schema_verified is True
    summary = validation.summary
    assert summary["report_id"] == "fictional-uav-separation-discrepancy-report"
    assert summary["state"] == "confirmed"
    assert summary["severity"] == "high"
    assert summary["discrepancy_count"] == 2
    assert summary["confirmed_discrepancy_count"] == 2
    assert summary["artifact_ref_count"] == 4
    assert summary["affected_path_count"] == 3
    assert summary["mutable_path_count"] == 2
    assert summary["immutable_path_count"] == 4
    assert summary["semantic_fingerprint"] == EXPECTED_FINGERPRINT
    for key in (
        "world_state_binding_verified",
        "artifact_bindings_verified",
        "source_artifact_semantics_verified",
        "discrepancies_computed",
        "impact_propagated",
        "correction_request_created",
        "corrections_applied",
        "world_state_materialized",
        "rechecks_executed",
        "external_truth_verified",
        "action_authorized",
    ):
        assert summary[key] is False


def test_discrepancy_report_fingerprint_is_collection_order_invariant() -> None:
    original = _payload()
    reordered = copy.deepcopy(original)
    body = reordered["discrepancy_report"]
    body["artifact_refs"].reverse()
    body["observation_refs"].reverse()
    body["evidence_refs"].reverse()
    body["discrepancies"].reverse()
    for item in body["discrepancies"]:
        item["basis_refs"].reverse()
        item["observation_refs"].reverse()
        item["evidence_refs"].reverse()
        item["impact"]["affected_paths"].reverse()
        item["impact"]["affected_assertion_refs"].reverse()
        item["impact"]["affected_output_refs"].reverse()
        item["impact"]["affected_action_refs"].reverse()
        item["correction_scope"]["mutable_paths"].reverse()
        item["correction_scope"]["immutable_paths"].reverse()

    assert load_discrepancy_report(original).semantic_fingerprint() == (
        load_discrepancy_report(reordered).semantic_fingerprint()
    )


def test_discrepancy_report_rejects_invalid_time_and_identity() -> None:
    payload = _payload()
    payload["discrepancy_report"]["recorded_at"] = "2026-07-16T09:59:00+08:00"
    with pytest.raises(DiscrepancyReportFormatError, match="must not be earlier"):
        load_discrepancy_report(payload)

    payload = _payload()
    payload["discrepancy_report"]["schema_id"] = "https://example.invalid/schema"
    with pytest.raises(DiscrepancyReportFormatError, match="schema_id"):
        load_discrepancy_report(payload)


def test_discrepancy_report_enforces_kind_specific_value_shape() -> None:
    payload = _payload()
    del payload["discrepancy_report"]["discrepancies"][0]["observed"]
    with pytest.raises(DiscrepancyReportFormatError, match="requires both expected and observed"):
        load_discrepancy_report(payload)

    payload = _payload()
    item = payload["discrepancy_report"]["discrepancies"][0]
    item["observed"] = item["expected"]
    with pytest.raises(DiscrepancyReportFormatError, match="to differ"):
        load_discrepancy_report(payload)

    payload = _payload()
    item = payload["discrepancy_report"]["discrepancies"][0]
    item["kind"] = "missing_claim"
    del item["observed"]
    load_discrepancy_report(payload)

    payload = _payload()
    item = payload["discrepancy_report"]["discrepancies"][0]
    item["kind"] = "unexpected_claim"
    del item["expected"]
    load_discrepancy_report(payload)


def test_discrepancy_report_enforces_subject_paths_and_json_safety() -> None:
    payload = _payload()
    payload["discrepancy_report"]["discrepancies"][0]["subject_path"] = (
        "/objects/uav-b/attributes/delay_seconds/value"
    )
    with pytest.raises(DiscrepancyReportFormatError, match="relation subjects"):
        load_discrepancy_report(payload)

    payload = _payload()
    payload["discrepancy_report"]["discrepancies"][0]["observed"] = float("inf")
    with pytest.raises(DiscrepancyReportFormatError, match="non-finite"):
        load_discrepancy_report(payload)


def test_discrepancy_report_enforces_impact_and_correction_scope() -> None:
    payload = _payload()
    impact = payload["discrepancy_report"]["discrepancies"][1]["impact"]
    impact["state"] = "none"
    with pytest.raises(DiscrepancyReportFormatError, match="requires all affected"):
        load_discrepancy_report(payload)

    payload = _payload()
    scope = payload["discrepancy_report"]["discrepancies"][0]["correction_scope"]
    scope["immutable_paths"] = ["/objects/uav-b"]
    with pytest.raises(DiscrepancyReportFormatError, match="must not overlap"):
        load_discrepancy_report(payload)

    payload = _payload()
    scope = payload["discrepancy_report"]["discrepancies"][1]["correction_scope"]
    scope["mutable_paths"] = ["/objects/uav-a/attributes/route_id/value"]
    with pytest.raises(DiscrepancyReportFormatError, match="state 'blocked'"):
        load_discrepancy_report(payload)


def test_discrepancy_report_enforces_reference_closure_and_uniqueness() -> None:
    payload = _payload()
    payload["discrepancy_report"]["discrepancies"][0]["basis_refs"].append(
        "not-declared"
    )
    with pytest.raises(DiscrepancyReportFormatError, match="must be declared"):
        load_discrepancy_report(payload)

    payload = _payload()
    payload["discrepancy_report"]["artifact_refs"][1]["ref_id"] = "task-gt16"
    with pytest.raises(DiscrepancyReportFormatError, match="duplicates ref_id"):
        load_discrepancy_report(payload)

    payload = _payload()
    payload["discrepancy_report"]["discrepancies"][1]["id"] = (
        payload["discrepancy_report"]["discrepancies"][0]["id"]
    )
    with pytest.raises(DiscrepancyReportFormatError, match="duplicates id"):
        load_discrepancy_report(payload)


def test_discrepancy_report_enforces_aggregate_state_and_severity() -> None:
    payload = _payload()
    payload["discrepancy_report"]["state"] = "need_review"
    with pytest.raises(DiscrepancyReportFormatError, match="aggregate discrepancy state"):
        load_discrepancy_report(payload)

    payload = _payload()
    payload["discrepancy_report"]["severity"] = "medium"
    with pytest.raises(DiscrepancyReportFormatError, match="maximum discrepancy severity"):
        load_discrepancy_report(payload)


def test_discrepancy_report_binding_rejects_world_state_mismatch() -> None:
    payload = _payload()
    payload["discrepancy_report"]["world_state"]["semantic_fingerprint"] = "0" * 64
    report = load_discrepancy_report(payload)
    world_state = load_world_state(_world_state_payload())

    with pytest.raises(DiscrepancyReportFormatError, match="does not match bound"):
        validate_discrepancy_report_bindings(
            report,
            world_state,
            _artifact_contents(),
        )


def test_discrepancy_report_binding_rejects_missing_unknown_and_modified_bytes() -> None:
    report = load_discrepancy_report(_payload())
    world_state = load_world_state(_world_state_payload())

    contents = _artifact_contents()
    del contents["task-gt16"]
    with pytest.raises(DiscrepancyReportFormatError, match="missing ref_id"):
        validate_discrepancy_report_bindings(report, world_state, contents)

    contents = _artifact_contents()
    contents["extra"] = b"{}"
    with pytest.raises(DiscrepancyReportFormatError, match="unknown ref_id"):
        validate_discrepancy_report_bindings(report, world_state, contents)

    contents = _artifact_contents()
    contents["task-gt16"] += b"\n"
    with pytest.raises(DiscrepancyReportFormatError, match="SHA-256 mismatch"):
        validate_discrepancy_report_bindings(report, world_state, contents)


def test_discrepancy_report_binding_rejects_unbound_observation_or_evidence() -> None:
    payload = _payload()
    payload["discrepancy_report"]["observation_refs"].append("obs-not-in-state")
    payload["discrepancy_report"]["discrepancies"][0]["observation_refs"].append(
        "obs-not-in-state"
    )
    report = load_discrepancy_report(payload)
    world_state = load_world_state(_world_state_payload())
    with pytest.raises(DiscrepancyReportFormatError, match="not declared by bound"):
        validate_discrepancy_report_bindings(report, world_state, _artifact_contents())

    payload = _payload()
    payload["discrepancy_report"]["evidence_refs"].append("evidence:not-in-state")
    payload["discrepancy_report"]["discrepancies"][0]["evidence_refs"].append(
        "evidence:not-in-state"
    )
    report = load_discrepancy_report(payload)
    with pytest.raises(DiscrepancyReportFormatError, match="not declared by bound"):
        validate_discrepancy_report_bindings(report, world_state, _artifact_contents())
