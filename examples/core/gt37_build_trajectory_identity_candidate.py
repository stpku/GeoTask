"""Build the fixed GT37 trajectory identity-candidate bundle.

All identities, coordinates, timestamps, and thresholds are fictional. The
builder classifies only a boundary-sample candidate. It never merges objects,
mutates subject references, predicts, verifies external identity, publishes,
authorizes, or executes real-world action.
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
TASK = CORE / "gt37_trajectory_identity_candidate.yaml"
RESULT = CORE / "gt37_trajectory_identity_candidate_result.json"
SCENARIO = CORE / "gt37_trajectory_identity_candidate.json"


class GT37BuildError(ValueError):
    """Raised when the fixed GT37 bundle crosses its declared boundary."""


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
        raise GT37BuildError(f"GT37 document validation failed: {errors}")

    document = canonicalize(raw_document)
    first = document.objects.get("track_alpha")
    second = document.objects.get("track_beta")
    if first is None or first.type != "trajectory":
        raise GT37BuildError("GT37 must declare track_alpha as trajectory")
    if second is None or second.type != "trajectory":
        raise GT37BuildError("GT37 must declare track_beta as trajectory")
    if first.data.get("subject_ref") != "provisional_alpha":
        raise GT37BuildError("GT37 track_alpha subject binding changed")
    if second.data.get("subject_ref") != "provisional_beta":
        raise GT37BuildError("GT37 track_beta subject binding changed")
    if first.data.get("interpolation") != "none" or second.data.get("interpolation") != "none":
        raise GT37BuildError("GT37 trajectories must not enable interpolation")

    result = execute_canonical(document)
    if not isinstance(result, GeotaskResult):
        raise GT37BuildError("GT37 execution did not return a GeotaskResult")
    if result.execution.status != "completed" or result.overall.status != "verified":
        raise GT37BuildError("GT37 deterministic execution must complete as verified")
    record = result.outputs.get("identity_candidate")
    if not isinstance(record, dict):
        raise GT37BuildError("GT37 must emit one structured candidate record")
    if record.get("candidate_state") != "same_object_candidate":
        raise GT37BuildError("GT37 fixed candidate state changed")
    if record.get("temporal_gap_seconds") != 60.0:
        raise GT37BuildError("GT37 fixed temporal gap changed")
    if record.get("spatial_distance_in_horizontal_unit") != 5.0:
        raise GT37BuildError("GT37 fixed boundary distance changed")
    if record.get("identity_merge_performed") is not False:
        raise GT37BuildError("GT37 must never merge identities")
    if record.get("subject_refs_mutated") is not False:
        raise GT37BuildError("GT37 must never mutate subject refs")
    if record.get("first_subject_ref") == record.get("second_subject_ref"):
        raise GT37BuildError("GT37 must preserve two distinct provisional subjects")
    if len(result.checks) != 1 or result.checks[0].unit:
        raise GT37BuildError("GT37 structured result must not claim one scalar unit")

    result.execution.started_at = "2026-08-05T08:40:00+00:00"
    result.execution.finished_at = "2026-08-05T08:40:00+00:00"
    result_bytes = _write(RESULT, result.to_dict())
    task_bytes = TASK.read_bytes()

    scenario = {
        "scenario": {
            "id": "gt37-trajectory-identity-candidate",
            "title_zh": "两段轨迹只差60秒和5米，就能自动认定为同一个对象吗？",
            "title_en": "Can two trajectory fragments 60 seconds and 5 meters apart be automatically merged as one object?",
            "problem": {
                "first_trajectory_ref": "track_alpha",
                "second_trajectory_ref": "track_beta",
                "first_subject_ref": "provisional_alpha",
                "second_subject_ref": "provisional_beta",
                "maximum_identity_gap_seconds": 120,
                "maximum_identity_distance_in_horizontal_unit": 10,
                "require_same_object_class": True,
                "horizontal_unit": "meter",
                "interpolation": "none",
            },
            "deterministic_candidate": record,
            "alternative_outcomes": {
                "far_boundary": "different_object_candidate",
                "class_mismatch_when_required": "different_object_candidate",
                "temporal_gap_exceeds_maximum": "unverifiable",
            },
            "deterministic_result": {
                "status": "verified",
                "assurance_level": "local_deterministic",
                "output_eligible": True,
            },
            "not_inferred": [
                "real_world_identity_equality",
                "automatic_identity_merge",
                "subject_ref_rewrite",
                "continuous_path_between_fragments",
                "sensor_track_association_truth",
                "future_position",
                "action_authorization",
            ],
            "incorrect_actions": [
                "merge_provisional_alpha_and_provisional_beta",
                "rewrite_track_beta_subject_ref",
                "treat_same_object_candidate_as_verified_identity",
                "interpolate_a_path_between_boundary_samples",
                "ignore_the_declared_time_or_distance_limits",
                "publish_or_execute_an_identity_update",
            ],
            "sha256": {
                "task": _sha256(task_bytes),
                "execution_result": _sha256(result_bytes),
            },
            "boundaries": {
                "fictional_data": True,
                "trajectory_references_verified": True,
                "subject_bindings_verified": True,
                "object_classes_bound": True,
                "boundary_samples_only": True,
                "caller_declared_limits": True,
                "same_object_candidate_computed": True,
                "real_world_identity_verified": False,
                "identity_merge_performed": False,
                "subject_refs_mutated": False,
                "trajectory_interpolated": False,
                "trajectory_smoothed": False,
                "trajectory_resampled": False,
                "map_matched": False,
                "future_position_predicted": False,
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
    print("GT37 trajectory identity-candidate bundle generated")
