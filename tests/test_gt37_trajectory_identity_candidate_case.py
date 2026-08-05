"""GT37 trajectory identity-candidate case tests."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "examples" / "core"
BUILDER = CORE / "gt37_build_trajectory_identity_candidate.py"
TASK = CORE / "gt37_trajectory_identity_candidate.yaml"
RESULT = CORE / "gt37_trajectory_identity_candidate_result.json"
SCENARIO = CORE / "gt37_trajectory_identity_candidate.json"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_builder():
    spec = importlib.util.spec_from_file_location("gt37_builder", BUILDER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_gt37_fixed_document_validates_and_executes_without_merge() -> None:
    from geotask_core.parser import load_geotask, validate_document
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    raw = load_geotask(TASK)
    assert validate_document(raw) == []
    canonical = canonicalize(raw)
    before = {
        ref: canonical.objects[ref].data.get("subject_ref")
        for ref in ("track_alpha", "track_beta")
    }
    result = execute_canonical(canonical)
    record = result.outputs["identity_candidate"]
    after = {
        ref: canonical.objects[ref].data.get("subject_ref")
        for ref in ("track_alpha", "track_beta")
    }
    assert result.overall.status == "verified"
    assert record["candidate_state"] == "same_object_candidate"
    assert record["temporal_gap_seconds"] == 60.0
    assert record["spatial_distance_in_horizontal_unit"] == 5.0
    assert record["identity_merge_performed"] is False
    assert record["subject_refs_mutated"] is False
    assert before == after == {
        "track_alpha": "provisional_alpha",
        "track_beta": "provisional_beta",
    }


def test_gt37_result_is_registered_and_valid() -> None:
    from geotask_core.v1.artifact_validation import validate_artifact_payload
    from geotask_core.v1.result import GeotaskResult

    payload = _json(RESULT)
    result = GeotaskResult.from_dict(payload)
    assert result.task_id == "gt37-trajectory-identity-candidate"
    assert result.outputs["identity_candidate"]["candidate_state"] == (
        "same_object_candidate"
    )
    report = validate_artifact_payload(
        "geotask.execution-result", payload, file=str(RESULT.relative_to(ROOT))
    ).to_dict()["artifact_validation"]
    assert report["valid"] is True
    assert report["schema_verified"] is True


def test_gt37_scenario_preserves_candidate_not_identity_boundary() -> None:
    scenario = _json(SCENARIO)["scenario"]
    assert scenario["deterministic_candidate"]["candidate_state"] == (
        "same_object_candidate"
    )
    assert scenario["alternative_outcomes"] == {
        "far_boundary": "different_object_candidate",
        "class_mismatch_when_required": "different_object_candidate",
        "temporal_gap_exceeds_maximum": "unverifiable",
    }
    assert "real_world_identity_equality" in scenario["not_inferred"]
    boundaries = scenario["boundaries"]
    assert boundaries["same_object_candidate_computed"] is True
    assert boundaries["real_world_identity_verified"] is False
    assert boundaries["identity_merge_performed"] is False
    assert boundaries["subject_refs_mutated"] is False


def test_gt37_hashes_bind_task_and_execution_result() -> None:
    scenario = _json(SCENARIO)["scenario"]
    assert scenario["sha256"] == {
        "task": _sha(TASK),
        "execution_result": _sha(RESULT),
    }


def test_gt37_builder_reproduces_fixed_outputs() -> None:
    before = {RESULT.name: RESULT.read_bytes(), SCENARIO.name: SCENARIO.read_bytes()}
    _load_builder().build()
    after = {RESULT.name: RESULT.read_bytes(), SCENARIO.name: SCENARIO.read_bytes()}
    assert after == before


def test_gt37_does_not_publish_authorize_or_execute() -> None:
    boundaries = _json(SCENARIO)["scenario"]["boundaries"]
    for key in (
        "trajectory_interpolated",
        "trajectory_smoothed",
        "trajectory_resampled",
        "map_matched",
        "future_position_predicted",
        "external_truth_verified_by_core",
        "production_output_released",
        "command_sent",
        "action_authorized_by_core",
        "action_executed",
    ):
        assert boundaries[key] is False
