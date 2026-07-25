from pathlib import Path

from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.executor import execute_canonical


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples" / "core" / "uav_energy_reserve.yaml"


def test_gt12_core_verifies_direct_and_detour_geometry() -> None:
    data = load_geotask(CASE)
    errors = [
        diagnostic
        for diagnostic in validate_document(data)
        if diagnostic.get("severity", "error") == "error"
    ]
    assert errors == []

    result = execute_canonical(canonicalize(data))
    checks = {check.assertion_id: check for check in result.checks}

    assert checks["direct_distance"].value == 8000.0
    assert checks["direct_distance"].status == "verified"
    assert checks["direct_route_enters_no_fly_zone"].value is True
    assert checks["direct_route_enters_no_fly_zone"].status == "verified"
    assert checks["detour_route_enters_no_fly_zone"].value is False
    assert checks["detour_route_enters_no_fly_zone"].status == "verified"

    segment_ids = [
        "segment_takeoff_to_w1",
        "segment_w1_to_w2",
        "segment_w2_to_target",
    ]
    segment_values = [checks[segment_id].value for segment_id in segment_ids]
    assert segment_values == [1500.0, 8000.0, 1500.0]
    assert sum(segment_values) == 11000.0
    assert all(checks[segment_id].status == "verified" for segment_id in segment_ids)
    assert result.execution.status == "completed"


def test_gt12_energy_budget_blocks_unsafe_launch() -> None:
    data = load_geotask(CASE)
    battery = data["extensions"]["battery_state"]
    comparison = data["extensions"]["route_comparison"]
    budget = data["extensions"]["energy_budget"]
    gate = data["extensions"]["mission_gate"]

    assert battery["remaining_range_km"] == 12
    assert battery["required_reserve_km"] == 2
    assert comparison["direct_distance_km"] == 8
    assert comparison["direct_route_legal"] is False
    assert comparison["compliant_detour_distance_km"] == 11
    assert comparison["compliant_detour_legal"] is True

    assert budget["route_requirement_km"] == 11
    assert budget["reserve_requirement_km"] == 2
    assert budget["total_required_range_km"] == 13
    assert budget["available_range_km"] == 12
    assert budget["shortfall_km"] == 1
    assert budget["arrival_possible_without_reserve"] is True
    assert budget["safe_completion_possible"] is False

    assert gate["status"] == "blocked"
    assert gate["selected_action"] == "request_recharge_or_replan"
    assert gate["blocked_outputs"] == ["launch_clearance", "automatic_dispatch"]
    assert gate["resume_when"] == "available_range_km >= total_required_range_km"
    assert gate["next_action"] == "recover_energy_margin"
    assert gate["expected_status"] == "insufficient_margin"


def test_gt12_shortfall_is_derived_from_explicit_requirements() -> None:
    data = load_geotask(CASE)
    budget = data["extensions"]["energy_budget"]

    total_required = budget["route_requirement_km"] + budget["reserve_requirement_km"]
    shortfall = total_required - budget["available_range_km"]

    assert total_required == budget["total_required_range_km"] == 13
    assert shortfall == budget["shortfall_km"] == 1


def test_gt12_recovery_options_do_not_fake_mission_clearance() -> None:
    data = load_geotask(CASE)
    gate = data["extensions"]["mission_gate"]

    assert gate["selected_action"] not in {"launch", "automatic_dispatch"}
    assert gate["alternatives"] == [
        "replace_battery",
        "add_intermediate_charging_stop",
        "reduce_route_energy_requirement",
    ]
