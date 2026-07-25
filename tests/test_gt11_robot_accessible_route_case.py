from pathlib import Path

from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.executor import execute_canonical


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples" / "core" / "robot_accessible_route.yaml"


def test_gt11_core_calculates_direct_and_network_segment_distances() -> None:
    data = load_geotask(CASE)
    errors = [
        diagnostic
        for diagnostic in validate_document(data)
        if diagnostic.get("severity", "error") == "error"
    ]
    assert errors == []

    result = execute_canonical(canonicalize(data))
    checks = {check.assertion_id: check for check in result.checks}

    assert checks["direct_distance"].value == 50.0
    assert checks["direct_distance"].status == "verified"

    segment_ids = [
        "segment_start_to_w1",
        "segment_w1_to_w2",
        "segment_w2_to_w3",
        "segment_w3_to_w4",
        "segment_w4_to_target",
    ]
    segment_values = [checks[segment_id].value for segment_id in segment_ids]
    assert segment_values == [100.0, 75.0, 50.0, 25.0, 50.0]
    assert all(checks[segment_id].status == "verified" for segment_id in segment_ids)
    assert sum(segment_values) == 300.0
    assert result.execution.status == "completed"


def test_gt11_robot_capability_blocks_the_shortest_geometric_route() -> None:
    data = load_geotask(CASE)
    profile = data["extensions"]["robot_profile"]
    direct = data["extensions"]["direct_path_constraints"]

    assert profile["mobility"] == "wheeled"
    assert profile["can_use_stairs"] is False
    assert profile["can_cross_fence"] is False
    assert profile["can_enter_motor_vehicle_lane"] is False
    assert direct["direct_path_distance_m"] == 50
    assert direct["direct_path_accessible"] is False
    assert direct["blocked_by"] == ["stairs", "fence", "motor_vehicle_lane"]


def test_gt11_accessible_network_is_complete_and_deterministic() -> None:
    data = load_geotask(CASE)
    network = data["extensions"]["accessible_network"]
    comparison = data["extensions"]["route_comparison"]
    plan = data["extensions"]["navigation_plan"]

    assert network["route_node_refs"] == [
        "robot_start",
        "waypoint_1",
        "waypoint_2",
        "waypoint_3",
        "waypoint_4",
        "delivery_target",
    ]
    assert network["segment_lengths_m"] == [100, 75, 50, 25, 50]
    assert sum(network["segment_lengths_m"]) == network["total_distance_m"] == 300
    assert network["all_edges_accessible"] is True

    assert comparison["euclidean_distance_m"] == 50
    assert comparison["accessible_route_distance_m"] == 300
    assert comparison["detour_ratio"] == 6
    assert comparison["shortest_geometric_route_accessible"] is False
    assert comparison["selected_route"] == "accessible_network"

    assert plan["selected_action"] == "follow_accessible_network"
    assert plan["planned_distance_m"] == 300
    assert plan["next_action"] == "navigate_network"
    assert plan["expected_status"] == "reachable"
    assert plan["rejected_actions"] == [
        "take_direct_line",
        "cross_motor_vehicle_lane",
    ]


def test_gt11_route_edges_match_the_declared_node_sequence() -> None:
    data = load_geotask(CASE)
    network = data["extensions"]["accessible_network"]
    nodes = network["route_node_refs"]
    expected_edges = [[nodes[index], nodes[index + 1]] for index in range(len(nodes) - 1)]

    assert network["allowed_edges"] == expected_edges
