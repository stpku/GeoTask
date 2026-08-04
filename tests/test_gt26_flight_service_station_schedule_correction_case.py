from __future__ import annotations

import copy
import importlib.util
import json
import shutil
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from geotask_core.v1.correction_request import (
    CorrectionRequestFormatError,
    load_correction_request,
    validate_correction_request_bindings,
)
from geotask_core.v1.discrepancy_report import (
    DiscrepancyReportFormatError,
    load_discrepancy_report,
    validate_discrepancy_report_bindings,
)
from geotask_core.v1.observation import load_observation
from geotask_core.v1.world_state import load_world_state


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "examples" / "core"
SCENARIO = CORE / "gt26_flight_service_station_schedule_correction.json"
OBSERVATION = CORE / "observation_flight_service_station_schedule_gt26.json"
WORLD_STATE = CORE / "world_state_flight_service_station_gt26.json"
DISCREPANCY = CORE / "discrepancy_report_flight_service_station_gt26.json"
CORRECTION = CORE / "correction_request_flight_service_station_gt26.json"
BUILDER_PATH = CORE / "gt26_build_schedule_correction.py"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_builder():
    spec = importlib.util.spec_from_file_location("gt26_builder", BUILDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILDER = _load_builder()


def _copy_case(tmp_path: Path) -> Path:
    for filename in (
        "gt26_flight_service_station_schedule_correction.json",
        "observation_flight_service_station_schedule_gt26.json",
        "world_state_flight_service_station_gt26.json",
    ):
        shutil.copy2(CORE / filename, tmp_path / filename)
    return tmp_path / "gt26_flight_service_station_schedule_correction.json"


def test_gt26_fixed_artifacts_are_strict_and_schema_valid() -> None:
    observation = load_observation(_json(OBSERVATION))
    world_state = load_world_state(_json(WORLD_STATE))
    report = load_discrepancy_report(_json(DISCREPANCY))
    request = load_correction_request(_json(CORRECTION))

    for schema_name, payload in (
        ("geotask-observation-v0.1.schema.json", _json(OBSERVATION)),
        ("geotask-world-state-v0.1.schema.json", _json(WORLD_STATE)),
        ("geotask-discrepancy-report-v0.1.schema.json", _json(DISCREPANCY)),
        ("geotask-correction-request-v0.1.schema.json", _json(CORRECTION)),
    ):
        schema = _json(ROOT / "schemas" / schema_name)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(payload)

    assert observation.observation_id == "obs-flight-service-station-schedule-gt26"
    assert world_state.revision == 4
    assert report.state == "confirmed"
    assert request.state == "required"


def test_gt26_builder_reproduces_fixed_artifacts_and_fingerprints() -> None:
    expected = _json(SCENARIO)["scenario"]["expected"]
    world_state, report, request, report_bytes, request_bytes = (
        BUILDER.build_gt26_schedule_correction(SCENARIO)
    )

    assert report_bytes == DISCREPANCY.read_bytes()
    assert request_bytes == CORRECTION.read_bytes()
    assert world_state.semantic_fingerprint() == expected["world_state_semantic_fingerprint"]
    assert report.semantic_fingerprint() == expected["discrepancy_semantic_fingerprint"]
    assert request.semantic_fingerprint() == expected["correction_semantic_fingerprint"]


def test_gt26_changes_only_schedule_and_preserves_station_attributes() -> None:
    scenario = _json(SCENARIO)["scenario"]
    world_state, report, request, *_ = BUILDER.build_gt26_schedule_correction(SCENARIO)
    finding = report.discrepancies[0]
    change = request.changes[0]

    assert finding.expected == scenario["expected"]["new_schedule"]
    assert finding.observed == scenario["expected"]["old_schedule"]
    assert set(finding.correction_scope.mutable_paths) == set(
        scenario["declared_scope"]["mutable_paths"]
    )
    assert set(finding.correction_scope.immutable_paths) == set(
        scenario["declared_scope"]["immutable_paths"]
    )
    assert change.operation == "replace"
    assert change.target_path == scenario["declared_scope"]["mutable_paths"][0]
    assert change.before == scenario["expected"]["old_schedule"]
    assert change.after == scenario["expected"]["new_schedule"]
    for name, expected_value in scenario["expected"]["preserved_values"].items():
        assert BUILDER._attribute_value(
            world_state, "flight-service-station-east", name
        ) == expected_value


def test_gt26_blocks_mission_output_and_dispatch_until_recheck() -> None:
    scenario = _json(SCENARIO)["scenario"]
    _, _, request, *_ = BUILDER.build_gt26_schedule_correction(SCENARIO)

    assert set(request.blocked_outputs) == set(
        scenario["declared_scope"]["blocked_outputs"]
    )
    assert set(request.blocked_actions) == set(
        scenario["declared_scope"]["blocked_actions"]
    )
    assert request.next_action == "materialize_successor_state"
    assert "mission_27_service_availability_rechecked" in request.resume_when
    assert any(
        criterion.kind == "recheck_completed"
        and criterion.output_refs == ("mission_27_service_availability",)
        for criterion in request.acceptance_criteria
    )


def test_gt26_exact_byte_bindings_cover_notice_state_and_report() -> None:
    world_state = load_world_state(_json(WORLD_STATE))
    report = load_discrepancy_report(_json(DISCREPANCY))
    request = load_correction_request(_json(CORRECTION))

    validate_discrepancy_report_bindings(
        report,
        world_state,
        {"schedule-notice-gt26": OBSERVATION.read_bytes()},
    )
    validate_correction_request_bindings(
        request,
        world_state,
        {"discrepancy-gt26": report},
        {
            "base-world-state-gt26": WORLD_STATE.read_bytes(),
            "discrepancy-gt26": DISCREPANCY.read_bytes(),
        },
    )

    with pytest.raises(DiscrepancyReportFormatError, match="SHA-256 mismatch"):
        validate_discrepancy_report_bindings(
            report,
            world_state,
            {"schedule-notice-gt26": OBSERVATION.read_bytes() + b"\n"},
        )


def test_gt26_fails_closed_when_mutable_scope_is_expanded(tmp_path: Path) -> None:
    scenario_path = _copy_case(tmp_path)
    payload = _json(scenario_path)
    payload["scenario"]["declared_scope"]["mutable_paths"].append(
        "/objects/flight-service-station-east/attributes/radio_frequency_mhz/value"
    )
    scenario_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    with pytest.raises(BUILDER.GT26BuildError, match="exactly one mutable"):
        BUILDER.build_gt26_schedule_correction(scenario_path)


def test_gt26_rejects_overlap_wrong_after_and_missing_recheck() -> None:
    overlap = copy.deepcopy(_json(DISCREPANCY))
    overlap["discrepancy_report"]["discrepancies"][0]["correction_scope"][
        "immutable_paths"
    ].append(
        "/objects/flight-service-station-east/attributes/operating_schedule/value"
    )
    with pytest.raises(DiscrepancyReportFormatError, match="overlap"):
        load_discrepancy_report(overlap)

    wrong_after = copy.deepcopy(_json(CORRECTION))
    wrong_after["correction_request"]["changes"][0]["after"]["end"] = "19:00"
    with pytest.raises(CorrectionRequestFormatError, match="path_equals"):
        load_correction_request(wrong_after)

    missing_recheck = copy.deepcopy(_json(CORRECTION))
    missing_recheck["correction_request"]["acceptance_criteria"] = [
        item
        for item in missing_recheck["correction_request"]["acceptance_criteria"]
        if item["kind"] != "recheck_completed"
    ]
    with pytest.raises(CorrectionRequestFormatError, match="recheck_completed"):
        load_correction_request(missing_recheck)
