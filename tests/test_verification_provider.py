"""Verification Provider Profile v0.1 and GT29 contract tests."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from geotask_core.v1.artifact_registry import get_artifact_descriptor
from geotask_core.v1.artifact_validation import validate_artifact_payload
from geotask_core.v1.verification_provider import (
    ASSURANCE_PROFILE_ARTIFACT_ID,
    VERIFICATION_PROVIDER_DESCRIPTOR_ARTIFACT_ID,
    VERIFICATION_REQUEST_ARTIFACT_ID,
    VERIFICATION_RESPONSE_ARTIFACT_ID,
    VerificationProviderFormatError,
    evaluate_verification_assurance,
    load_assurance_profile,
    load_verification_provider_descriptor,
    load_verification_request,
    load_verification_response,
    validate_verification_request_contract,
    validate_verification_response_bindings,
    verification_provider_profile_payload,
)


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "examples" / "core"
DESCRIPTOR_OFFICIAL = CORE / "verification_provider_descriptor_authoritative_weather_gt29.json"
DESCRIPTOR_SENSOR = CORE / "verification_provider_descriptor_onsite_sensor_gt29.json"
REQUEST = CORE / "verification_request_weather_conflict_gt29.json"
RESPONSE_OFFICIAL = CORE / "verification_response_authoritative_weather_gt29.json"
RESPONSE_SENSOR = CORE / "verification_response_onsite_sensor_gt29.json"
PROFILE = CORE / "assurance_profile_weather_conflict_gt29.json"
EVALUATION = CORE / "assurance_evaluation_weather_conflict_gt29.json"
SCENARIO = CORE / "gt29_weather_provider_conflict.json"
SCHEMAS = (
    ROOT / "schemas" / "geotask-verification-provider-descriptor-v0.1.schema.json",
    ROOT / "schemas" / "geotask-verification-request-v0.1.schema.json",
    ROOT / "schemas" / "geotask-verification-response-v0.1.schema.json",
    ROOT / "schemas" / "geotask-assurance-profile-v0.1.schema.json",
)


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "geotask_core.cli", *args],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def _loaded_bundle():
    official_descriptor = load_verification_provider_descriptor(_json(DESCRIPTOR_OFFICIAL))
    sensor_descriptor = load_verification_provider_descriptor(_json(DESCRIPTOR_SENSOR))
    request = load_verification_request(_json(REQUEST))
    official_response = load_verification_response(_json(RESPONSE_OFFICIAL))
    sensor_response = load_verification_response(_json(RESPONSE_SENSOR))
    profile = load_assurance_profile(_json(PROFILE))
    return (
        official_descriptor,
        sensor_descriptor,
        request,
        official_response,
        sensor_response,
        profile,
    )


def test_provider_profile_registry_and_schemas_are_public_and_read_only() -> None:
    profile = verification_provider_profile_payload()["verification_provider_profile"]
    assert profile["profile_version"] == "0.1"
    assert profile["provider_self_assurance_allowed"] is False
    assert profile["external_side_effects_allowed"] is False
    assert profile["production_output_release_supported"] is False
    assert profile["action_authorization_supported"] is False
    assert profile["action_execution_supported"] is False
    assert set(profile["artifacts"]) == {
        VERIFICATION_PROVIDER_DESCRIPTOR_ARTIFACT_ID,
        VERIFICATION_REQUEST_ARTIFACT_ID,
        VERIFICATION_RESPONSE_ARTIFACT_ID,
        ASSURANCE_PROFILE_ARTIFACT_ID,
    }

    for artifact_id in profile["artifacts"]:
        descriptor = get_artifact_descriptor(artifact_id)
        assert descriptor.schema_version == "0.1"
        assert "does not" in descriptor.execution_boundary.lower()

    for path in SCHEMAS:
        schema = _json(path)
        Draft202012Validator.check_schema(schema)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_gt29_fixed_artifacts_validate_and_bind_exact_bytes() -> None:
    (
        official_descriptor,
        sensor_descriptor,
        request,
        official_response,
        sensor_response,
        profile,
    ) = _loaded_bundle()

    assert validate_verification_request_contract(official_descriptor, request)[
        "verification_provider_contract"
    ]["valid"] is True
    assert validate_verification_request_contract(sensor_descriptor, request)[
        "verification_provider_contract"
    ]["valid"] is True

    validate_verification_response_bindings(
        official_response,
        request=request,
        request_bytes=REQUEST.read_bytes(),
        descriptor=official_descriptor,
        descriptor_bytes=DESCRIPTOR_OFFICIAL.read_bytes(),
    )
    validate_verification_response_bindings(
        sensor_response,
        request=request,
        request_bytes=REQUEST.read_bytes(),
        descriptor=sensor_descriptor,
        descriptor_bytes=DESCRIPTOR_SENSOR.read_bytes(),
    )

    artifact_payloads = {
        VERIFICATION_PROVIDER_DESCRIPTOR_ARTIFACT_ID: _json(DESCRIPTOR_OFFICIAL),
        VERIFICATION_REQUEST_ARTIFACT_ID: _json(REQUEST),
        VERIFICATION_RESPONSE_ARTIFACT_ID: _json(RESPONSE_OFFICIAL),
        ASSURANCE_PROFILE_ARTIFACT_ID: _json(PROFILE),
    }
    for artifact_id, payload in artifact_payloads.items():
        report = validate_artifact_payload(artifact_id, payload)
        assert report.valid is True
        assert report.schema_verified is True

    assert profile.minimum_provider_count == 2
    assert profile.minimum_independent_groups == 2


def test_gt29_conflict_remains_unknown_without_precedence_or_average() -> None:
    (
        official_descriptor,
        sensor_descriptor,
        request,
        official_response,
        sensor_response,
        profile,
    ) = _loaded_bundle()
    result = evaluate_verification_assurance(
        profile,
        request=request,
        bound_results=[
            (official_descriptor, official_response),
            (sensor_descriptor, sensor_response),
        ],
        evaluated_at="2026-08-04T14:05:30+08:00",
    )["assurance_evaluation"]
    fixed = _json(EVALUATION)["assurance_evaluation"]
    assert result == fixed
    assert result["state"] == "unknown"
    assert result["reason"] == "independent_provider_conflict"
    assert result["usable_provider_count"] == 2
    assert result["independent_group_count"] == 2
    assert result["eligible_outputs"] == []
    assert result["blocked_outputs"] == [
        "weather_condition_verified",
        "automatic_takeoff_authorization",
    ]
    assert result["blocked_actions"] == ["takeoff_command"]
    assert result["next_action"] == "request_third_independent_weather_verification"
    assert result["independent_verification_completed"] is False
    assert result["production_output_released"] is False
    assert result["action_authorized"] is False
    assert result["action_executed"] is False

    scenario = _json(SCENARIO)["scenario"]
    assert scenario["facts"]["authoritative_weather_wind_speed_mps"] == 8
    assert scenario["facts"]["onsite_sensor_wind_speed_mps"] == 13
    assert scenario["facts"]["mission_wind_limit_mps"] == 12
    assert scenario["boundaries"]["provider_precedence_inferred"] is False
    assert scenario["boundaries"]["values_averaged"] is False


def test_provider_response_cannot_self_promote_assurance_or_action() -> None:
    for field in (
        "independently_verified",
        "production_output_released",
        "action_authorized",
        "action_executed",
    ):
        payload = _json(RESPONSE_SENSOR)
        payload["verification_response"][field] = True
        with pytest.raises(VerificationProviderFormatError, match=field):
            load_verification_response(payload)


def test_provider_response_cannot_change_descriptor_assurance_declarations() -> None:
    official_descriptor, _, request, official_response, _, _ = _loaded_bundle()
    response_payload = official_response.to_dict()
    response_payload["verification_response"]["assurance_declarations"][
        "independence_group"
    ] = "invented-independent-group"
    response = load_verification_response(response_payload)
    with pytest.raises(VerificationProviderFormatError, match="independence_group"):
        validate_verification_response_bindings(
            response,
            request=request,
            request_bytes=REQUEST.read_bytes(),
            descriptor=official_descriptor,
            descriptor_bytes=DESCRIPTOR_OFFICIAL.read_bytes(),
        )


def test_tampered_request_or_descriptor_bytes_fail_exact_binding() -> None:
    official_descriptor, _, request, official_response, _, _ = _loaded_bundle()
    with pytest.raises(VerificationProviderFormatError, match="request SHA-256"):
        validate_verification_response_bindings(
            official_response,
            request=request,
            request_bytes=REQUEST.read_bytes() + b" ",
            descriptor=official_descriptor,
            descriptor_bytes=DESCRIPTOR_OFFICIAL.read_bytes(),
        )
    with pytest.raises(VerificationProviderFormatError, match="provider SHA-256"):
        validate_verification_response_bindings(
            official_response,
            request=request,
            request_bytes=REQUEST.read_bytes(),
            descriptor=official_descriptor,
            descriptor_bytes=DESCRIPTOR_OFFICIAL.read_bytes() + b" ",
        )


def test_same_independence_group_and_stale_response_fail_assurance() -> None:
    (
        official_descriptor,
        sensor_descriptor,
        request,
        official_response,
        sensor_response,
        profile,
    ) = _loaded_bundle()

    duplicate_group_payload = sensor_descriptor.to_dict()
    duplicate_group_payload["verification_provider_descriptor"]["independence_group"] = (
        official_descriptor.independence_group
    )
    duplicate_group = load_verification_provider_descriptor(duplicate_group_payload)
    duplicate_response_payload = sensor_response.to_dict()
    duplicate_response_payload["verification_response"]["assurance_declarations"][
        "independence_group"
    ] = official_descriptor.independence_group
    duplicate_response = load_verification_response(duplicate_response_payload)
    result = evaluate_verification_assurance(
        profile,
        request=request,
        bound_results=[
            (official_descriptor, official_response),
            (duplicate_group, duplicate_response),
        ],
        evaluated_at="2026-08-04T14:05:30+08:00",
    )["assurance_evaluation"]
    assert result["state"] == "unknown"
    assert any(
        item["code"] == "insufficient_independent_groups"
        for item in result["diagnostics"]
    )

    stale_response_payload = sensor_response.to_dict()
    stale_response_payload["verification_response"]["result"]["observed_at"] = (
        "2026-08-04T13:00:00+08:00"
    )
    stale_response_payload["verification_response"]["result"]["valid_until"] = (
        "2026-08-04T13:10:00+08:00"
    )
    stale_response = load_verification_response(stale_response_payload)
    stale_result = evaluate_verification_assurance(
        profile,
        request=request,
        bound_results=[
            (official_descriptor, official_response),
            (sensor_descriptor, stale_response),
        ],
        evaluated_at="2026-08-04T14:05:30+08:00",
    )["assurance_evaluation"]
    assert stale_result["state"] == "unknown"
    assert any(item["code"] == "stale_response" for item in stale_result["diagnostics"])


def test_matching_responses_can_make_output_eligible_but_never_execute_action() -> None:
    (
        official_descriptor,
        sensor_descriptor,
        request,
        official_response,
        sensor_response,
        profile,
    ) = _loaded_bundle()
    matching_payload = sensor_response.to_dict()
    matching_payload["verification_response"]["result"]["value"] = 8
    matching_response = load_verification_response(matching_payload)
    result = evaluate_verification_assurance(
        profile,
        request=request,
        bound_results=[
            (official_descriptor, official_response),
            (sensor_descriptor, matching_response),
        ],
        evaluated_at="2026-08-04T14:05:30+08:00",
    )["assurance_evaluation"]
    assert result["state"] == "verified"
    assert result["eligible_outputs"] == ["weather_assurance_record"]
    assert result["blocked_outputs"] == []
    assert result["blocked_actions"] == ["takeoff_command"]
    assert result["production_output_released"] is False
    assert result["action_authorized"] is False
    assert result["action_executed"] is False


def test_local_predictive_model_cannot_bypass_independence_requirements() -> None:
    _, sensor_descriptor, request, _, sensor_response, profile = _loaded_bundle()
    model_payload = sensor_descriptor.to_dict()
    model_body = model_payload["verification_provider_descriptor"]
    model_body["provider_id"] = "geotask.provider.mock-local-weather-model"
    model_body["provider_type"] = "local_predictive_model"
    model_body["independence_group"] = "fictional-model-derived-from-onsite-sensor"
    model_body["reproducibility"] = "non_deterministic"
    model_body["calibration_status"] = "uncalibrated"
    model_descriptor = load_verification_provider_descriptor(model_payload)

    response_payload = sensor_response.to_dict()
    body = response_payload["verification_response"]
    body["response_id"] = "weather-response-local-model-gt29"
    body["provider_ref"]["provider_id"] = model_descriptor.provider_id
    body["assurance_declarations"]["independence_group"] = model_descriptor.independence_group
    body["assurance_declarations"]["reproducibility"] = model_descriptor.reproducibility
    body["assurance_declarations"]["calibration_status"] = model_descriptor.calibration_status
    model_response = load_verification_response(response_payload)

    permissive_request_payload = request.to_dict()
    permissive_request_payload["verification_request"]["allowed_provider_types"].append(
        "local_predictive_model"
    )
    permissive_request = load_verification_request(permissive_request_payload)
    result = evaluate_verification_assurance(
        profile,
        request=permissive_request,
        bound_results=[(model_descriptor, model_response)],
        evaluated_at="2026-08-04T14:05:30+08:00",
    )["assurance_evaluation"]
    assert result["state"] == "unknown"
    assert result["independent_verification_completed"] is False
    assert result["action_executed"] is False


def test_provider_cli_is_read_only_and_validates_exact_bindings() -> None:
    inspect = _run_cli("provider", "inspect", "--profile", "--format", "json")
    assert inspect.returncode == 0, inspect.stderr
    inspect_payload = json.loads(inspect.stdout)
    assert inspect_payload["verification_provider_profile"][
        "provider_self_assurance_allowed"
    ] is False

    check = _run_cli(
        "provider",
        "check",
        str(DESCRIPTOR_OFFICIAL.relative_to(ROOT)),
        str(REQUEST.relative_to(ROOT)),
        "--format",
        "json",
    )
    assert check.returncode == 0, check.stderr
    check_payload = json.loads(check.stdout)["verification_provider_contract"]
    assert check_payload["valid"] is True
    assert check_payload["request_submitted"] is False
    assert check_payload["action_executed"] is False

    validate = _run_cli(
        "provider",
        "validate",
        str(RESPONSE_OFFICIAL.relative_to(ROOT)),
        "--request",
        str(REQUEST.relative_to(ROOT)),
        "--descriptor",
        str(DESCRIPTOR_OFFICIAL.relative_to(ROOT)),
        "--format",
        "json",
    )
    assert validate.returncode == 0, validate.stderr
    validate_payload = json.loads(validate.stdout)["verification_response_validation"]
    assert validate_payload["exact_request_binding_verified"] is True
    assert validate_payload["exact_descriptor_binding_verified"] is True
    assert validate_payload["provider_self_assurance_used"] is False
    assert validate_payload["production_output_released"] is False
    assert validate_payload["action_executed"] is False
