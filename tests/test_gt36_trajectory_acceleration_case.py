"""GT36 trajectory acceleration and motion-continuity case tests."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "examples" / "core"
BUILDER = CORE / "gt36_build_trajectory_acceleration.py"
TASK = CORE / "gt36_trajectory_acceleration.yaml"
RESULT = CORE / "gt36_trajectory_acceleration_result.json"
SCENARIO = CORE / "gt36_trajectory_acceleration.json"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_builder():
    spec = importlib.util.spec_from_file_location("gt36_builder", BUILDER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_gt36_fixed_document_validates_and_executes() -> None:
    from geotask_core.parser import load_geotask, validate_document
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    raw = load_geotask(TASK)
    assert validate_document(raw) == []
    result = execute_canonical(canonicalize(raw))
    records = result.outputs["trajectory_acceleration_estimates"]
    assert result.overall.status == "verified"
    assert [record["continuity_state"] for record in records] == [
        "continuous_observation",
        "continuous_observation",
        "unverifiable",
    ]
    assert records[0]["acceleration_in_horizontal_units_per_second_squared"] == 0.0
    assert records[1]["acceleration_in_horizontal_units_per_second_squared"] == (
        1.0 / 300.0
    )
    assert records[2]["acceleration_in_horizontal_units_per_second_squared"] is None
    assert result.checks[0].unit == ""


def test_gt36_fixed_execution_result_is_registered_and_valid() -> None:
    from geotask_core.v1.artifact_validation import validate_artifact_payload
    from geotask_core.v1.result import GeotaskResult

    payload = _json(RESULT)
    result = GeotaskResult.from_dict(payload)
    assert result.task_id == "gt36-trajectory-acceleration"
    assert len(result.outputs["trajectory_acceleration_estimates"]) == 3
    report = validate_artifact_payload(
        "geotask.execution-result",
        payload,
        file=str(RESULT.relative_to(ROOT)),
    ).to_dict()["artifact_validation"]
    assert report["valid"] is True
    assert report["schema_verified"] is True


def test_gt36_scenario_preserves_midpoint_and_gap_contract() -> None:
    scenario = _json(SCENARIO)["scenario"]
    problem = scenario["problem"]
    assert problem["representative_time_method"] == "segment_midpoint"
    assert problem["maximum_observation_gap_seconds"] == 300
    records = scenario["deterministic_estimates"]
    assert [record["representative_interval_seconds"] for record in records] == [
        150.0,
        150.0,
        360.0,
    ]
    assert records[-1]["continuity_state"] == "unverifiable"
    assert records[-1]["speed_change_in_horizontal_units_per_second"] is None
    assert records[-1]["acceleration_in_horizontal_units_per_second_squared"] is None


def test_gt36_never_claims_instantaneous_vector_prediction_or_action() -> None:
    scenario = _json(SCENARIO)["scenario"]
    boundaries = scenario["boundaries"]
    assert boundaries["representative_time_method_explicit"] is True
    assert boundaries["maximum_gap_caller_declared"] is True
    assert boundaries["scalar_acceleration_estimated"] is True
    assert boundaries["gap_transition_failed_closed"] is True
    for key in (
        "instantaneous_acceleration_verified",
        "vector_acceleration_verified",
        "direction_change_inferred",
        "trajectory_interpolated",
        "trajectory_smoothed",
        "trajectory_resampled",
        "continuous_motion_verified",
        "loss_of_link_inferred",
        "anomaly_inferred",
        "future_position_predicted",
        "map_matched",
        "external_truth_verified_by_core",
        "production_output_released",
        "command_sent",
        "action_authorized_by_core",
        "action_executed",
    ):
        assert boundaries[key] is False
    assert "instantaneous_acceleration" in scenario["not_inferred"]
    assert "vector_acceleration" in scenario["not_inferred"]


def test_gt36_hashes_bind_task_and_execution_result() -> None:
    scenario = _json(SCENARIO)["scenario"]
    assert scenario["sha256"] == {
        "task": _sha(TASK),
        "execution_result": _sha(RESULT),
    }


def test_gt36_builder_reproduces_fixed_outputs() -> None:
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


def test_gt36_tampered_parameters_fail_closed() -> None:
    from geotask_core.parser import load_geotask
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.validator import validate_canonical

    payload = load_geotask(TASK)
    del payload["tasks"][0]["assertions"][0]["parameters"][
        "maximum_observation_gap_seconds"
    ]
    diagnostics = validate_canonical(canonicalize(payload))
    assert any(item["code"] == "missing_field" for item in diagnostics)

    payload = load_geotask(TASK)
    payload["tasks"][0]["assertions"][0]["parameters"][
        "representative_time_method"
    ] = "sample_boundary"
    diagnostics = validate_canonical(canonicalize(payload))
    assert any(item["code"] == "invalid_type" for item in diagnostics)
