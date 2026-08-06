"""Cross-stage tests for the GT38–GT42 UAV identity-governance story."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "core"
STORY_PATH = EXAMPLES / "uav_017_identity_governance_story_gt38_gt42.json"

SCENARIO_WRAPPERS = (
    EXAMPLES / "gt38_trajectory_identity_adjudication.json",
    EXAMPLES / "gt39_identity_merge_proposal.json",
    EXAMPLES / "gt40_identity_merge_approval_record.json",
    EXAMPLES / "gt41_object_graph_change_request.json",
    EXAMPLES / "gt42_object_graph_change_application_approval_record.json",
)

CORE_ARTIFACTS = (
    EXAMPLES / "trajectory_identity_adjudication_gt38.json",
    EXAMPLES / "identity_merge_proposal_gt39.json",
    EXAMPLES / "identity_merge_approval_record_gt40.json",
    EXAMPLES / "object_graph_change_request_gt41.json",
    EXAMPLES / "object_graph_change_application_approval_record_gt42.json",
)


def test_story_defines_one_concrete_five_stage_uav_scenario() -> None:
    story = json.loads(STORY_PATH.read_text(encoding="utf-8"))["composite_case"]

    assert story["id"] == "gt38-gt42-uav-017-reidentification"
    assert story["fictional_data"] is True
    assert story["asset_label"] == "巡检无人机UAV-017"
    assert story["operational_context"] == "园区电力线路巡检"
    assert [item["case_id"] for item in story["stages"]] == [
        "GT38",
        "GT39",
        "GT40",
        "GT41",
        "GT42",
    ]
    assert [item["stage"] for item in story["stages"]] == [1, 2, 3, 4, 5]


def test_story_keeps_stable_machine_ids_with_human_labels() -> None:
    story = json.loads(STORY_PATH.read_text(encoding="utf-8"))["composite_case"]

    assert story["machine_to_display_mapping"] == {
        "track_alpha": "失联前轨迹",
        "track_beta": "恢复后轨迹",
        "provisional_alpha": "UAV-017原始主体",
        "provisional_beta": "遮挡后临时主体",
    }
    assert story["boundary_observation"] == {
        "temporal_gap_seconds": 60,
        "spatial_distance_meters": 5,
        "object_class": "uav",
    }
    assert story["timeline"][0]["observed_at"] == "2026-08-05T08:02:00+08:00"
    assert story["timeline"][1]["observed_at"] == "2026-08-05T08:03:00+08:00"


def test_story_explains_independent_evidence_and_both_identity_risks() -> None:
    story = json.loads(STORY_PATH.read_text(encoding="utf-8"))["composite_case"]
    evidence_text = json.dumps(story["independent_evidence"], ensure_ascii=False)
    risk_text = json.dumps(story["business_risks"], ensure_ascii=False)

    assert "Remote ID" in evidence_text
    assert "设备序列号" in evidence_text
    assert "任务编号、机型、运营人和时间连续性" in evidence_text
    assert "另一架无人机" in risk_text
    assert "重复计数" in risk_text


def test_every_scenario_wrapper_points_to_the_same_story_stage() -> None:
    expected_story = "gt38-gt42-uav-017-reidentification"
    for stage_number, path in enumerate(SCENARIO_WRAPPERS, start=1):
        payload = json.loads(path.read_text(encoding="utf-8"))
        scenario = payload.get("scenario", payload)
        composite = scenario["composite_case"]
        assert composite["id"] == expected_story
        assert composite["stage"] == stage_number
        assert composite["stage_count"] == 5
        assert composite["asset_label"] == "巡检无人机UAV-017"
        assert composite["story_file"] == (
            "examples/core/uav_017_identity_governance_story_gt38_gt42.json"
        )


def test_story_metadata_does_not_enter_registered_core_artifacts() -> None:
    for path in CORE_ARTIFACTS:
        text = path.read_text(encoding="utf-8")
        assert "composite_case" not in text
        assert "UAV-017" not in text
        assert "machine_to_display_mapping" not in text
