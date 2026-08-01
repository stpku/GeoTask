from pathlib import Path

from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.executor import execute_canonical


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples" / "core" / "uav_route_crossing_temporal_separation.yaml"


def test_gt16_core_verifies_crossing_altitude_and_time() -> None:
    data = load_geotask(CASE)
    errors = [
        diagnostic
        for diagnostic in validate_document(data)
        if diagnostic.get("severity", "error") == "error"
    ]
    assert errors == []

    result = execute_canonical(canonicalize(data))
    checks = {check.assertion_id: check for check in result.checks}

    assert checks["route_a_crossing_distance"].value == 0.0
    assert checks["route_b_crossing_distance"].value == 0.0
    assert checks["altitude_conflict"].value is True
    assert checks["temporal_conflict"].value is False
    assert all(check.status == "verified" for check in checks.values())
    assert result.execution.status == "completed"


def test_gt16_collision_rule_requires_space_altitude_and_time() -> None:
    data = load_geotask(CASE)
    crossing = data["extensions"]["crossing_state"]
    rule = data["extensions"]["collision_rule"]

    assert crossing == {
        "route_a_passes_crossing": True,
        "route_b_passes_crossing": True,
        "horizontal_crossing": True,
        "altitude_overlap": True,
        "temporal_overlap": False,
    }
    assert rule["expression"] == (
        "horizontal_crossing AND altitude_overlap AND temporal_overlap"
    )
    assert rule["collision_conflict"] is False
    assert rule["reason"] == "crossing_zone_occupancy_windows_do_not_overlap"


def test_gt16_temporal_separation_meets_minimum() -> None:
    data = load_geotask(CASE)
    separation = data["extensions"]["temporal_separation"]

    assert separation["uav_a_crossing_window"] == "09:00-09:01"
    assert separation["uav_b_crossing_window"] == "09:03-09:04"
    assert separation["actual_separation_minutes"] == 2
    assert separation["minimum_separation_minutes"] == 1
    assert separation["planned_separation_seconds"] == 120
    assert separation["separation_requirement_met"] is True
    assert separation["schedule_evidence_status"] == "current_and_verified"


def test_gt16_gate_preserves_verified_separation() -> None:
    data = load_geotask(CASE)
    gate = data["extensions"]["flight_gate"]

    assert gate["status"] == "open_with_verified_separation"
    assert gate["selected_action"] == "maintain_planned_time_separation"
    assert gate["next_action"] == "maintain_planned_time_separation"
    assert gate["expected_status"] == "verified_separation"
    assert gate["required_controls"] == [
        "preserve_crossing_windows",
        "monitor_arrival_deviation",
        "recalculate_if_delay_exceeds_margin",
    ]
    assert gate["rejected_actions"] == [
        "declare_collision_from_route_crossing_only",
        "declare_collision_from_altitude_overlap_only",
    ]
    assert gate["blocked_outputs"] == [
        "claim_collision_is_verified",
        "force_emergency_stop_without_temporal_conflict",
    ]


def test_gt16_new_state_reduces_margin_but_requires_monitoring_not_reversal() -> None:
    data = load_geotask(CASE)
    state = data["extensions"]["monitoring_state"]
    gate = data["extensions"]["monitoring_gate"]

    assert state == {
        "observed_update": "uav_a_arrival_delay",
        "observed_delay_seconds": 40,
        "predicted_separation_seconds": 80,
        "minimum_separation_seconds": 60,
        "remaining_margin_seconds": 20,
        "telemetry_freshness_seconds": 8,
        "telemetry_freshness_limit_seconds": 10,
        "monitoring_required": True,
    }
    assert gate["state"] == "eligible_with_active_monitoring"
    assert gate["selected_action"] == "continue_with_active_monitoring"
    assert gate["next_action"] == "monitor_and_recheck"
    assert gate["expected_status"] == "eligible_with_active_monitoring"
    assert gate["preserved_findings"] == [
        "horizontal_crossing_verified",
        "altitude_overlap_verified",
        "planned_temporal_separation_verified",
    ]
    assert gate["invalidated_outputs"] == [
        "treat_initial_plan_as_permanently_safe",
        "disable_arrival_deviation_monitoring",
    ]
    assert gate["recheck_when"] == [
        "predicted_separation_seconds <= 60",
        "telemetry_freshness_seconds > 10",
    ]
