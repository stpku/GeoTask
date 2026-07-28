from pathlib import Path

from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.executor import execute_canonical


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples" / "core" / "vehicle_green_light_downstream_blockage.yaml"


def test_gt20_core_verifies_green_window_queue_intersection_and_storage() -> None:
    data = load_geotask(CASE)
    errors = [
        diagnostic
        for diagnostic in validate_document(data)
        if diagnostic.get("severity", "error") == "error"
    ]
    assert errors == []

    result = execute_canonical(canonicalize(data))
    checks = {check.assertion_id: check for check in result.checks}

    assert len(checks) == 3
    assert checks["green_phase_matches_entry_window"].value is True
    assert checks["path_intersects_downstream_queue"].value is True
    assert checks["available_downstream_storage"].value == 4.0
    assert all(check.status == "verified" for check in checks.values())
    assert result.execution.status == "completed"


def test_gt20_green_signal_does_not_authorize_blocked_intersection_entry() -> None:
    data = load_geotask(CASE)
    signal = data["extensions"]["signal_evidence"]
    downstream = data["extensions"]["downstream_state"]
    envelope = data["extensions"]["vehicle_envelope"]
    rule = data["extensions"]["entry_rule"]

    assert signal["signal_aspect"] == "green"
    assert signal["signal_permission_valid"] is True
    assert signal["evidence_status"] == "verified"

    assert downstream["available_storage_m"] == 4.0
    assert downstream["queue_spillback_present"] is True
    assert downstream["downstream_exit_clear"] is False
    assert downstream["freshness_limit_seconds"] == 3

    assert envelope["vehicle_length_m"] == 4.8
    assert envelope["minimum_exit_buffer_m"] == 2.0
    assert envelope["required_storage_m"] == 6.8

    assert rule["signal_condition_verified"] is True
    assert rule["downstream_condition_verified"] is True
    assert rule["storage_sufficient"] is False
    assert rule["intersection_entry_authorized"] is False


def test_gt20_entry_rule_requires_signal_exit_clearance_and_storage() -> None:
    data = load_geotask(CASE)
    rule = data["extensions"]["entry_rule"]

    assert rule["expression"] == (
        "signal_permission_valid AND downstream_exit_clear AND "
        "available_storage_m >= required_storage_m"
    )


def test_gt20_holds_before_stop_line_and_rechecks_downstream() -> None:
    data = load_geotask(CASE)
    gate = data["extensions"]["task_gate"]

    assert gate["status"] == "blocked_pending_downstream_clearance"
    assert gate["selected_action"] == "wait_before_stop_line_and_recheck_downstream"
    assert gate["rejected_actions"] == [
        "enter_intersection_because_green",
        "enter_intersection_and_wait_inside",
    ]
    assert gate["blocked_outputs"] == [
        "intersection_entry_command",
        "follow_green_without_exit_check",
    ]
    assert gate["required_controls"] == [
        "remain_before_stop_line",
        "retain_signal_and_queue_evidence",
        "recheck_downstream_storage",
        "enter_only_when_full_vehicle_can_clear_junction",
        "reevaluate_if_signal_phase_changes",
    ]
    assert gate["resume_when"] == (
        "signal_permission_valid == true AND downstream_exit_clear == true AND "
        "available_storage_m >= 6.8 AND downstream_evidence_age_seconds <= 3"
    )
    assert gate["next_action"] == "recheck_signal_and_downstream_clearance"
    assert gate["expected_status"] == "verified_intersection_hold"
