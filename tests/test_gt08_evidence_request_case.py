from pathlib import Path

from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.executor import execute_canonical


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples" / "core" / "evidence_request_plan.yaml"


def test_gt08_core_result_triggers_evidence_request() -> None:
    data = load_geotask(CASE)
    errors = [
        diagnostic
        for diagnostic in validate_document(data)
        if diagnostic.get("severity", "error") == "error"
    ]
    assert errors == []

    result = execute_canonical(canonicalize(data))
    checks = {check.assertion_id: check for check in result.checks}

    assert checks["route_intersects_zone"].value is True
    assert checks["route_intersects_zone"].status == "verified"
    assert checks["altitude_conflict"].value is True
    assert checks["altitude_conflict"].status == "verified"

    temporal = checks["temporal_conflict"]
    assert temporal.value is None
    assert temporal.status == "unverifiable"
    assert temporal.error is not None
    assert temporal.error["code"] == "unverifiable_condition"
    assert result.execution.status == "partial"

    request = data["extensions"]["evidence_request"]
    assert request["trigger"] == temporal.assertion_id
    assert request["trigger_status"] == temporal.status
    assert request["next_action"] == "request_evidence"


def test_gt08_evidence_request_is_actionable_and_blocks_unsafe_outputs() -> None:
    data = load_geotask(CASE)
    request = data["extensions"]["evidence_request"]

    assert request["id"] == "verify-restricted-schedule"
    assert request["reason"] == "restricted_schedule_not_verified"
    assert request["required_fields"] == [
        "issuing_authority",
        "effective_date",
        "start_time",
        "end_time",
        "document_version",
        "source_reference",
        "verified_at",
    ]
    assert request["blocked_outputs"] == ["full_conflict", "automatic_approval"]
    assert request["resume_when"] == "restricted_schedule_verified == true"


def test_gt08_unverifiable_result_does_not_authorize_boolean_decision() -> None:
    data = load_geotask(CASE)
    result = execute_canonical(canonicalize(data))
    statuses = {check.assertion_id: check.status for check in result.checks}

    full_conflict_status = data["extensions"]["decision_rule"]["expected_status"]
    next_action = data["extensions"]["evidence_request"]["next_action"]

    assert statuses["temporal_conflict"] == "unverifiable"
    assert full_conflict_status == "unverifiable"
    assert next_action == "request_evidence"
    assert next_action not in {"approve", "reject"}
