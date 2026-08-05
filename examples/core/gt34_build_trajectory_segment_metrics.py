"""Build the fixed GT34 trajectory-segment metric bundle.

All coordinates, identities, and timestamps are fictional. The builder validates
one discrete trajectory, derives only adjacent-sample duration, planar distance,
and average speed in document horizontal units per second, and keeps
interpolation, smoothing, prediction, map matching, publication, authorization,
and real-world action outside GeoTask Core.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.executor import execute_canonical
from geotask_core.v1.result import GeotaskResult


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "examples" / "core"
TASK = CORE / "gt34_trajectory_segment_metrics.yaml"
RESULT = CORE / "gt34_trajectory_segment_metrics_result.json"
SCENARIO = CORE / "gt34_trajectory_segment_metrics.json"

EXPECTED_SEGMENTS = [
    {
        "segment_index": 0,
        "start_sample_index": 0,
        "end_sample_index": 1,
        "start_observed_at": "2026-08-05T08:00:00+08:00",
        "end_observed_at": "2026-08-05T08:02:00+08:00",
        "start_coordinates": [0, 0],
        "end_coordinates": [36, 48],
        "duration_seconds": 120.0,
        "distance_in_horizontal_unit": 60.0,
        "average_speed_in_horizontal_units_per_second": 0.5,
    },
    {
        "segment_index": 1,
        "start_sample_index": 1,
        "end_sample_index": 2,
        "start_observed_at": "2026-08-05T08:02:00+08:00",
        "end_observed_at": "2026-08-05T08:05:00+08:00",
        "start_coordinates": [36, 48],
        "end_coordinates": [36, 138],
        "duration_seconds": 180.0,
        "distance_in_horizontal_unit": 90.0,
        "average_speed_in_horizontal_units_per_second": 0.5,
    },
]


class GT34BuildError(ValueError):
    """Raised when the fixed GT34 bundle crosses its declared boundary."""


def _pretty_bytes(payload: Mapping[str, object]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _write(path: Path, payload: Mapping[str, object]) -> bytes:
    raw = _pretty_bytes(payload)
    path.write_bytes(raw)
    return raw


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def build() -> dict[str, object]:
    raw_document = load_geotask(TASK)
    errors = [
        item
        for item in validate_document(raw_document)
        if item.get("severity", "error") == "error"
    ]
    if errors:
        raise GT34BuildError(f"GT34 document validation failed: {errors}")

    document = canonicalize(raw_document)
    moving_object = document.objects.get("uav_alpha")
    trajectory = document.objects.get("uav_alpha_track")
    if moving_object is None or moving_object.type != "moving_object":
        raise GT34BuildError("GT34 must declare uav_alpha as moving_object")
    if trajectory is None or trajectory.type != "trajectory":
        raise GT34BuildError("GT34 must declare uav_alpha_track as trajectory")
    if trajectory.data.get("subject_ref") != "uav_alpha":
        raise GT34BuildError("GT34 trajectory must bind to uav_alpha")
    if trajectory.data.get("interpolation") != "none":
        raise GT34BuildError("GT34 must not enable interpolation")
    if document.space.horizontal_unit != "meter":
        raise GT34BuildError("GT34 fixed document must declare meter as horizontal unit")

    samples = trajectory.data.get("samples")
    if not isinstance(samples, list) or len(samples) != 3:
        raise GT34BuildError("GT34 fixed trajectory must contain exactly three samples")

    result = execute_canonical(document)
    if not isinstance(result, GeotaskResult):
        raise GT34BuildError("GT34 execution did not return a GeotaskResult")
    if result.execution.status != "completed" or result.overall.status != "verified":
        raise GT34BuildError("GT34 deterministic execution must complete as verified")
    if result.outputs != {"trajectory_segments": EXPECTED_SEGMENTS}:
        raise GT34BuildError("GT34 segment metrics do not match the fixed contract")
    if len(result.checks) != 1 or result.checks[0].operator != "trajectory_segment_metrics":
        raise GT34BuildError("GT34 must execute only trajectory_segment_metrics")
    if result.checks[0].unit:
        raise GT34BuildError("GT34 list output must not overclaim one scalar unit")

    result.execution.started_at = "2026-08-05T02:30:00+00:00"
    result.execution.finished_at = "2026-08-05T02:30:00+00:00"
    result_bytes = _write(RESULT, result.to_dict())
    task_bytes = TASK.read_bytes()
    scenario = {
        "scenario": {
            "id": "gt34-trajectory-segment-metrics",
            "title_zh": "三个轨迹样本之间，每一段到底移动了多远、多快？",
            "title_en": "How far and how fast did each explicit trajectory segment move?",
            "problem": {
                "moving_object": "uav_alpha",
                "object_class": "uav",
                "trajectory": "uav_alpha_track",
                "subject_ref": "uav_alpha",
                "sample_count": 3,
                "segment_count": 2,
                "interpolation": "none",
                "horizontal_unit": "meter",
                "duration_unit": "second",
                "speed_unit": "horizontal_unit_per_second",
            },
            "explicit_samples": samples,
            "deterministic_segments": EXPECTED_SEGMENTS,
            "deterministic_result": {
                "status": "verified",
                "assurance_level": "local_deterministic",
                "output_eligible": True,
            },
            "not_computed": [
                "intermediate_positions",
                "smoothed_trajectory",
                "resampled_trajectory",
                "future_positions",
                "acceleration",
                "map_matched_path",
                "real_world_identity_authenticity",
                "action_command",
            ],
            "incorrect_actions": [
                "treat_non_adjacent_samples_as_one_segment_without_declaration",
                "divide_distance_by_zero_or_reversed_time",
                "label_all_horizontal_units_as_meters",
                "interpolate_or_smooth_between_samples",
                "predict_future_motion_from_two_segment_averages",
                "treat_local_segment_metrics_as_action_authorization",
            ],
            "sha256": {
                "task": _sha256(task_bytes),
                "execution_result": _sha256(result_bytes),
            },
            "boundaries": {
                "fictional_data": True,
                "sample_order_verified": True,
                "subject_binding_verified": True,
                "adjacent_segment_binding_verified": True,
                "duration_positive": True,
                "distance_unit_inherited_from_document": True,
                "speed_unit_composed_from_horizontal_unit_and_second": True,
                "trajectory_interpolated": False,
                "trajectory_smoothed": False,
                "trajectory_resampled": False,
                "future_position_predicted": False,
                "acceleration_computed": False,
                "map_matched": False,
                "external_truth_verified_by_core": False,
                "production_output_released": False,
                "command_sent": False,
                "action_authorized_by_core": False,
                "action_executed": False,
            },
        }
    }
    _write(SCENARIO, scenario)
    return {"result": result.to_dict(), "scenario": scenario}


if __name__ == "__main__":
    build()
    print("GT34 trajectory-segment metric bundle generated")
