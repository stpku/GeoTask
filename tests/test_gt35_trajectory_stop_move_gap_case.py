"""GT35 trajectory stop/move and observation-gap case tests."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "examples" / "core"
BUILDER = CORE / "gt35_build_trajectory_stop_move_gap.py"
TASK = CORE / "gt35_trajectory_stop_move_gap.yaml"
RESULT = CORE / "gt35_trajectory_stop_move_gap_result.json"
SCENARIO = CORE / "gt35_trajectory_stop_move_gap.json"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_builder():
    spec = importlib.util.spec_from_file_location("gt35_builder", BUILDER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_gt35_fixed_document_validates_and_executes() -> None:
    from geotask_core.parser import load_geotask, validate_document
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    raw = load_geotask(TASK)
    assert validate_document(raw) == []
    result = execute_canonical(canonicalize(raw))
    records = result.outputs["trajectory_segment_states"]
    assert result.overall.status == "verified"
    assert [record["classification"] for record in records] == [
        "stationary_candidate",
        "moving_observed",
        "observation_gap",
    ]
    assert result.checks[0].unit == ""


def test_gt35_fixed_execution_result_is_registered_and_valid() -> None:
    from geotask_core.v1.artifact_validation import validate_artifact_payload
    from geotask_core.v1.result import GeotaskResult

    payload = _json(RESULT)
    result = GeotaskResult.from_dict(payload)
    assert result.task_id == "gt35-trajectory-stop-move-gap"
    assert len(result.outputs["trajectory_segment_states"]) == 3
    report = validate_artifact_payload(
        "geotask.execution-result",
        payload,
        file=str(RESULT.relative_to(ROOT)),
    ).to_dict()["artifact_validation"]
    assert report["valid"] is True
    assert report["schema_verified"] is True


def test_gt35_scenario_preserves_declared_thresholds_and_gap_policy() -> None:
    scenario = _json(SCENARIO)["scenario"]
    thresholds = scenario["problem"]["thresholds"]
    assert thresholds == {
        "stationary_radius_in_horizontal_unit": 5,
        "minimum_stationary_duration_seconds": 120,
        "maximum_observation_gap_seconds": 300,
        "allow_observation_gap": True,
    }
    assert [
        record["classification"]
        for record in scenario["deterministic_classifications"]
    ] == ["stationary_candidate", "moving_observed", "observation_gap"]
    assert scenario["gap_marking_disallowed"] == {
        "allow_observation_gap": False,
        "classifications": [
            "stationary_candidate",
            "moving_observed",
            "unverifiable",
        ],
        "last_segment_state": "unverifiable",
    }


def test_gt35_never_claims_loss_of_link_anomaly_prediction_or_action() -> None:
    scenario = _json(SCENARIO)["scenario"]
    boundaries = scenario["boundaries"]
    assert boundaries["thresholds_caller_declared"] is True
    assert boundaries["closed_classification_vocabulary_verified"] is True
    for key in (
        "trajectory_interpolated",
        "trajectory_smoothed",
        "trajectory_resampled",
        "continuous_stationary_state_verified",
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
    assert "loss_of_link" in scenario["not_inferred"]
    assert "anomaly" in scenario["not_inferred"]


def test_gt35_hashes_bind_task_and_execution_result() -> None:
    scenario = _json(SCENARIO)["scenario"]
    assert scenario["sha256"] == {
        "task": _sha(TASK),
        "execution_result": _sha(RESULT),
    }


def test_gt35_builder_reproduces_fixed_outputs() -> None:
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


def test_gt35_tampered_thresholds_fail_closed() -> None:
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
        "allow_observation_gap"
    ] = "yes"
    diagnostics = validate_canonical(canonicalize(payload))
    assert any(item["code"] == "invalid_type" for item in diagnostics)
