"""GT30 three-source weather conflict case tests."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from geotask_core.v1.verification_provider import (
    VerificationProviderFormatError,
    evaluate_verification_assurance,
    load_assurance_profile,
    load_verification_provider_descriptor,
    load_verification_request,
    load_verification_response,
    validate_verification_response_bindings,
)


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "examples" / "core"
SCENARIO = CORE / "gt30_three_source_weather_conflict.json"
BUILDER = CORE / "gt30_build_three_source_weather_conflict.py"
PROFILE = CORE / "assurance_profile_weather_three_source_gt30.json"
REQUEST = CORE / "verification_request_weather_three_source_gt30.json"
OFFICIAL_DESCRIPTOR = CORE / "verification_provider_descriptor_authoritative_weather_gt29.json"
SENSOR_DESCRIPTOR = CORE / "verification_provider_descriptor_onsite_sensor_gt29.json"
LIDAR_DESCRIPTOR = CORE / "verification_provider_descriptor_mobile_lidar_gt30.json"
OFFICIAL_RESPONSE = CORE / "verification_response_authoritative_weather_gt30.json"
SENSOR_RESPONSE = CORE / "verification_response_onsite_sensor_gt30.json"
LIDAR_RESPONSE = CORE / "verification_response_mobile_lidar_gt30.json"
EVALUATION = CORE / "assurance_evaluation_weather_three_source_gt30.json"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_builder():
    spec = importlib.util.spec_from_file_location("gt30_builder", BUILDER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gt30_records_three_usable_independent_sources_and_two_matching_values() -> None:
    scenario = _json(SCENARIO)["scenario"]
    assert scenario["facts"] == {
        "authoritative_weather_wind_speed_mps": 8,
        "onsite_sensor_wind_speed_mps": 13,
        "mobile_lidar_wind_speed_mps": 13,
        "mission_wind_limit_mps": 12,
        "provider_count": 3,
        "usable_provider_count": 3,
        "independent_group_count": 3,
        "agreeing_provider_count_for_13_mps": 2,
    }
    assert scenario["result"]["state"] == "unknown"
    assert scenario["result"]["reason"] == "independent_provider_conflict"
    assert scenario["result"]["next_action"] == "request_explicit_weather_adjudication"


def test_gt30_fixed_hashes_match_all_bound_artifacts() -> None:
    expected = _json(SCENARIO)["scenario"]["sha256"]
    paths = {
        "official_observation": CORE / "observation_weather_authoritative_gt29.json",
        "sensor_observation": CORE / "observation_weather_onsite_sensor_gt29.json",
        "lidar_observation": CORE / "observation_weather_mobile_lidar_gt30.json",
        "assurance_profile": PROFILE,
        "official_descriptor": OFFICIAL_DESCRIPTOR,
        "sensor_descriptor": SENSOR_DESCRIPTOR,
        "lidar_descriptor": LIDAR_DESCRIPTOR,
        "verification_request": REQUEST,
        "official_response": OFFICIAL_RESPONSE,
        "sensor_response": SENSOR_RESPONSE,
        "lidar_response": LIDAR_RESPONSE,
        "assurance_evaluation": EVALUATION,
    }
    assert {key: _sha(path) for key, path in paths.items()} == expected


def test_gt30_builder_reproduces_fixed_outputs() -> None:
    before = {path.name: path.read_bytes() for path in CORE.glob("*gt30.json")}
    _load_builder().build()
    after = {path.name: path.read_bytes() for path in CORE.glob("*gt30.json")}
    assert after == before


def test_gt30_all_three_responses_bind_exact_request_and_descriptor_bytes() -> None:
    request = load_verification_request(_json(REQUEST))
    for descriptor_path, response_path in (
        (OFFICIAL_DESCRIPTOR, OFFICIAL_RESPONSE),
        (SENSOR_DESCRIPTOR, SENSOR_RESPONSE),
        (LIDAR_DESCRIPTOR, LIDAR_RESPONSE),
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


def test_gt30_tampered_third_descriptor_binding_fails_closed() -> None:
    request = load_verification_request(_json(REQUEST))
    descriptor = load_verification_provider_descriptor(_json(LIDAR_DESCRIPTOR))
    response = load_verification_response(_json(LIDAR_RESPONSE))
    with pytest.raises(VerificationProviderFormatError, match="exact bytes"):
        validate_verification_response_bindings(
            response,
            request=request,
            request_bytes=REQUEST.read_bytes(),
            descriptor=descriptor,
            descriptor_bytes=LIDAR_DESCRIPTOR.read_bytes() + b"\n",
        )


def test_gt30_two_matching_sources_do_not_satisfy_three_source_profile() -> None:
    profile = load_assurance_profile(_json(PROFILE))
    request = load_verification_request(_json(REQUEST))
    sensor_descriptor = load_verification_provider_descriptor(_json(SENSOR_DESCRIPTOR))
    lidar_descriptor = load_verification_provider_descriptor(_json(LIDAR_DESCRIPTOR))
    sensor_response = load_verification_response(_json(SENSOR_RESPONSE))
    lidar_response = load_verification_response(_json(LIDAR_RESPONSE))
    result = evaluate_verification_assurance(
        profile,
        request=request,
        bound_results=[
            (sensor_descriptor, sensor_response),
            (lidar_descriptor, lidar_response),
        ],
        evaluated_at="2026-08-04T14:06:30+08:00",
    )["assurance_evaluation"]
    assert result["state"] == "unknown"
    assert result["reason"] == "insufficient_assurance"
    assert {item["code"] for item in result["diagnostics"]} == {
        "insufficient_provider_count",
        "insufficient_independent_groups",
    }


def test_gt30_keeps_outputs_and_actions_blocked_without_majority_policy() -> None:
    scenario = _json(SCENARIO)["scenario"]
    result = _json(EVALUATION)["assurance_evaluation"]
    assert scenario["incorrect_actions"] == [
        "apply_implicit_majority_vote",
        "discard_minority_source_without_adjudication",
        "convert_two_matching_values_to_verified",
        "authorize_takeoff_from_two_of_three_sources",
    ]
    assert scenario["boundaries"] == {
        "majority_policy_declared": False,
        "minority_source_discarded": False,
        "provider_precedence_inferred": False,
        "external_truth_verified": False,
        "production_output_released": False,
        "action_authorized": False,
        "action_executed": False,
    }
    assert result["eligible_outputs"] == []
    assert result["blocked_outputs"] == [
        "weather_condition_verified",
        "automatic_takeoff_authorization",
    ]
    assert result["blocked_actions"] == ["takeoff_command"]
    assert result["independent_verification_completed"] is False
    assert result["action_executed"] is False
