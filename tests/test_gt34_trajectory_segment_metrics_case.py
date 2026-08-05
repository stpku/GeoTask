"""GT34 trajectory-segment metric case tests."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "examples" / "core"
BUILDER = CORE / "gt34_build_trajectory_segment_metrics.py"
TASK = CORE / "gt34_trajectory_segment_metrics.yaml"
RESULT = CORE / "gt34_trajectory_segment_metrics_result.json"
SCENARIO = CORE / "gt34_trajectory_segment_metrics.json"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_builder():
    spec = importlib.util.spec_from_file_location("gt34_builder", BUILDER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_gt34_fixed_document_validates_and_executes() -> None:
    from geotask_core.parser import load_geotask, validate_document
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    raw = load_geotask(TASK)
    assert validate_document(copy.deepcopy(raw)) == []
    document = canonicalize(raw)
    result = execute_canonical(document)
    segments = result.outputs["trajectory_segments"]
    assert result.overall.status == "verified"
    assert len(segments) == 2
    assert [item["duration_seconds"] for item in segments] == [120.0, 180.0]
    assert [item["distance_in_horizontal_unit"] for item in segments] == [60.0, 90.0]
    assert [
        item["average_speed_in_horizontal_units_per_second"] for item in segments
    ] == [0.5, 0.5]
    assert result.checks[0].unit == ""


def test_gt34_fixed_execution_result_is_registered_and_valid() -> None:
    from geotask_core.v1.artifact_validation import validate_artifact_payload
    from geotask_core.v1.result import GeotaskResult

    payload = _json(RESULT)
    result = GeotaskResult.from_dict(payload)
    assert result.task_id == "gt34-trajectory-segment-metrics"
    assert len(result.outputs["trajectory_segments"]) == 2
    report = validate_artifact_payload(
        "geotask.execution-result",
        payload,
        file=str(RESULT.relative_to(ROOT)),
    ).to_dict()["artifact_validation"]
    assert report["valid"] is True
    assert report["schema_verified"] is True


def test_gt34_segments_bind_adjacent_samples_exactly() -> None:
    scenario = _json(SCENARIO)["scenario"]
    samples = scenario["explicit_samples"]
    segments = scenario["deterministic_segments"]
    assert scenario["problem"]["sample_count"] == 3
    assert scenario["problem"]["segment_count"] == 2
    assert len(segments) == len(samples) - 1
    for index, segment in enumerate(segments):
        assert segment["segment_index"] == index
        assert segment["start_sample_index"] == index
        assert segment["end_sample_index"] == index + 1
        assert segment["start_observed_at"] == samples[index]["observed_at"]
        assert segment["end_observed_at"] == samples[index + 1]["observed_at"]
        assert segment["start_coordinates"] == samples[index]["coordinates"]
        assert segment["end_coordinates"] == samples[index + 1]["coordinates"]


def test_gt34_never_claims_interpolation_prediction_or_action() -> None:
    scenario = _json(SCENARIO)["scenario"]
    boundaries = scenario["boundaries"]
    assert boundaries["adjacent_segment_binding_verified"] is True
    assert boundaries["duration_positive"] is True
    assert boundaries["distance_unit_inherited_from_document"] is True
    assert boundaries["speed_unit_composed_from_horizontal_unit_and_second"] is True
    for key in (
        "trajectory_interpolated",
        "trajectory_smoothed",
        "trajectory_resampled",
        "future_position_predicted",
        "acceleration_computed",
        "map_matched",
        "external_truth_verified_by_core",
        "production_output_released",
        "command_sent",
        "action_authorized_by_core",
        "action_executed",
    ):
        assert boundaries[key] is False


def test_gt34_hashes_bind_task_and_execution_result() -> None:
    scenario = _json(SCENARIO)["scenario"]
    assert scenario["sha256"] == {
        "task": _sha(TASK),
        "execution_result": _sha(RESULT),
    }


def test_gt34_builder_reproduces_fixed_outputs() -> None:
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


def test_gt34_tampered_time_coordinate_or_type_fails_closed() -> None:
    from geotask_core.parser import load_geotask
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.validator import validate_canonical

    payload = load_geotask(TASK)
    payload["objects"]["uav_alpha_track"]["samples"][1]["observed_at"] = (
        "2026-08-05T08:00:00+08:00"
    )
    diagnostics = validate_canonical(canonicalize(payload))
    assert any("strictly increasing" in item["message"] for item in diagnostics)

    payload = load_geotask(TASK)
    payload["objects"]["uav_alpha_track"]["samples"][1]["coordinates"][0] = float("nan")
    diagnostics = validate_canonical(canonicalize(payload))
    assert any(item["code"] == "invalid_coordinates" for item in diagnostics)

    payload = load_geotask(TASK)
    payload["objects"]["uav_alpha_track"] = {
        "type": "polyline",
        "coordinates": [[0, 0], [36, 48], [36, 138]],
    }
    diagnostics = validate_canonical(canonicalize(payload))
    assert any(
        item["code"] == "object_type_mismatch"
        and "expects type 'trajectory'" in item["message"]
        for item in diagnostics
    )
