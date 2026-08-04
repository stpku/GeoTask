from __future__ import annotations

import copy
import importlib.util
import json
import shutil
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from geotask_core.v1.artifact_validation import validate_artifact_payload
from geotask_core.v1.correction_request import (
    load_correction_request,
    validate_correction_request_bindings,
)
from geotask_core.v1.discrepancy_report import (
    load_discrepancy_report,
    validate_discrepancy_report_bindings,
)
from geotask_core.v1.observation import load_observation
from geotask_core.v1.recompute_derivation import (
    RecomputeDerivationError,
    evaluate_recompute_derivations,
    load_recompute_derivation_result,
    validate_recompute_derivation_bindings,
)
from geotask_core.v1.world_state import load_world_state


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "examples" / "core"
SCENARIO = CORE / "gt25_corridor_safety_recompute.json"
OBSERVATION = CORE / "observation_uav_corridor_position_gt25.json"
TASK = CORE / "gt25_corridor_safety_distance_task.yaml"
WORLD_STATE = CORE / "world_state_corridor_safety_gt25.json"
DISCREPANCY = CORE / "discrepancy_report_corridor_safety_gt25.json"
CORRECTION = CORE / "correction_request_corridor_safety_gt25.json"
DERIVATION = CORE / "recompute_derivation_result_corridor_safety_gt25.json"
BUILDER_PATH = CORE / "gt25_build_bounded_recompute.py"


