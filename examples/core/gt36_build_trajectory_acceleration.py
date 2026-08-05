"""Build the fixed GT36 acceleration and motion-continuity bundle.

All identities, coordinates, timestamps, and thresholds are fictional. The
builder estimates only scalar change between adjacent segment-average speeds.
It does not claim instantaneous or vector acceleration, interpolate gaps,
predict motion, infer anomaly or lost link, publish output, authorize action,
or execute real-world commands.
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
TASK = CORE / "gt36_trajectory_acceleration.yaml"
RESULT = CORE / "gt36_trajectory_acceleration_result.json"
SCENARIO = CORE / "gt36_trajectory_acceleration.json"


class GT36BuildError(ValueError):
    """Raised when the fixed GT36 bundle crosses its declared boundary."""


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
        raise GT36BuildError(f"GT36 document validation failed: {errors}")

    document = canonicalize(raw_document)
    trajectory = document.objects.get("uav_alpha_track")
    if trajectory is None or trajectory.type != "trajectory":
        raise GT36BuildError("GT36 must declare uav_alpha_track as trajectory")
    if trajectory.data.get("subject_ref") != "uav_alpha":
        raise GT36BuildError("GT36 trajectory must bind to uav_alpha")
    if trajectory.data.get("interpolation") != "none":
        raise GT36BuildError("GT36 must not enable interpolation")
    if document.space.horizontal_unit != "meter":
        raise GT36BuildError("GT36 fixed document must declare meter as horizontal unit")

    samples = trajectory.data.get("samples")
    if not isinstance(samples, list) or len(samples) != 5:
        raise GT36BuildError("GT36 fixed trajectory must contain exactly five samples")

    result = execute_canonical(document)
    if not isinstance(result, GeotaskResult):
        raise GT36BuildError("GT36 execution did not return a GeotaskResult")
    if result.execution.status != "completed" or result.overall.status != "verified":
        raise GT36BuildError("GT36 deterministic execution must complete as verified")
    records = result.outputs.get("trajectory_acceleration_estimates")
    if not isinstance(records, list) or len(records) != 3:
        raise GT36BuildError("GT36 must emit exactly three adjacent segment transitions")
    if [record.get("continuity_state") for record in records] != [
        "continuous_observation",
        "continuous_observation",
        "unverifiable",
    ]:
        raise GT36BuildError("GT36 continuity states do not match the fixed contract")
    if records[0].get("acceleration_in_horizontal_units_per_second_squared") != 0.0:
        raise GT36BuildError("GT36 first transition must have zero scalar acceleration")
    if abs(
        records[1].get("acceleration_in_horizontal_units_per_second_squared", 0.0)
        - (1.0 / 300.0)
    ) > 1e-15:
        raise GT36BuildError("GT36 second transition acceleration changed")
    if records[2].get("acceleration_in_horizontal_units_per_second_squared") is not None:
        raise GT36BuildError("GT36 gap transition must not emit acceleration")
    if records[2].get("speed_change_in_horizontal_units_per_second") is not None:
        raise GT36BuildError("GT36 gap transition must not emit speed change")
    if len(result.checks) != 1 or result.checks[0].operator != (
        "trajectory_segment_acceleration_estimates"
    ):
        raise GT36BuildError("GT36 must execute only the acceleration estimator")
    if result.checks[0].unit:
        raise GT36BuildError("GT36 list output must not overclaim one scalar unit")

    result.execution.started_at = "2026-08-05T05:20:00+00:00"
    result.execution.finished_at = "2026-08-05T05:20:00+00:00"
    result_bytes = _write(RESULT, result.to_dict())
    task_bytes = TASK.read_bytes()

    scenario = {
        "scenario": {
            "id": "gt36-trajectory-acceleration",
            "title_zh": "两段平均速度变了，就能证明瞬时加速度和连续运动吗？",
            "title_en": "Does a change between segment-average speeds prove instantaneous acceleration and continuous motion?",
            "problem": {
                "moving_object": "uav_alpha",
                "trajectory": "uav_alpha_track",
                "sample_count": 5,
                "segment_count": 4,
                "transition_count": 3,
                "horizontal_unit": "meter",
                "representative_time_method": "segment_midpoint",
                "maximum_observation_gap_seconds": 300,
                "interpolation": "none",
            },
            "explicit_samples": samples,
            "deterministic_estimates": records,
            "deterministic_result": {
                "status": "verified",
                "assurance_level": "local_deterministic",
                "output_eligible": True,
            },
            "not_inferred": [
                "instantaneous_acceleration",
                "vector_acceleration",
                "heading_change",
                "continuous_motion_inside_gap",
                "loss_of_link",
                "anomaly",
                "intermediate_positions",
                "future_positions",
                "map_matched_path",
                "real_world_identity_authenticity",
                "action_command",
            ],
            "incorrect_actions": [
                "use_sample_boundary_without_declaring_representative_time",
                "compute_acceleration_across_an_observation_gap",
                "treat_scalar_average_speed_change_as_vector_acceleration",
                "infer_heading_or_turn_rate_from_speed_magnitudes",
                "interpolate_positions_inside_the_gap",
                "predict_future_motion_from_acceleration_estimates",
                "treat_local_estimation_as_action_authorization",
            ],
            "sha256": {
                "task": _sha256(task_bytes),
                "execution_result": _sha256(result_bytes),
            },
            "boundaries": {
                "fictional_data": True,
                "sample_order_verified": True,
                "subject_binding_verified": True,
                "representative_time_method_explicit": True,
                "maximum_gap_caller_declared": True,
                "adjacent_segment_binding_verified": True,
                "scalar_acceleration_estimated": True,
                "gap_transition_failed_closed": True,
                "instantaneous_acceleration_verified": False,
                "vector_acceleration_verified": False,
                "direction_change_inferred": False,
                "trajectory_interpolated": False,
                "trajectory_smoothed": False,
                "trajectory_resampled": False,
                "continuous_motion_verified": False,
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
    print("GT36 acceleration and motion-continuity bundle generated")
