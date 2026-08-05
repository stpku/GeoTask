"""Build the fixed GT33 moving-object trajectory bundle.

All coordinates, identities, and timestamps are fictional. The builder validates
one discrete trajectory, executes only an endpoint-duration calculation, and
keeps interpolation, prediction, map matching, publication, authorization, and
real-world action outside GeoTask Core.
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
TASK = CORE / "gt33_moving_object_trajectory.yaml"
RESULT = CORE / "gt33_moving_object_trajectory_result.json"
SCENARIO = CORE / "gt33_moving_object_trajectory.json"


class GT33BuildError(ValueError):
    """Raised when the fixed GT33 bundle crosses its declared boundary."""


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
        raise GT33BuildError(f"GT33 document validation failed: {errors}")

    document = canonicalize(raw_document)
    moving_object = document.objects.get("uav_alpha")
    trajectory = document.objects.get("uav_alpha_track")
    if moving_object is None or moving_object.type != "moving_object":
        raise GT33BuildError("GT33 must declare uav_alpha as moving_object")
    if trajectory is None or trajectory.type != "trajectory":
        raise GT33BuildError("GT33 must declare uav_alpha_track as trajectory")
    if trajectory.data.get("subject_ref") != "uav_alpha":
        raise GT33BuildError("GT33 trajectory must bind to uav_alpha")
    if trajectory.data.get("interpolation") != "none":
        raise GT33BuildError("GT33 must not enable interpolation")

    samples = trajectory.data.get("samples")
    if not isinstance(samples, list) or len(samples) != 3:
        raise GT33BuildError("GT33 fixed trajectory must contain exactly three samples")

    result = execute_canonical(document)
    if not isinstance(result, GeotaskResult):
        raise GT33BuildError("GT33 execution did not return a GeotaskResult")
    if result.execution.status != "completed" or result.overall.status != "verified":
        raise GT33BuildError("GT33 deterministic execution must complete as verified")
    if result.outputs != {"track_duration_seconds": 300.0}:
        raise GT33BuildError("GT33 duration must be exactly 300 seconds")
    if len(result.checks) != 1 or result.checks[0].operator != "trajectory_duration_seconds":
        raise GT33BuildError("GT33 must execute only trajectory_duration_seconds")

    # Fixed public artifacts must be byte-for-byte reproducible. These timestamps
    # describe the example build record, not the observed trajectory interval.
    result.execution.started_at = "2026-08-05T00:00:00+00:00"
    result.execution.finished_at = "2026-08-05T00:00:00+00:00"
    result_bytes = _write(RESULT, result.to_dict())
    task_bytes = TASK.read_bytes()
    scenario = {
        "scenario": {
            "id": "gt33-moving-object-trajectory",
            "title_zh": "三个带时间位置点连起来，就是一条可验证轨迹吗？",
            "title_en": "Do three timestamped positions form a verifiable trajectory?",
            "problem": {
                "moving_object": "uav_alpha",
                "object_class": "uav",
                "trajectory": "uav_alpha_track",
                "subject_ref": "uav_alpha",
                "sample_count": 3,
                "interpolation": "none",
            },
            "explicit_samples": samples,
            "deterministic_result": {
                "track_duration_seconds": 300.0,
                "status": "verified",
                "assurance_level": "local_deterministic",
                "output_eligible": True,
            },
            "not_computed": [
                "intermediate_positions",
                "future_positions",
                "velocity_or_acceleration",
                "map_matched_path",
                "real_world_identity_authenticity",
                "action_command",
            ],
            "incorrect_actions": [
                "replace_timestamped_samples_with_a_static_polyline",
                "interpolate_between_samples_without_declared_method",
                "predict_future_position_from_three_samples",
                "treat_local_validation_as_real_world_tracking",
                "treat_duration_output_as_action_authorization",
            ],
            "sha256": {
                "task": _sha256(task_bytes),
                "execution_result": _sha256(result_bytes),
            },
            "boundaries": {
                "fictional_data": True,
                "sample_order_verified": True,
                "subject_binding_verified": True,
                "trajectory_interpolated": False,
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
    print("GT33 moving-object trajectory bundle generated")
