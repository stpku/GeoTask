from pathlib import Path

from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.executor import execute_canonical


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples" / "core" / "robot_corridor_coordination.yaml"


def _time_to_minutes(value: str) -> int:
    hour, minute = (int(part) for part in value.split(":"))
    return hour * 60 + minute


def test_gt10_core_confirms_single_capacity_corridor_conflict() -> None:
    data = load_geotask(CASE)
    errors = [
        diagnostic
        for diagnostic in validate_document(data)
        if diagnostic.get("severity", "error") == "error"
    ]
    assert errors == []

    result = execute_canonical(canonicalize(data))
    checks = {check.assertion_id: check for check in result.checks}

    assert checks["robot_a_uses_corridor"].value is True
    assert checks["robot_a_uses_corridor"].status == "verified"
    assert checks["robot_b_uses_corridor"].value is True
    assert checks["robot_b_uses_corridor"].status == "verified"
    assert checks["corridor_occupancy_overlap"].value is True
    assert checks["corridor_occupancy_overlap"].status == "verified"
    assert result.execution.status == "completed"


def test_gt10_explicit_priority_policy_selects_robot_b_wait() -> None:
    data = load_geotask(CASE)
    context = data["extensions"]["application_context"]
    tasks = data["extensions"]["robot_tasks"]
    policy = data["extensions"]["coordination_policy"]
    plan = data["extensions"]["coordination_plan"]

    assert context["scenario"] == "warehouse_robot_single_capacity_corridor"
    assert context["resource_capacity"] == 1
    assert tasks["robot_a"]["mission"] == "urgent_outbound_order"
    assert tasks["robot_b"]["mission"] == "empty_return"
    assert tasks["robot_a"]["task_priority"] > tasks["robot_b"]["task_priority"]
    assert policy["priority_rule"] == "higher_task_priority_first"
    assert policy["tie_breaker"] == "request_dispatch_review"
    assert policy["clearance_buffer_minutes"] == 1

    assert plan["selected_action"] == "robot_b_wait"
    assert plan["proceed_robot"] == "robot_a"
    assert plan["wait_robot"] == "robot_b"
    assert plan["hold_at"] == "robot_b.holding_point"
    assert plan["next_action"] == "coordinate_passage"
    assert plan["expected_status"] == "coordinated"


def test_gt10_wait_duration_and_revised_window_are_deterministic() -> None:
    data = load_geotask(CASE)
    tasks = data["extensions"]["robot_tasks"]
    policy = data["extensions"]["coordination_policy"]
    plan = data["extensions"]["coordination_plan"]

    robot_a_exit = _time_to_minutes(tasks["robot_a"]["original_corridor_window"][1])
    robot_b_entry = _time_to_minutes(tasks["robot_b"]["original_corridor_window"][0])
    revised_entry = robot_a_exit + policy["clearance_buffer_minutes"]
    original_duration = (
        _time_to_minutes(tasks["robot_b"]["original_corridor_window"][1])
        - robot_b_entry
    )

    assert revised_entry == _time_to_minutes(plan["revised_entry_time"])
    assert revised_entry - robot_b_entry == plan["wait_duration_minutes"]
    assert revised_entry + original_duration == _time_to_minutes(plan["revised_exit_time"])
    assert plan["blocked_actions"] == [
        "robot_b_enter_corridor_before_08_36",
        "simultaneous_corridor_entry",
    ]
    assert plan["resume_when"] == (
        "robot_a_cleared_corridor == true and current_time >= 08:36"
    )


def test_gt10_policy_does_not_hide_equal_priority_case() -> None:
    data = load_geotask(CASE)
    policy = data["extensions"]["coordination_policy"]

    assert policy["tie_breaker"] == "request_dispatch_review"
    assert policy["tie_breaker"] not in {"robot_a_wait", "robot_b_wait"}
