"""GT31 human weather adjudication case tests."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from geotask_core.v1.control_evaluation import load_control_evaluation
from geotask_core.v1.verification_provider import (
    VerificationProviderFormatError,
    load_verification_provider_descriptor,
    load_verification_request,
    load_verification_response,
    validate_verification_response_bindings,
)


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "examples" / "core"
BUILDER = CORE / "gt31_build_human_weather_adjudication.py"
SCENARIO = CORE / "gt31_human_weather_adjudication.json"
CONTEXT = CORE / "weather_context_evidence_gt31.json"
PROFILE = CORE / "assurance_profile_human_weather_adjudication_gt31.json"
DESCRIPTOR = CORE / "verification_provider_descriptor_human_weather_reviewer_gt31.json"
REQUEST = CORE / "verification_request_human_weather_adjudication_gt31.json"
RESPONSE = CORE / "verification_response_human_weather_adjudication_gt31.json"
EVALUATION = CORE / "assurance_evaluation_human_weather_adjudication_gt31.json"
GT28_CONTROL = CORE / "takeoff_authorization_control_evaluation_gt28.json"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_builder():
    spec = importlib.util.spec_from_file_location("gt31_builder", BUILDER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gt31_human_review_scopes_conflicting_values_without_deleting_them() -> None:
    scenario = _json(SCENARIO)["scenario"]
    assert scenario["facts"] == {
        "gt30_values_mps": [8, 13, 13],
        "human_selected_wind_speed_mps": 8,
        "mission_wind_limit_mps": 12,
        "weather_suitable": True,
        "retained_response_count": 3,
        "not_applicable_response_count": 2,
        "deleted_response_count": 0,
    }
    assert scenario["adjudication"]["majority_vote_used"] is False
    assert scenario["adjudication"]["conflicting_responses_preserved"] is True
    assert scenario["adjudication"]["provider_self_assured"] is False


def test_gt31_fixed_hashes_match_case_and_bound_gt30_gt28_inputs() -> None:
    expected = _json(SCENARIO)["scenario"]["sha256"]
    paths = {
        "context_evidence": CONTEXT,
        "assurance_profile": PROFILE,
        "human_descriptor": DESCRIPTOR,
        "verification_request": REQUEST,
        "human_response": RESPONSE,
        "assurance_evaluation": EVALUATION,
        "gt30_official_response": CORE / "verification_response_authoritative_weather_gt30.json",
        "gt30_sensor_response": CORE / "verification_response_onsite_sensor_gt30.json",
        "gt30_lidar_response": CORE / "verification_response_mobile_lidar_gt30.json",
        "gt30_profile": CORE / "assurance_profile_weather_three_source_gt30.json",
        "gt30_evaluation": CORE / "assurance_evaluation_weather_three_source_gt30.json",
        "gt28_control": GT28_CONTROL,
    }
    assert {key: _sha(path) for key, path in paths.items()} == expected


def test_gt31_builder_reproduces_fixed_outputs() -> None:
    before = {path.name: path.read_bytes() for path in CORE.glob("*gt31.json")}
    _load_builder().build()
    after = {path.name: path.read_bytes() for path in CORE.glob("*gt31.json")}
    assert after == before


def test_gt31_human_response_binds_exact_request_and_descriptor_bytes() -> None:
    request = load_verification_request(_json(REQUEST))
    descriptor = load_verification_provider_descriptor(_json(DESCRIPTOR))
    response = load_verification_response(_json(RESPONSE))
    validate_verification_response_bindings(
        response,
        request=request,
        request_bytes=REQUEST.read_bytes(),
        descriptor=descriptor,
        descriptor_bytes=DESCRIPTOR.read_bytes(),
    )


def test_gt31_human_response_cannot_self_promote_assurance_or_action() -> None:
    for field in (
        "independently_verified",
        "production_output_released",
        "action_authorized",
        "action_executed",
    ):
        payload = _json(RESPONSE)
        payload["verification_response"][field] = True
        with pytest.raises(VerificationProviderFormatError, match=field):
            load_verification_response(payload)


def test_gt31_tampered_request_binding_fails_closed() -> None:
    request = load_verification_request(_json(REQUEST))
    descriptor = load_verification_provider_descriptor(_json(DESCRIPTOR))
    response = load_verification_response(_json(RESPONSE))
    with pytest.raises(VerificationProviderFormatError, match="exact bytes"):
        validate_verification_response_bindings(
            response,
            request=request,
            request_bytes=REQUEST.read_bytes() + b"\n",
            descriptor=descriptor,
            descriptor_bytes=DESCRIPTOR.read_bytes(),
        )


def test_gt31_context_evidence_retains_both_13_mps_responses() -> None:
    body = _json(CONTEXT)["weather_context_evidence"]
    assert body["reason_code"] == "shared_local_test_interference"
    assert body["selected_ambient_wind_speed_mps"] == 8
    assert body["responses_not_applicable_to_mission_claim"] == [
        "weather-response-onsite-sensor-gt30",
        "weather-response-mobile-lidar-gt30",
    ]
    assert body["responses_deleted"] == []
    assert len(body["responses_retained"]) == 3


def test_gt31_rejects_context_packet_that_silently_deletes_a_response() -> None:
    module = _load_builder()
    payload = _json(CONTEXT)
    payload["weather_context_evidence"]["responses_deleted"] = [
        "weather-response-onsite-sensor-gt30"
    ]
    input_bytes = {
        "gt30_official_response": (CORE / "verification_response_authoritative_weather_gt30.json").read_bytes(),
        "gt30_sensor_response": (CORE / "verification_response_onsite_sensor_gt30.json").read_bytes(),
        "gt30_lidar_response": (CORE / "verification_response_mobile_lidar_gt30.json").read_bytes(),
    }
    with pytest.raises(AssertionError):
        module._validate_context_evidence(payload, input_bytes)


def test_gt31_releases_weather_conclusion_but_takeoff_gate_remains_blocked() -> None:
    scenario = _json(SCENARIO)["scenario"]
    assurance = _json(EVALUATION)["assurance_evaluation"]
    control = load_control_evaluation(_json(GT28_CONTROL))

    assert assurance["state"] == "verified"
    assert assurance["reason"] == "assurance_requirements_satisfied"
    assert assurance["eligible_outputs"] == ["weather_condition_verified"]
    assert assurance["production_output_released"] is False
    assert assurance["action_authorized"] is False
    assert assurance["action_executed"] is False

    assert control.blocked_outputs == (
        "automatic_takeoff_authorization",
        "takeoff_command",
    )
    assert control.action_executed is False
    assert scenario["layered_gate"] == {
        "evidence_adjudication": "completed",
        "weather_conclusion": "eligible",
        "takeoff_authorization": "blocked",
        "takeoff_command": "blocked",
        "missing_authorizations": [
            "airspace_authorized",
            "departure_site_authorized",
            "mission_authorized",
            "operator_authorized",
            "weather_release_authorized",
        ],
    }
    assert scenario["required_action"] == "request_remaining_takeoff_authorizations"
    assert scenario["boundaries"]["automatic_takeoff_authorization_eligible"] is False
