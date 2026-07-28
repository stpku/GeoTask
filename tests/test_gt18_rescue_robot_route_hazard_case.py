from pathlib import Path

from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.executor import execute_canonical


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples" / "core" / "rescue_robot_shortest_route_hazard.yaml"


def test_gt18_core_verifies_route_lengths_and_hazard_intersections() -> None:
    data = load_geotask(CASE)
    errors = [
        diagnostic
        for diagnostic in validate_document(data)
        if diagnostic.get("severity", "error") == "error"
    ]
    assert errors == []

    result = execute_canonical(canonicalize(data))
    checks = {check.assertion_id: check for check in result.checks}

    assert len(checks) == 6
    assert checks["shortest_route_distance"].value == 120.0
    assert checks["safe_route_segment_1_distance"].value == 70.0
    assert checks["safe_route_segment_2_distance"].value == 120.0
    assert checks["safe_route_segment_3_distance"].value == 70.0
    assert checks["shortest_route_intersects_hazard"].value is True
    assert checks["safe_route_intersects_hazard"].value is False
    assert all(check.status == "verified" for check in checks.values())
    assert result.execution.status == "completed"


def test_gt18_shortest_route_is_not_temperature_compatible() -> None:
    data = load_geotask(CASE)
    metrics = data["extensions"]["route_metrics"]
    environment = data["extensions"]["environment_evidence"]
    capability = data["extensions"]["robot_capability"]
    rule = data["extensions"]["feasibility_rule"]

    assert metrics["shortest_route_length_m"] == 120
    assert metrics["safe_route_length_m"] == 260
    assert metrics["shortest_route_is_geometrically_shortest"] is True
    assert metrics["shortest_route_intersects_high_temperature_zone"] is True
    assert metrics["safe_route_intersects_high_temperature_zone"] is False

    assert environment["shortest_route_max_temperature_c"] == 120
    assert environment["safe_route_max_temperature_c"] == 60
    assert environment["evidence_status"] == "verified"
    assert capability["maximum_operating_temperature_c"] == 80

    assert rule["shortest_route_reaches_target"] is True
    assert rule["shortest_route_temperature_compatible"] is False
    assert rule["shortest_route_executable"] is False


def test_gt18_longer_safe_route_is_executable() -> None:
    data = load_geotask(CASE)
    rule = data["extensions"]["feasibility_rule"]
    gate = data["extensions"]["task_gate"]

    assert rule["expression"] == (
        "route_reaches_target AND NOT route_intersects_hazard AND "
        "route_max_temperature_c <= robot_maximum_operating_temperature_c"
    )
    assert rule["safe_route_reaches_target"] is True
    assert rule["safe_route_temperature_compatible"] is True
    assert rule["safe_route_executable"] is True

    assert gate["status"] == "open_for_safe_route_entry"
    assert gate["selected_action"] == "enter_via_safe_route"
    assert gate["next_action"] == "dispatch_robot_via_safe_route"
    assert gate["expected_status"] == "verified_safe_route_entry"


def test_gt18_rejects_shortest_route_entry_without_aborting_safe_mission() -> None:
    data = load_geotask(CASE)
    gate = data["extensions"]["task_gate"]

    assert gate["rejected_actions"] == [
        "enter_via_shortest_route",
        "abort_rescue_mission",
    ]
    assert gate["blocked_outputs"] == [
        "authorize_shortest_route_entry",
        "ignore_verified_hazard",
    ]
    assert gate["required_controls"] == [
        "retain_verified_temperature_evidence",
        "bind_route_to_robot_capability",
        "monitor_safe_route_temperature",
        "stop_if_temperature_exceeds_limit",
    ]
