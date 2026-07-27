from pathlib import Path

from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.executor import execute_canonical


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples" / "core" / "vehicle_clearance_envelope.yaml"


def test_gt13_core_verifies_roadwork_and_widths() -> None:
    data = load_geotask(CASE)
    errors = [
        diagnostic
        for diagnostic in validate_document(data)
        if diagnostic.get("severity", "error") == "error"
    ]
    assert errors == []

    result = execute_canonical(canonicalize(data))
    checks = {check.assertion_id: check for check in result.checks}

    assert checks["route_enters_roadwork_zone"].value is True
    assert checks["route_enters_roadwork_zone"].status == "verified"
    assert checks["available_passage_width"].value == 2.4
    assert checks["available_passage_width"].status == "verified"
    assert checks["vehicle_body_width"].value == 2.1
    assert checks["vehicle_body_width"].status == "verified"
    assert result.execution.status == "completed"


def test_gt13_clearance_budget_is_object_specific() -> None:
    data = load_geotask(CASE)
    road = data["extensions"]["road_state"]
    vehicle = data["extensions"]["vehicle_profile"]
    budget = data["extensions"]["clearance_budget"]

    assert road["road_open"] is True
    assert road["temporary_roadwork_active"] is True
    assert road["narrowed_passage_width_m"] == 2.4

    required = (
        vehicle["vehicle_body_width_m"]
        + vehicle["left_safety_buffer_m"]
        + vehicle["right_safety_buffer_m"]
    )
    assert round(required, 1) == vehicle["required_envelope_width_m"] == 2.7

    assert budget["available_width_m"] == 2.4
    assert budget["required_width_m"] == 2.7
    assert round(budget["required_width_m"] - budget["available_width_m"], 1) == 0.3
    assert budget["clearance_shortfall_m"] == 0.3
    assert budget["road_state_allows_entry"] is True
    assert budget["object_specific_passability"] is False


def test_gt13_passage_gate_blocks_unsafe_entry() -> None:
    data = load_geotask(CASE)
    gate = data["extensions"]["passage_gate"]

    assert gate["status"] == "blocked"
    assert gate["reason"] == "insufficient_lateral_clearance"
    assert gate["blocked_outputs"] == ["autonomous_passage", "full_speed_entry"]
    assert gate["selected_action"] == "request_alternate_route_or_controlled_passage"
    assert gate["alternatives"] == [
        "use_alternate_route",
        "request_manual_traffic_control",
        "wait_for_workzone_clearance",
    ]
    assert gate["rejected_actions"] == [
        "proceed_because_road_open",
        "shrink_safety_buffer_to_fit",
    ]
    assert gate["resume_when"] == (
        "available_width_m >= required_envelope_width_m or "
        "controlled_passage_authorized == true"
    )
    assert gate["next_action"] == "recover_clearance_margin"
    assert gate["expected_status"] == "insufficient_clearance"


def test_gt13_does_not_relabel_open_road_as_passable() -> None:
    data = load_geotask(CASE)
    road = data["extensions"]["road_state"]
    budget = data["extensions"]["clearance_budget"]
    gate = data["extensions"]["passage_gate"]

    assert road["road_open"] is True
    assert budget["object_specific_passability"] is False
    assert gate["selected_action"] not in {
        "proceed_because_road_open",
        "shrink_safety_buffer_to_fit",
    }
