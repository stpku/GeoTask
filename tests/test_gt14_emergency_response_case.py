from pathlib import Path

from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.executor import execute_canonical


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples" / "core" / "emergency_response_fastest_arrival.yaml"


def test_gt14_core_verifies_candidate_proximity() -> None:
    data = load_geotask(CASE)
    errors = [
        diagnostic
        for diagnostic in validate_document(data)
        if diagnostic.get("severity", "error") == "error"
    ]
    assert errors == []

    result = execute_canonical(canonicalize(data))
    checks = {check.assertion_id: check for check in result.checks}

    assert checks["team_a_straight_distance"].value == 2.4
    assert checks["team_a_straight_distance"].status == "verified"
    assert checks["team_b_straight_distance"].value == 5.6
    assert checks["team_b_straight_distance"].status == "verified"
    assert result.execution.status == "completed"


def test_gt14_arrival_comparison_separates_nearest_from_fastest() -> None:
    data = load_geotask(CASE)
    candidates = data["extensions"]["candidates"]
    comparison = data["extensions"]["arrival_comparison"]

    team_a = candidates["team_a"]
    team_b = candidates["team_b"]

    assert team_a["straight_distance_km"] < team_b["straight_distance_km"]
    assert team_a["route_distance_km"] > team_b["route_distance_km"]

    team_a_eta = (
        team_a["readiness_time_min"]
        + team_a["route_travel_time_min"]
        + team_a["access_delay_min"]
    )
    team_b_eta = (
        team_b["readiness_time_min"]
        + team_b["route_travel_time_min"]
        + team_b["access_delay_min"]
    )

    assert team_a_eta == team_a["estimated_arrival_min"] == 14
    assert team_b_eta == team_b["estimated_arrival_min"] == 8
    assert comparison["nearest_team"] == "team_a"
    assert comparison["fastest_verified_team"] == "team_b"
    assert comparison["nearest_is_fastest"] is False
    assert comparison["arrival_advantage_min"] == 6


def test_gt14_response_window_selects_team_b() -> None:
    data = load_geotask(CASE)
    response_window = data["extensions"]["response_window"]
    candidates = data["extensions"]["candidates"]
    gate = data["extensions"]["dispatch_gate"]

    deadline = response_window["maximum_response_time_min"]
    assert deadline == 12
    assert candidates["team_a"]["estimated_arrival_min"] > deadline
    assert candidates["team_a"]["meets_deadline"] is False
    assert candidates["team_b"]["estimated_arrival_min"] <= deadline
    assert candidates["team_b"]["meets_deadline"] is True

    assert gate["status"] == "ready"
    assert gate["selected_action"] == "dispatch_team_b"
    assert gate["next_action"] == "dispatch_team_b"
    assert gate["expected_status"] == "verified_dispatch"
    assert gate["blocked_outputs"] == [
        "distance_only_dispatch",
        "primary_dispatch_team_a",
    ]


def test_gt14_requires_current_route_time_evidence() -> None:
    data = load_geotask(CASE)
    evidence = data["extensions"]["route_time_evidence"]
    gate = data["extensions"]["dispatch_gate"]

    assert evidence["status"] == "current"
    assert evidence["verified_at"] == "08:59"
    assert evidence["freshness_limit_min"] == 5
    assert gate["recalculate_when"] == (
        "route_time_evidence.status != current or candidate_state_changed == true"
    )
    assert "request_route_refresh_with_current_evidence" in gate["rejected_actions"]
    assert gate["selected_action"] != "dispatch_team_a_because_nearest"
