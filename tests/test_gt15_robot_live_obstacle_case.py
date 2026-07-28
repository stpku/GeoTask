from pathlib import Path

from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.executor import execute_canonical


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples" / "core" / "robot_live_obstacle_stop.yaml"


def test_gt15_core_verifies_route_obstacle_and_stop_clearance() -> None:
    data = load_geotask(CASE)
    errors = [
        diagnostic
        for diagnostic in validate_document(data)
        if diagnostic.get("severity", "error") == "error"
    ]
    assert errors == []

    result = execute_canonical(canonicalize(data))
    checks = {check.assertion_id: check for check in result.checks}

    assert checks["route_intersects_live_obstacle"].value is True
    assert checks["route_intersects_live_obstacle"].status == "verified"
    assert checks["stop_clearance_distance"].value == 4.0
    assert checks["stop_clearance_distance"].status == "verified"
    assert result.execution.status == "completed"


def test_gt15_separates_static_map_from_current_occupancy() -> None:
    data = load_geotask(CASE)
    static_map = data["extensions"]["static_map_state"]
    live = data["extensions"]["live_perception"]
    resolution = data["extensions"]["state_resolution"]

    assert static_map["corridor_passable"] is True
    assert static_map["scope"] == "structural_passability"
    assert static_map["proves_current_occupancy"] is False

    assert live["status"] == "current"
    assert live["obstacle_blocks_corridor"] is True
    assert live["confidence"] == 0.97

    assert resolution["static_map_passable"] is True
    assert resolution["live_route_blocked"] is True
    assert resolution["current_passability"] is False
    assert resolution["authoritative_for_immediate_motion"] == "live_perception"


def test_gt15_stop_point_preserves_required_clearance() -> None:
    data = load_geotask(CASE)
    route_state = data["extensions"]["route_state"]

    assert route_state["planned_route_intersects_obstacle"] is True
    assert route_state["current_passability"] is False
    assert route_state["safe_stop_clearance_m"] == 4.0
    assert route_state["minimum_stop_clearance_m"] == 3.0
    assert (
        route_state["safe_stop_clearance_m"]
        >= route_state["minimum_stop_clearance_m"]
    )
    assert route_state["stop_point_is_safe"] is True


def test_gt15_motion_gate_blocks_map_only_proceed_action() -> None:
    data = load_geotask(CASE)
    gate = data["extensions"]["motion_gate"]

    assert gate["status"] == "blocked"
    assert gate["reason"] == "current_route_occupied_by_live_obstacle"
    assert gate["selected_action"] == "stop_and_replan_route"
    assert gate["next_action"] == "stop_and_replan_route"
    assert gate["expected_status"] == "verified_stop"
    assert gate["blocked_outputs"] == [
        "autonomous_forward_motion",
        "continue_inspection_without_revalidation",
    ]
    assert gate["rejected_actions"] == [
        "proceed_because_static_map_passable",
        "ignore_live_obstacle_as_temporary",
    ]
    assert gate["resume_when"] == (
        "live_obstacle_cleared == true and route_reverified == true"
    )
