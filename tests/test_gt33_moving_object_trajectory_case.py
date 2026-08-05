"""GT33 moving-object trajectory case tests."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "examples" / "core"
BUILDER = CORE / "gt33_build_moving_object_trajectory.py"
TASK = CORE / "gt33_moving_object_trajectory.yaml"
RESULT = CORE / "gt33_moving_object_trajectory_result.json"
SCENARIO = CORE / "gt33_moving_object_trajectory.json"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_builder():
    spec = importlib.util.spec_from_file_location("gt33_builder", BUILDER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_gt33_fixed_document_validates_and_executes() -> None:
    from geotask_core.parser import load_geotask, validate_document
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    raw = load_geotask(TASK)
    assert validate_document(copy.deepcopy(raw)) == []
    document = canonicalize(raw)
    assert document.objects["uav_alpha"].type == "moving_object"
    assert document.objects["uav_alpha_track"].type == "trajectory"
    result = execute_canonical(document)
    assert result.outputs == {"track_duration_seconds": 300.0}
    assert result.overall.status == "verified"
    assert result.checks[0].unit == "second"


def test_gt33_fixed_execution_result_is_registered_and_valid() -> None:
    from geotask_core.v1.artifact_validation import validate_artifact_payload
    from geotask_core.v1.result import GeotaskResult

    payload = _json(RESULT)
    result = GeotaskResult.from_dict(payload)
    assert result.task_id == "gt33-moving-object-trajectory"
    assert result.outputs == {"track_duration_seconds": 300.0}
    report = validate_artifact_payload(
        "geotask.execution-result",
        payload,
        file=str(RESULT.relative_to(ROOT)),
    ).to_dict()["artifact_validation"]
    assert report["valid"] is True
    assert report["schema_verified"] is True


def test_gt33_scenario_preserves_discrete_observation_semantics() -> None:
    scenario = _json(SCENARIO)["scenario"]
    assert scenario["problem"] == {
        "moving_object": "uav_alpha",
        "object_class": "uav",
        "trajectory": "uav_alpha_track",
        "subject_ref": "uav_alpha",
        "sample_count": 3,
        "interpolation": "none",
    }
    assert [item["observed_at"] for item in scenario["explicit_samples"]] == [
        "2026-08-05T08:00:00+08:00",
        "2026-08-05T08:02:00+08:00",
        "2026-08-05T08:05:00+08:00",
    ]
    assert scenario["deterministic_result"] == {
        "track_duration_seconds": 300.0,
        "status": "verified",
        "assurance_level": "local_deterministic",
        "output_eligible": True,
    }


def test_gt33_never_claims_interpolation_prediction_or_action() -> None:
    scenario = _json(SCENARIO)["scenario"]
    assert scenario["boundaries"] == {
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
    }
    assert "future_positions" in scenario["not_computed"]
    assert "map_matched_path" in scenario["not_computed"]
    assert "action_command" in scenario["not_computed"]


def test_gt33_hashes_bind_task_and_execution_result() -> None:
    scenario = _json(SCENARIO)["scenario"]
    assert scenario["sha256"] == {
        "task": _sha(TASK),
        "execution_result": _sha(RESULT),
    }


def test_gt33_builder_reproduces_fixed_outputs() -> None:
    before = {
        RESULT.name: RESULT.read_bytes(),
        SCENARIO.name: SCENARIO.read_bytes(),
    }
    _load_builder().build()
    after = {
        RESULT.name: RESULT.read_bytes(),
        SCENARIO.name: SCENARIO.read_bytes(),
    }
    assert after == before


def test_gt33_tampered_time_or_interpolation_fails_closed() -> None:
    from geotask_core.parser import load_geotask
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.validator import validate_canonical

    payload = load_geotask(TASK)
    payload["objects"]["uav_alpha_track"]["interpolation"] = "linear"
    diagnostics = validate_canonical(canonicalize(payload))
    assert any("interpolation must be exactly 'none'" in item["message"] for item in diagnostics)

    payload = load_geotask(TASK)
    payload["objects"]["uav_alpha_track"]["samples"][2]["observed_at"] = (
        "2026-08-05T08:01:00+08:00"
    )
    diagnostics = validate_canonical(canonicalize(payload))
    assert any("strictly increasing" in item["message"] for item in diagnostics)
