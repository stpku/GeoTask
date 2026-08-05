"""Build the fixed GT35 stop/move and observation-gap bundle.

All coordinates, identities, timestamps, and thresholds are fictional. The
builder classifies only adjacent explicit samples and keeps interpolation,
loss-of-link inference, anomaly inference, prediction, publication,
authorization, and action outside GeoTask Core.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

from geotask_core.ops import trajectory_segment_classifications
from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.executor import execute_canonical
from geotask_core.v1.result import GeotaskResult


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "examples" / "core"
TASK = CORE / "gt35_trajectory_stop_move_gap.yaml"
RESULT = CORE / "gt35_trajectory_stop_move_gap_result.json"
SCENARIO = CORE / "gt35_trajectory_stop_move_gap.json"

PARAMETERS = {
    "stationary_radius_in_horizontal_unit": 5,
    "minimum_stationary_duration_seconds": 120,
    "maximum_observation_gap_seconds": 300,
    "allow_observation_gap": True,
}

EXPECTED_CLASSIFICATIONS = [
    "stationary_candidate",
    "moving_observed",
    "observation_gap",
]


class GT35BuildError(ValueError):
    """Raised when the fixed GT35 bundle crosses its declared boundary."""


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
        raise GT35BuildError(f"GT35 document validation failed: {errors}")

    document = canonicalize(raw_document)
    trajectory = document.objects.get("uav_alpha_track")
    if trajectory is None or trajectory.type != "trajectory":
        raise GT35BuildError("GT35 must declare uav_alpha_track as trajectory")
    if trajectory.data.get("subject_ref") != "uav_alpha":
        raise GT35BuildError("GT35 trajectory must bind to uav_alpha")
    if trajectory.data.get("interpolation") != "none":
        raise GT35BuildError("GT35 must not enable interpolation")
    if document.space.horizontal_unit != "meter":
        raise GT35BuildError("GT35 fixed document must declare meter as horizontal unit")

    samples = trajectory.data.get("samples")
    if not isinstance(samples, list) or len(samples) != 4:
        raise GT35BuildError("GT35 fixed trajectory must contain exactly four samples")

    result = execute_canonical(document)
    if not isinstance(result, GeotaskResult):
        raise GT35BuildError("GT35 execution did not return a GeotaskResult")
    if result.execution.status != "completed" or result.overall.status != "verified":
        raise GT35BuildError("GT35 deterministic execution must complete as verified")
    records = result.outputs.get("trajectory_segment_states")
    if not isinstance(records, list) or len(records) != 3:
        raise GT35BuildError("GT35 must emit exactly three adjacent segment records")
    if [record.get("classification") for record in records] != EXPECTED_CLASSIFICATIONS:
        raise GT35BuildError("GT35 classifications do not match the fixed contract")
    if [record.get("duration_seconds") for record in records] != [120.0, 120.0, 600.0]:
        raise GT35BuildError("GT35 fixed segment durations changed")
    if [record.get("distance_in_horizontal_unit") for record in records] != [5.0, 10.0, 0.0]:
        raise GT35BuildError("GT35 fixed segment distances changed")
    if len(result.checks) != 1 or result.checks[0].operator != "trajectory_segment_classifications":
        raise GT35BuildError("GT35 must execute only trajectory_segment_classifications")
    if result.checks[0].unit:
        raise GT35BuildError("GT35 list output must not overclaim one scalar unit")

    disallowed_gap_records = trajectory_segment_classifications(
        samples,
        **{**PARAMETERS, "allow_observation_gap": False},
    )
    if disallowed_gap_records[-1]["classification"] != "unverifiable":
        raise GT35BuildError("GT35 disallowed gap must remain unverifiable")

    result.execution.started_at = "2026-08-05T04:20:00+00:00"
    result.execution.finished_at = "2026-08-05T04:20:00+00:00"
    result_bytes = _write(RESULT, result.to_dict())
    task_bytes = TASK.read_bytes()
    scenario = {
        "scenario": {
            "id": "gt35-trajectory-stop-move-gap",
            "title_zh": "位置几乎没变就是停留，十分钟没观测就是失联吗？",
            "title_en": "Does little movement prove a stop, and does a ten-minute interval prove lost link?",
            "problem": {
                "moving_object": "uav_alpha",
                "trajectory": "uav_alpha_track",
                "sample_count": 4,
                "segment_count": 3,
                "interpolation": "none",
                "horizontal_unit": "meter",
                "thresholds": PARAMETERS,
            },
            "explicit_samples": samples,
            "deterministic_classifications": records,
            "gap_marking_disallowed": {
                "allow_observation_gap": False,
                "classifications": [
                    record["classification"] for record in disallowed_gap_records
                ],
                "last_segment_state": "unverifiable",
            },
            "deterministic_result": {
                "status": "verified",
                "assurance_level": "local_deterministic",
                "output_eligible": True,
            },
            "not_inferred": [
                "continuous_stationary_state",
                "instantaneous_velocity",
                "loss_of_link",
                "anomaly",
                "intermediate_positions",
                "future_positions",
                "map_matched_path",
                "real_world_identity_authenticity",
                "action_command",
            ],
            "incorrect_actions": [
                "choose_stationary_or_gap_thresholds_implicitly",
                "treat_stationary_candidate_as_proven_continuous_stop",
                "treat_observation_gap_as_lost_link_or_anomaly",
                "interpolate_positions_inside_the_gap",
                "predict_future_motion_from_segment_labels",
                "treat_local_classification_as_action_authorization",
            ],
            "sha256": {
                "task": _sha256(task_bytes),
                "execution_result": _sha256(result_bytes),
            },
            "boundaries": {
                "fictional_data": True,
                "sample_order_verified": True,
                "subject_binding_verified": True,
                "thresholds_caller_declared": True,
                "adjacent_segment_binding_verified": True,
                "closed_classification_vocabulary_verified": True,
                "trajectory_interpolated": False,
                "trajectory_smoothed": False,
                "trajectory_resampled": False,
                "continuous_stationary_state_verified": False,
                "loss_of_link_inferred": False,
                "anomaly_inferred": False,
                "future_position_predicted": False,
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
    print("GT35 stop/move and observation-gap bundle generated")
