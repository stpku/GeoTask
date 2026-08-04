"""GT29 fictional weather Provider conflict case tests."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from geotask_core.v1.verification_provider import (
    VerificationProviderFormatError,
    load_verification_provider_descriptor,
    load_verification_request,
    load_verification_response,
    validate_verification_response_bindings,
)


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "examples" / "core"
SCENARIO = CORE / "gt29_weather_provider_conflict.json"
BUILDER = CORE / "gt29_build_weather_provider_conflict.py"
REQUEST = CORE / "verification_request_weather_conflict_gt29.json"
OFFICIAL_DESCRIPTOR = CORE / "verification_provider_descriptor_authoritative_weather_gt29.json"
SENSOR_DESCRIPTOR = CORE / "verification_provider_descriptor_onsite_sensor_gt29.json"
OFFICIAL_RESPONSE = CORE / "verification_response_authoritative_weather_gt29.json"
SENSOR_RESPONSE = CORE / "verification_response_onsite_sensor_gt29.json"
EVALUATION = CORE / "assurance_evaluation_weather_conflict_gt29.json"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_builder():
    spec = importlib.util.spec_from_file_location("gt29_builder", BUILDER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gt29_fixed_scenario_records_two_conflicting_fresh_sources() -> None:
    scenario = _json(SCENARIO)["scenario"]
    assert scenario["facts"] == {
        "authoritative_weather_wind_speed_mps": 8,
        "onsite_sensor_wind_speed_mps": 13,
        "mission_wind_limit_mps": 12,
        "provider_count": 2,
        "independent_group_count": 2,
    }
    assert scenario["result"]["state"] == "unknown"
    assert scenario["result"]["reason"] == "independent_provider_conflict"
    assert scenario["result"]["next_action"] == (
        "request_third_independent_weather_verification"
    )


def test_gt29_fixed_hashes_match_all_bound_artifacts() -> None:
    scenario = _json(SCENARIO)["scenario"]
    expected = scenario["sha256"]
    paths = {
        "official_observation": CORE / "observation_weather_authoritative_gt29.json",
        "sensor_observation": CORE / "observation_weather_onsite_sensor_gt29.json",
        "assurance_profile": CORE / "assurance_profile_weather_conflict_gt29.json",
        "official_descriptor": OFFICIAL_DESCRIPTOR,
        "sensor_descriptor": SENSOR_DESCRIPTOR,
        "verification_request": REQUEST,
        "official_response": OFFICIAL_RESPONSE,
        "sensor_response": SENSOR_RESPONSE,
        "assurance_evaluation": EVALUATION,
    }
    assert {key: _sha(path) for key, path in paths.items()} == expected


def test_gt29_builder_reproduces_fixed_outputs() -> None:
    before = {path.name: path.read_bytes() for path in CORE.glob("*gt29.json")}
    _load_builder().build()
    after = {path.name: path.read_bytes() for path in CORE.glob("*gt29.json")}
    assert after == before


def test_gt29_responses_bind_exact_request_and_descriptor_bytes() -> None:
    request = load_verification_request(_json(REQUEST))
    for descriptor_path, response_path in (
        (OFFICIAL_DESCRIPTOR, OFFICIAL_RESPONSE),
        (SENSOR_DESCRIPTOR, SENSOR_RESPONSE),
    ):
        descriptor = load_verification_provider_descriptor(_json(descriptor_path))
        response = load_verification_response(_json(response_path))
        validate_verification_response_bindings(
            response,
            request=request,
            request_bytes=REQUEST.read_bytes(),
            descriptor=descriptor,
            descriptor_bytes=descriptor_path.read_bytes(),
        )


def test_gt29_tampered_response_binding_fails_closed() -> None:
    request = load_verification_request(_json(REQUEST))
    descriptor = load_verification_provider_descriptor(_json(OFFICIAL_DESCRIPTOR))
    response = load_verification_response(_json(OFFICIAL_RESPONSE))
    with pytest.raises(VerificationProviderFormatError, match="exact bytes"):
        validate_verification_response_bindings(
            response,
            request=request,
            request_bytes=REQUEST.read_bytes() + b"\n",
            descriptor=descriptor,
            descriptor_bytes=OFFICIAL_DESCRIPTOR.read_bytes(),
        )


def test_gt29_does_not_infer_precedence_average_or_action() -> None:
    scenario = _json(SCENARIO)["scenario"]
    assert scenario["incorrect_actions"] == [
        "prefer_authoritative_label",
        "prefer_newer_timestamp",
        "average_values",
        "authorize_takeoff_from_one_source",
    ]
    assert scenario["boundaries"] == {
        "external_truth_verified": False,
        "provider_precedence_inferred": False,
        "values_averaged": False,
        "production_output_released": False,
        "action_authorized": False,
        "action_executed": False,
    }


def test_gt29_keeps_weather_and_takeoff_outputs_blocked() -> None:
    result = _json(EVALUATION)["assurance_evaluation"]
    assert result["eligible_outputs"] == []
    assert result["blocked_outputs"] == [
        "weather_condition_verified",
        "automatic_takeoff_authorization",
    ]
    assert result["blocked_actions"] == ["takeoff_command"]
    assert result["independent_verification_completed"] is False
    assert result["production_output_released"] is False
    assert result["action_authorized"] is False
    assert result["action_executed"] is False