def _load_builder():
    spec = importlib.util.spec_from_file_location("gt25_builder", BUILDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILDER = _load_builder()


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _task_payload() -> dict:
    return yaml.safe_load(TASK.read_text(encoding="utf-8"))


def _copy_case(tmp_path: Path) -> Path:
    for filename in (
        "gt25_corridor_safety_recompute.json",
        "observation_uav_corridor_position_gt25.json",
        "gt25_corridor_safety_distance_task.yaml",
        "world_state_corridor_safety_gt25.json",
    ):
        shutil.copy2(CORE / filename, tmp_path / filename)
    return tmp_path / "gt25_corridor_safety_recompute.json"


def test_gt25_fixed_source_and_output_artifacts_are_strictly_valid() -> None:
    observation = load_observation(_json(OBSERVATION))
    world_state = load_world_state(_json(WORLD_STATE))
    report = load_discrepancy_report(_json(DISCREPANCY))
    request = load_correction_request(_json(CORRECTION))
    result = load_recompute_derivation_result(_json(DERIVATION))

    for schema_name, payload in (
        ("geotask-observation-v0.1.schema.json", _json(OBSERVATION)),
        ("geotask-world-state-v0.1.schema.json", _json(WORLD_STATE)),
        ("geotask-discrepancy-report-v0.1.schema.json", _json(DISCREPANCY)),
        ("geotask-correction-request-v0.1.schema.json", _json(CORRECTION)),
        ("geotask-recompute-derivation-result-v0.1.schema.json", _json(DERIVATION)),
    ):
        schema = _json(ROOT / "schemas" / schema_name)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(payload)

    task_validation = validate_artifact_payload(
        "geotask.document", _task_payload(), file=TASK.as_posix()
    )
    assert task_validation.valid is True
    assert observation.observation_id == "obs-uav-alpha-corridor-position-gt25"
    assert world_state.revision == 2
    assert request.state == "required"
    assert result.state == "completed"


def test_gt25_builder_reproduces_exact_artifacts_and_fingerprints() -> None:
    expected = _json(SCENARIO)["scenario"]["expected"]
    world_state, report, request, result, report_bytes, request_bytes, result_bytes = (
        BUILDER.build_gt25_bounded_recompute(SCENARIO)
    )

    assert report_bytes == DISCREPANCY.read_bytes()
    assert request_bytes == CORRECTION.read_bytes()
    assert result_bytes == DERIVATION.read_bytes()
    assert world_state.semantic_fingerprint() == expected["world_state_semantic_fingerprint"]
    assert report.semantic_fingerprint() == expected["discrepancy_semantic_fingerprint"]
    assert request.semantic_fingerprint() == expected["correction_semantic_fingerprint"]
    assert result.semantic_fingerprint() == expected["derivation_semantic_fingerprint"]


def test_gt25_recomputes_only_uav_dependent_distances() -> None:
    scenario = _json(SCENARIO)["scenario"]
    world_state, _, request, result, *_ = BUILDER.build_gt25_bounded_recompute(SCENARIO)
    values = evaluate_recompute_derivations(result)

    assert values == {
        "recompute-uav-crane-distance": 20,
        "recompute-uav-tower-distance": 130,
    }
    assert {change.target_path for change in request.changes} == set(
        scenario["declared_scope"]["recompute_paths"]
    )
    assert BUILDER._resolve_world_state_value(
        world_state, "/relations/crane-tower-distance/value"
    ) == 110
    assert BUILDER._resolve_world_state_value(
        world_state, "/objects/uav-alpha/attributes/battery_percent/value"
    ) == 48


def test_gt25_exact_bindings_cover_report_request_and_derivation() -> None:
    observation = load_observation(_json(OBSERVATION))
    world_state = load_world_state(_json(WORLD_STATE))
    report = load_discrepancy_report(_json(DISCREPANCY))
    request = load_correction_request(_json(CORRECTION))
    result = load_recompute_derivation_result(_json(DERIVATION))

    validate_discrepancy_report_bindings(
        report,
        world_state,
        {
            "observation-position-gt25": OBSERVATION.read_bytes(),
            "task-gt25": TASK.read_bytes(),
        },
    )
    validate_correction_request_bindings(
        request,
        world_state,
        {"discrepancy-gt25": report},
        {
            "base-world-state-gt25": WORLD_STATE.read_bytes(),
            "discrepancy-gt25": DISCREPANCY.read_bytes(),
            "task-gt25": TASK.read_bytes(),
        },
    )
    validate_recompute_derivation_bindings(
        result,
        world_state,
        request,
        {
            "observation-position-gt25": _json(OBSERVATION),
            "task-gt25": _task_payload(),
        },
        {
            "base-world-state-gt25": WORLD_STATE.read_bytes(),
            "correction-gt25": CORRECTION.read_bytes(),
            "observation-position-gt25": OBSERVATION.read_bytes(),
            "task-gt25": TASK.read_bytes(),
        },
    )
    assert observation.source.reference in request.evidence_refs


def test_gt25_fails_closed_when_recompute_scope_is_incomplete(tmp_path: Path) -> None:
    scenario_path = _copy_case(tmp_path)
    payload = _json(scenario_path)
    payload["scenario"]["declared_scope"]["recompute_paths"].pop()
    scenario_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    with pytest.raises(BUILDER.GT25BuildError, match="declared recompute scope mismatch"):
        BUILDER.build_gt25_bounded_recompute(scenario_path)


def test_gt25_fails_closed_when_reuse_scope_overlaps_recompute(tmp_path: Path) -> None:
    scenario_path = _copy_case(tmp_path)
    payload = _json(scenario_path)
    payload["scenario"]["declared_scope"]["reuse_paths"].append(
        "/relations/uav-alpha-crane-distance/value"
    )
    scenario_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    with pytest.raises(BUILDER.GT25BuildError, match="must be disjoint"):
        BUILDER.build_gt25_bounded_recompute(scenario_path)


def test_gt25_rejects_unallowlisted_method_and_tampered_source_bytes() -> None:
    payload = copy.deepcopy(_json(DERIVATION))
    payload["recompute_derivation_result"]["derivations"][0]["method"] = "python_eval"
    with pytest.raises(RecomputeDerivationError, match="must be one of"):
        load_recompute_derivation_result(payload)

    world_state = load_world_state(_json(WORLD_STATE))
    request = load_correction_request(_json(CORRECTION))
    result = load_recompute_derivation_result(_json(DERIVATION))
    with pytest.raises(RecomputeDerivationError, match="SHA-256 mismatch"):
        validate_recompute_derivation_bindings(
            result,
            world_state,
            request,
            {
                "observation-position-gt25": _json(OBSERVATION),
                "task-gt25": _task_payload(),
            },
            {
                "base-world-state-gt25": WORLD_STATE.read_bytes(),
                "correction-gt25": CORRECTION.read_bytes(),
                "observation-position-gt25": OBSERVATION.read_bytes() + b"\n",
                "task-gt25": TASK.read_bytes(),
            },
        )
