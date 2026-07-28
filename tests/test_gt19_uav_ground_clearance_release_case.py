from pathlib import Path

from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.executor import execute_canonical


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples" / "core" / "uav_arrival_ground_clearance_release.yaml"


def test_gt19_core_verifies_arrival_altitude_time_and_ground_clearance() -> None:
    data = load_geotask(CASE)
    errors = [
        diagnostic
        for diagnostic in validate_document(data)
        if diagnostic.get("severity", "error") == "error"
    ]
    assert errors == []

    result = execute_canonical(canonicalize(data))
    checks = {check.assertion_id: check for check in result.checks}

    assert len(checks) == 4
    assert checks["projection_inside_drop_zone"].value is True
    assert checks["release_altitude_authorized"].value is True
    assert checks["release_time_authorized"].value is True
    assert checks["ground_responder_clearance"].value == 10.0
    assert all(check.status == "verified" for check in checks.values())
    assert result.execution.status == "completed"


def test_gt19_arrival_is_verified_but_release_is_not_authorized() -> None:
    data = load_geotask(CASE)
    arrival = data["extensions"]["arrival_state"]
    evidence = data["extensions"]["ground_clearance_evidence"]
    rule = data["extensions"]["release_rule"]

    assert arrival == {
        "projection_inside_drop_zone": True,
        "release_altitude_authorized": True,
        "release_time_authorized": True,
        "target_overhead_reached": True,
    }
    assert evidence["planned_impact_point_clearance_m"] == 10
    assert evidence["minimum_release_clearance_m"] == 30
    assert evidence["ground_responder_inside_safety_radius"] is True
    assert evidence["ground_zone_clear"] is False
    assert evidence["evidence_status"] == "verified"
    assert evidence["freshness_limit_seconds"] == 15

    assert rule["arrival_conditions_verified"] is True
    assert rule["release_conditions_verified"] is False
    assert rule["immediate_release_authorized"] is False


def test_gt19_release_rule_requires_live_ground_clearance() -> None:
    data = load_geotask(CASE)
    rule = data["extensions"]["release_rule"]
    payload = data["extensions"]["payload_state"]

    assert rule["expression"] == (
        "projection_inside_drop_zone AND release_altitude_authorized AND "
        "release_time_authorized AND ground_zone_clear AND release_system_ready"
    )
    assert payload["release_system_ready"] is True
    assert payload["release_mode"] == "controlled_parachute_drop"


def test_gt19_blocks_release_and_requests_clearance_reverification() -> None:
    data = load_geotask(CASE)
    gate = data["extensions"]["task_gate"]

    assert gate["status"] == "blocked_pending_ground_clearance"
    assert gate["selected_action"] == "hold_position_and_request_ground_clearance"
    assert gate["rejected_actions"] == [
        "release_cargo_because_over_target",
        "abort_delivery_mission",
    ]
    assert gate["blocked_outputs"] == [
        "payload_release_command",
        "automatic_drop_authorization",
    ]
    assert gate["required_controls"] == [
        "retain_live_ground_clearance_evidence",
        "notify_ground_team_to_clear_drop_zone",
        "maintain_safe_hover_position",
        "reverify_clearance_before_release",
        "abort_or_divert_if_hover_margin_expires",
    ]
    assert gate["resume_when"] == (
        "ground_zone_clear == true AND clearance_evidence_age_seconds <= 15"
    )
    assert gate["next_action"] == "request_ground_clearance_and_reverify"
    assert gate["expected_status"] == "verified_release_hold"
