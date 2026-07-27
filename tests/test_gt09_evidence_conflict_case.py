from pathlib import Path

from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.executor import execute_canonical


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples" / "core" / "evidence_conflict_review.yaml"


def _detect_boolean_conflict(values: list[bool | None]) -> bool:
    known = {value for value in values if value is not None}
    return known == {True, False}


def test_gt09_verified_sources_produce_incompatible_temporal_results() -> None:
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

    source_a = checks["temporal_conflict_authority_a"]
    source_b = checks["temporal_conflict_bulletin_b"]
    assert source_a.value is True
    assert source_a.status == "verified"
    assert source_b.value is False
    assert source_b.status == "verified"
    assert result.execution.status == "completed"
    assert _detect_boolean_conflict([source_a.value, source_b.value]) is True


def test_gt09_conflict_review_plan_is_actionable() -> None:
    data = load_geotask(CASE)
    context = data["extensions"]["application_context"]
    conflict = data["extensions"]["evidence_conflict"]

    assert context["scenario"] == "uav_temporary_no_fly_notice_conflict"
    assert context["vehicle"] == "uav"
    assert context["planned_flight_window"] == "08:00-09:00"
    assert conflict["id"] == "resolve-restricted-schedule-conflict"
    assert conflict["conflict_type"] == "incompatible_verified_sources"
    assert conflict["conflicting_assertions"] == [
        "temporal_conflict_authority_a",
        "temporal_conflict_bulletin_b",
    ]
    assert conflict["source_refs"] == [
        "authority_notice_a",
        "operations_bulletin_b",
    ]
    assert conflict["blocked_outputs"] == ["full_conflict", "automatic_approval"]
    assert conflict["resolution_required_fields"] == [
        "authoritative_source",
        "superseded_version",
        "effective_schedule",
        "resolution_basis",
        "resolved_by",
        "resolved_at",
    ]
    assert conflict["resume_when"] == "evidence_conflict_resolved == true"
    assert conflict["next_action"] == "request_conflict_review"
    assert conflict["expected_status"] == "conflicted"


def test_gt09_does_not_choose_a_source_without_resolution_policy() -> None:
    data = load_geotask(CASE)
    result = execute_canonical(canonicalize(data))
    checks = {check.assertion_id: check for check in result.checks}
    temporal_values = [
        checks["temporal_conflict_authority_a"].value,
        checks["temporal_conflict_bulletin_b"].value,
    ]

    conflict = data["extensions"]["evidence_conflict"]
    assert _detect_boolean_conflict(temporal_values) is True
    assert conflict["expected_status"] == "conflicted"
    assert conflict["next_action"] == "request_conflict_review"
    assert conflict["next_action"] not in {"trust_source_a", "trust_source_b"}
