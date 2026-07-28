from pathlib import Path

from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.executor import execute_canonical


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples" / "core" / "city_event_report_deduplication.yaml"


def test_gt17_core_verifies_all_report_distances_and_times() -> None:
    data = load_geotask(CASE)
    errors = [
        diagnostic
        for diagnostic in validate_document(data)
        if diagnostic.get("severity", "error") == "error"
    ]
    assert errors == []

    result = execute_canonical(canonicalize(data))
    checks = {check.assertion_id: check for check in result.checks}

    distance_values = [checks[f"report_{number:02d}_distance"].value for number in range(1, 11)]
    time_values = [checks[f"report_{number:02d}_time_overlap"].value for number in range(1, 11)]

    assert len(checks) == 20
    assert max(distance_values) < 19.0
    assert min(distance_values) == 0.0
    assert time_values == [True] * 10
    assert all(check.status == "verified" for check in checks.values())
    assert result.execution.status == "completed"


def test_gt17_report_cluster_has_one_semantic_spatiotemporal_signature() -> None:
    data = load_geotask(CASE)
    cluster = data["extensions"]["report_cluster"]

    assert cluster["report_count"] == 10
    assert cluster["event_type"] == "road_waterlogging"
    assert cluster["same_semantic_signature"] is True
    assert cluster["spatial_threshold_m"] == 30
    assert cluster["maximum_report_distance_m"] == 18.97
    assert cluster["all_reports_within_spatial_threshold"] is True
    assert cluster["dedup_window"] == "08:00-08:10"
    assert cluster["all_reports_within_temporal_window"] is True
    assert len(cluster["source_ids"]) == 10
    assert len(set(cluster["source_ids"])) == 10


def test_gt17_dedup_rule_creates_one_incident_without_losing_evidence() -> None:
    data = load_geotask(CASE)
    rule = data["extensions"]["dedup_rule"]
    gate = data["extensions"]["task_gate"]

    assert rule["expression"] == (
        "same_semantic_signature AND all_reports_within_spatial_threshold "
        "AND all_reports_within_temporal_window"
    )
    assert rule["duplicate_reports_verified"] is True
    assert rule["unique_incident_count"] == 1
    assert rule["evidence_source_count"] == 10

    assert gate["status"] == "open_for_single_dispatch"
    assert gate["selected_action"] == "merge_reports_and_create_one_task"
    assert gate["task_count"] == 1
    assert gate["preserve_source_evidence"] is True
    assert gate["next_action"] == "dispatch_single_verified_task"
    assert gate["expected_status"] == "verified_deduplication"


def test_gt17_rejects_duplicate_dispatch_and_evidence_deletion() -> None:
    data = load_geotask(CASE)
    gate = data["extensions"]["task_gate"]

    assert gate["rejected_actions"] == [
        "create_ten_dispatch_tasks",
        "discard_repeated_reports",
    ]
    assert gate["blocked_outputs"] == [
        "duplicate_dispatch",
        "duplicate_work_orders",
        "source_evidence_loss",
    ]
    assert gate["required_controls"] == [
        "retain_all_source_ids",
        "increment_report_count",
        "update_incident_confidence",
        "link_new_reports_to_existing_task",
    ]
