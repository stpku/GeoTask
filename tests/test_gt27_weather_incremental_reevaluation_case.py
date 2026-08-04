from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from geotask_core.v1.correction_request import load_correction_request
from geotask_core.v1.discrepancy_report import (
    DiscrepancyReportFormatError,
    load_discrepancy_report,
    validate_discrepancy_report_bindings,
)
from geotask_core.v1.impact_graph import load_impact_graph
from geotask_core.v1.incremental_reevaluation_result import (
    IncrementalReevaluationResultFormatError,
    load_incremental_reevaluation_result,
    validate_incremental_reevaluation_result_bindings,
)
from geotask_core.v1.observation import load_observation
from geotask_core.v1.result import GeotaskResult
from geotask_core.v1.world_state import load_world_state


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "examples" / "core"
SCENARIO = CORE / "gt27_weather_incremental_reevaluation.json"
OBSERVATION = CORE / "observation_weather_wind_speed_gt27.json"
BASE = CORE / "world_state_weather_missions_base_gt27.json"
SUCCESSOR = CORE / "world_state_weather_missions_successor_gt27.json"
DISCREPANCY = CORE / "discrepancy_report_weather_wind_gt27.json"
CORRECTION = CORE / "correction_request_weather_wind_gt27.json"
GRAPH = CORE / "impact_graph_weather_missions_gt27.json"
EXECUTION = CORE / "incremental_reevaluation_weather_execution_result_gt27.json"
RESULT = CORE / "incremental_reevaluation_result_weather_gt27.json"
BUILDER_PATH = CORE / "gt27_build_incremental_reevaluation.py"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _raw(payload: dict) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _load_builder():
    spec = importlib.util.spec_from_file_location("gt27_builder", BUILDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILDER = _load_builder()


def _dependencies():
    return (
        load_world_state(_json(BASE)),
        load_world_state(_json(SUCCESSOR)),
        load_discrepancy_report(_json(DISCREPANCY)),
        load_correction_request(_json(CORRECTION)),
        load_impact_graph(_json(GRAPH)),
        GeotaskResult.from_dict(_json(EXECUTION)),
        load_incremental_reevaluation_result(_json(RESULT)),
    )


def _contents() -> dict[str, bytes]:
    return {
        "base-world-state-gt27": BASE.read_bytes(),
        "successor-world-state-gt27": SUCCESSOR.read_bytes(),
        "discrepancy-weather-gt27": DISCREPANCY.read_bytes(),
        "correction-weather-gt27": CORRECTION.read_bytes(),
        "impact-graph-weather-gt27": GRAPH.read_bytes(),
        "execution-weather-gt27": EXECUTION.read_bytes(),
    }


def test_gt27_fixed_artifacts_are_strict_and_schema_valid() -> None:
    load_observation(_json(OBSERVATION))
    base, successor, report, request, graph, execution, result = _dependencies()
    assert base.revision == 7
    assert successor.revision == 8
    assert report.state == "confirmed"
    assert request.state == "required"
    assert graph.state == "blocked"
    assert execution.task_id == "gt27-weather-affected-mission-recheck"
    assert result.state == "completed"

    for schema_name, payload in (
        ("geotask-observation-v0.1.schema.json", _json(OBSERVATION)),
        ("geotask-world-state-v0.1.schema.json", _json(BASE)),
        ("geotask-world-state-v0.1.schema.json", _json(SUCCESSOR)),
        ("geotask-discrepancy-report-v0.1.schema.json", _json(DISCREPANCY)),
        ("geotask-correction-request-v0.1.schema.json", _json(CORRECTION)),
        ("geotask-impact-graph-v0.1.schema.json", _json(GRAPH)),
        ("geotask-result-v1.0.schema.json", _json(EXECUTION)),
        ("geotask-incremental-reevaluation-result-v0.1.schema.json", _json(RESULT)),
    ):
        schema = _json(ROOT / "schemas" / schema_name)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(payload)


def test_gt27_builder_reproduces_all_fixed_artifacts_and_fingerprints() -> None:
    bundle = BUILDER.build_gt27_incremental_reevaluation(SCENARIO)
    expected = _json(SCENARIO)["scenario"]["expected"]
    filenames = {
        "successor_world_state": SUCCESSOR,
        "discrepancy_report": DISCREPANCY,
        "correction_request": CORRECTION,
        "impact_graph": GRAPH,
        "execution_result": EXECUTION,
        "incremental_result": RESULT,
    }
    for key, path in filenames.items():
        assert bundle["bytes"][key] == path.read_bytes()

    assert bundle["base_world_state"].semantic_fingerprint() == expected[
        "base_world_state_semantic_fingerprint"
    ]
    assert bundle["successor_world_state"].semantic_fingerprint() == expected[
        "successor_world_state_semantic_fingerprint"
    ]
    assert bundle["discrepancy_report"].semantic_fingerprint() == expected[
        "discrepancy_semantic_fingerprint"
    ]
    assert bundle["correction_request"].semantic_fingerprint() == expected[
        "correction_semantic_fingerprint"
    ]
    assert bundle["impact_graph"].semantic_fingerprint() == expected[
        "impact_graph_semantic_fingerprint"
    ]
    assert bundle["incremental_result"].semantic_fingerprint() == expected[
        "incremental_result_semantic_fingerprint"
    ]


def test_gt27_reevaluates_only_a_and_d_while_b_and_c_are_reused() -> None:
    base, successor, _, _, graph, execution, result = _dependencies()
    assertions = {node.identity for node in graph.nodes if node.kind == "assertion"}
    assert assertions == {
        "mission_a_wind_within_limit",
        "mission_d_wind_within_limit",
    }
    assert set(execution.outputs) == assertions
    assert execution.outputs == {
        "mission_a_wind_within_limit": False,
        "mission_d_wind_within_limit": True,
    }

    base_relations = {item.id: item.value for item in base.relations}
    successor_relations = {item.id: item.value for item in successor.relations}
    assert base_relations["mission-a-weather-suitable"] is True
    assert successor_relations["mission-a-weather-suitable"] is False
    assert base_relations["mission-d-weather-suitable"] is True
    assert successor_relations["mission-d-weather-suitable"] is True
    assert successor_relations["mission-b-weather-suitable"] is True
    assert successor_relations["mission-c-weather-suitable"] is True
    assert len(result.target_results) == 4
    assert len(result.output_gates) == 2
    assert all(item.state == "released" for item in result.output_gates)


def test_gt27_exact_bindings_reject_tampered_observation_or_execution_bytes() -> None:
    base, successor, report, request, graph, execution, result = _dependencies()
    validate_discrepancy_report_bindings(
        report,
        base,
        {"weather-observation-gt27": OBSERVATION.read_bytes()},
    )
    with pytest.raises(DiscrepancyReportFormatError, match="SHA-256 mismatch"):
        validate_discrepancy_report_bindings(
            report,
            base,
            {"weather-observation-gt27": OBSERVATION.read_bytes() + b"\n"},
        )

    contents = _contents()
    contents["execution-weather-gt27"] += b"\n"
    with pytest.raises(IncrementalReevaluationResultFormatError, match="SHA-256 mismatch"):
        validate_incremental_reevaluation_result_bindings(
            result,
            base,
            successor,
            graph,
            {"correction-weather-gt27": request},
            {"discrepancy-weather-gt27": report},
            {"execution-weather-gt27": execution},
            contents,
        )


def test_gt27_fails_closed_when_excluded_mission_enters_declared_scope(tmp_path: Path) -> None:
    for filename in (
        SCENARIO.name,
        OBSERVATION.name,
        BASE.name,
    ):
        shutil.copy2(CORE / filename, tmp_path / filename)
    scenario_path = tmp_path / SCENARIO.name
    payload = _json(scenario_path)
    payload["scenario"]["declared_scope"]["reevaluation_targets"].append(
        "mission_b_wind_within_limit"
    )
    scenario_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    with pytest.raises(BUILDER.GT27BuildError, match="assertion scope"):
        BUILDER.build_gt27_incremental_reevaluation(scenario_path)


def test_gt27_rejects_change_to_immutable_mission_b_result() -> None:
    base, _, report, request, graph, execution, _ = _dependencies()
    successor_payload = _json(SUCCESSOR)
    relation = next(
        item
        for item in successor_payload["world_state"]["relations"]
        if item["id"] == "mission-b-weather-suitable"
    )
    relation["value"] = False
    successor_bytes = _raw(successor_payload)
    successor = load_world_state(successor_payload)

    result_payload = _json(RESULT)
    successor_ref = result_payload["incremental_reevaluation_result"][
        "successor_world_state"
    ]
    successor_ref["semantic_fingerprint"] = successor.semantic_fingerprint()
    successor_ref["content_sha256"] = hashlib.sha256(successor_bytes).hexdigest()
    result = load_incremental_reevaluation_result(result_payload)
    contents = _contents()
    contents["successor-world-state-gt27"] = successor_bytes

    with pytest.raises(
        IncrementalReevaluationResultFormatError,
        match="outside requested paths|immutable path changed",
    ):
        validate_incremental_reevaluation_result_bindings(
            result,
            base,
            successor,
            graph,
            {"correction-weather-gt27": request},
            {"discrepancy-weather-gt27": report},
            {"execution-weather-gt27": execution},
            contents,
        )


def test_gt27_records_release_in_artifact_without_authorizing_action() -> None:
    _, _, _, _, _, _, result = _dependencies()
    assert {item.output_ref for item in result.output_gates} == {
        "mission_a_weather_assessment",
        "mission_d_weather_assessment",
    }
    assert result.action_gates == ()
    assert result.next_action == "none"
    boundary = _json(SCENARIO)["scenario"]["safety_boundary"]
    assert boundary["artifact_output_gates_recorded_released"] is True
    assert boundary["production_outputs_released"] is False
    assert boundary["action_authorized"] is False
    assert boundary["action_executed"] is False
