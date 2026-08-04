"""Build the fixed GT29 Verification Provider conflict bundle.

All data are fictional. The builder performs no network call, external evidence
resolution, production output release, action authorization, or flight action.
"""

from __future__ import annotations

import json
from pathlib import Path

from geotask_core.v1.observation import load_observation
from geotask_core.v1.verification_provider import (
    evaluate_verification_assurance,
    load_assurance_profile,
    load_verification_provider_descriptor,
    load_verification_request,
    load_verification_response,
    sha256_bytes,
    validate_verification_request_contract,
    validate_verification_response_bindings,
)


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "examples" / "core"

FILES = {
    "official_observation": CORE / "observation_weather_authoritative_gt29.json",
    "sensor_observation": CORE / "observation_weather_onsite_sensor_gt29.json",
    "profile": CORE / "assurance_profile_weather_conflict_gt29.json",
    "official_descriptor": CORE / "verification_provider_descriptor_authoritative_weather_gt29.json",
    "sensor_descriptor": CORE / "verification_provider_descriptor_onsite_sensor_gt29.json",
    "request": CORE / "verification_request_weather_conflict_gt29.json",
    "official_response": CORE / "verification_response_authoritative_weather_gt29.json",
    "sensor_response": CORE / "verification_response_onsite_sensor_gt29.json",
    "evaluation": CORE / "assurance_evaluation_weather_conflict_gt29.json",
    "scenario": CORE / "gt29_weather_provider_conflict.json",
}


def _write(path: Path, payload: dict) -> bytes:
    raw = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.write_bytes(raw)
    return raw


def _observation(*, observation_id: str, source_kind: str, producer_id: str, value: int, observed_at: str, valid_until: str, suffix: str) -> dict:
    return {
        "observation": {
            "schema_id": "https://stpku.github.io/GeoTask/schemas/geotask-observation-v0.1.schema.json",
            "schema_version": "0.1",
            "observation_id": observation_id,
            "observed_at": observed_at,
            "received_at": observed_at,
            "source": {
                "kind": source_kind,
                "reference": f"weather:fictional/east/{suffix}",
                "sha256": suffix * 64,
            },
            "producer": {
                "id": producer_id,
                "kind": "sensor" if source_kind == "sensor" else "organization",
                "version": "0.1.0",
            },
            "claims": [
                {
                    "id": f"east-current-wind-speed-{suffix}",
                    "subject_ref": "weather-cell-east-gt29",
                    "predicate": "wind_speed_mps",
                    "basis": "direct_observation",
                    "value": value,
                    "uncertainty": {
                        "kind": "standard_deviation",
                        "value": 0.5,
                        "unit": "meter_per_second",
                    },
                    "valid_until": valid_until,
                    "evidence_refs": [f"weather:fictional/east/{suffix}"],
                }
            ],
        }
    }


def build() -> dict[str, dict]:
    official_observation = _observation(
        observation_id="obs-weather-authoritative-gt29",
        source_kind="authoritative_data",
        producer_id="fictional-authoritative-weather-service",
        value=8,
        observed_at="2026-08-04T14:00:00+08:00",
        valid_until="2026-08-04T14:15:00+08:00",
        suffix="a",
    )
    sensor_observation = _observation(
        observation_id="obs-weather-onsite-sensor-gt29",
        source_kind="sensor",
        producer_id="fictional-onsite-wind-sensor",
        value=13,
        observed_at="2026-08-04T14:04:00+08:00",
        valid_until="2026-08-04T14:09:00+08:00",
        suffix="b",
    )
    load_observation(official_observation)
    load_observation(sensor_observation)
    official_observation_bytes = _write(FILES["official_observation"], official_observation)
    sensor_observation_bytes = _write(FILES["sensor_observation"], sensor_observation)

    profile_payload = {
        "assurance_profile": {
            "profile_version": "0.1",
            "profile_id": "gt29-independent-weather-assurance",
            "title": "GT29 independent current-wind assurance",
            "minimum_provider_count": 2,
            "minimum_independent_groups": 2,
            "allowed_provider_types": [
                "authoritative_data_provider",
                "sensor_data_provider",
            ],
            "require_fresh_results": True,
            "max_result_age_seconds": 600,
            "require_reproducible": True,
            "accepted_reproducibility": ["deterministic", "repeatable"],
            "require_calibration": True,
            "accepted_calibration_states": ["not_applicable", "calibrated"],
            "conflict_policy": "unknown",
            "eligible_output": "weather_assurance_record",
            "blocked_outputs": [
                "weather_condition_verified",
                "automatic_takeoff_authorization",
            ],
            "blocked_actions": ["takeoff_command"],
            "next_action_on_insufficient_assurance": "request_third_independent_weather_verification",
            "action_authorized": False,
            "action_executed": False,
        }
    }
    profile = load_assurance_profile(profile_payload)
    profile_bytes = _write(FILES["profile"], profile.to_dict())

    official_descriptor_payload = {
        "verification_provider_descriptor": {
            "interface_version": "0.1",
            "provider_id": "geotask.provider.mock-authoritative-weather",
            "provider_version": "0.1.0",
            "title": "Mock Authoritative Weather Provider",
            "provider_type": "authoritative_data_provider",
            "implementation_kind": "mock",
            "production_ready": False,
            "capabilities": ["weather.current_wind_speed"],
            "supported_methods": ["measure_current_wind_speed"],
            "independence_group": "fictional-weather-service-network",
            "reproducibility": "deterministic",
            "calibration_status": "not_applicable",
            "valid_until": "2026-08-05T00:00:00+08:00",
            "audit_supported": True,
            "credentials_managed_externally": True,
            "external_side_effects_allowed": False,
        }
    }
    sensor_descriptor_payload = {
        "verification_provider_descriptor": {
            "interface_version": "0.1",
            "provider_id": "geotask.provider.mock-onsite-wind-sensor",
            "provider_version": "0.1.0",
            "title": "Mock Onsite Wind Sensor Provider",
            "provider_type": "sensor_data_provider",
            "implementation_kind": "mock",
            "production_ready": False,
            "capabilities": ["weather.current_wind_speed"],
            "supported_methods": ["measure_current_wind_speed"],
            "independence_group": "fictional-onsite-sensor-network",
            "reproducibility": "repeatable",
            "calibration_status": "calibrated",
            "valid_until": "2026-08-05T00:00:00+08:00",
            "audit_supported": True,
            "credentials_managed_externally": True,
            "external_side_effects_allowed": False,
        }
    }
    official_descriptor = load_verification_provider_descriptor(official_descriptor_payload)
    sensor_descriptor = load_verification_provider_descriptor(sensor_descriptor_payload)
    official_descriptor_bytes = _write(FILES["official_descriptor"], official_descriptor.to_dict())
    sensor_descriptor_bytes = _write(FILES["sensor_descriptor"], sensor_descriptor.to_dict())

    request_payload = {
        "verification_request": {
            "request_version": "0.1",
            "request_id": "verify-east-current-wind-speed-gt29",
            "created_at": "2026-08-04T14:05:00+08:00",
            "subject": {
                "claim_id": "east-current-wind-speed",
                "claim_type": "weather.wind_speed",
                "value": None,
                "unit": "meter_per_second",
                "observed_at": "2026-08-04T14:05:00+08:00",
                "valid_until": "2026-08-04T14:10:00+08:00",
            },
            "input_artifacts": [
                {
                    "ref_id": "official-weather-observation",
                    "artifact_id": "geotask.observation",
                    "sha256": sha256_bytes(official_observation_bytes),
                },
                {
                    "ref_id": "onsite-sensor-observation",
                    "artifact_id": "geotask.observation",
                    "sha256": sha256_bytes(sensor_observation_bytes),
                },
            ],
            "verification_method": "measure_current_wind_speed",
            "required_capabilities": ["weather.current_wind_speed"],
            "allowed_provider_types": [
                "authoritative_data_provider",
                "sensor_data_provider",
            ],
            "assurance_profile_ref": {
                "profile_id": profile.profile_id,
                "sha256": sha256_bytes(profile_bytes),
            },
            "deadline": "2026-08-04T14:08:00+08:00",
            "external_side_effects_allowed": False,
            "action_authorized": False,
        }
    }
    request = load_verification_request(request_payload)
    request_bytes = _write(FILES["request"], request.to_dict())
    assert validate_verification_request_contract(official_descriptor, request)[
        "verification_provider_contract"
    ]["valid"]
    assert validate_verification_request_contract(sensor_descriptor, request)[
        "verification_provider_contract"
    ]["valid"]

    def response_payload(*, response_id: str, descriptor, descriptor_bytes: bytes, value: int, observed_at: str, valid_until: str, evidence_ref: str) -> dict:
        return {
            "verification_response": {
                "response_version": "0.1",
                "response_id": response_id,
                "request_ref": {
                    "request_id": request.request_id,
                    "sha256": sha256_bytes(request_bytes),
                },
                "provider_ref": {
                    "provider_id": descriptor.provider_id,
                    "provider_version": descriptor.provider_version,
                    "sha256": sha256_bytes(descriptor_bytes),
                },
                "state": "verified",
                "result": {
                    "claim_id": request.subject.claim_id,
                    "claim_type": request.subject.claim_type,
                    "value": value,
                    "unit": "meter_per_second",
                    "observed_at": observed_at,
                    "valid_until": valid_until,
                },
                "verification_method": request.verification_method,
                "evidence_refs": [evidence_ref],
                "assurance_declarations": {
                    "independence_group": descriptor.independence_group,
                    "reproducibility": descriptor.reproducibility,
                    "calibration_status": descriptor.calibration_status,
                    "confidence": None,
                },
                "diagnostics": [],
                "completed_at": "2026-08-04T14:05:10+08:00",
                "independently_verified": False,
                "production_output_released": False,
                "action_authorized": False,
                "action_executed": False,
            }
        }

    official_response_payload = response_payload(
        response_id="weather-response-authoritative-gt29",
        descriptor=official_descriptor,
        descriptor_bytes=official_descriptor_bytes,
        value=8,
        observed_at="2026-08-04T14:00:00+08:00",
        valid_until="2026-08-04T14:15:00+08:00",
        evidence_ref="weather:fictional/east/a",
    )
    sensor_response_payload = response_payload(
        response_id="weather-response-onsite-sensor-gt29",
        descriptor=sensor_descriptor,
        descriptor_bytes=sensor_descriptor_bytes,
        value=13,
        observed_at="2026-08-04T14:04:00+08:00",
        valid_until="2026-08-04T14:09:00+08:00",
        evidence_ref="weather:fictional/east/b",
    )
    official_response = load_verification_response(official_response_payload)
    sensor_response = load_verification_response(sensor_response_payload)
    validate_verification_response_bindings(
        official_response,
        request=request,
        request_bytes=request_bytes,
        descriptor=official_descriptor,
        descriptor_bytes=official_descriptor_bytes,
    )
    validate_verification_response_bindings(
        sensor_response,
        request=request,
        request_bytes=request_bytes,
        descriptor=sensor_descriptor,
        descriptor_bytes=sensor_descriptor_bytes,
    )
    official_response_bytes = _write(FILES["official_response"], official_response.to_dict())
    sensor_response_bytes = _write(FILES["sensor_response"], sensor_response.to_dict())

    evaluation = evaluate_verification_assurance(
        profile,
        request=request,
        bound_results=[
            (official_descriptor, official_response),
            (sensor_descriptor, sensor_response),
        ],
        evaluated_at="2026-08-04T14:05:30+08:00",
    )
    evaluation_bytes = _write(FILES["evaluation"], evaluation)
    body = evaluation["assurance_evaluation"]
    assert body["state"] == "unknown"
    assert body["reason"] == "independent_provider_conflict"
    assert body["independent_group_count"] == 2
    assert body["blocked_outputs"] == [
        "weather_condition_verified",
        "automatic_takeoff_authorization",
    ]
    assert body["blocked_actions"] == ["takeoff_command"]
    assert body["action_executed"] is False

    scenario = {
        "scenario": {
            "id": "gt29-weather-provider-conflict",
            "title_zh": "气象服务数据和现场传感器冲突时，AI应该相信谁？",
            "title_en": "When weather-service data conflicts with an onsite sensor, what should the AI trust?",
            "facts": {
                "authoritative_weather_wind_speed_mps": 8,
                "onsite_sensor_wind_speed_mps": 13,
                "mission_wind_limit_mps": 12,
                "provider_count": 2,
                "independent_group_count": 2,
            },
            "incorrect_actions": [
                "prefer_authoritative_label",
                "prefer_newer_timestamp",
                "average_values",
                "authorize_takeoff_from_one_source",
            ],
            "required_action": "request_third_independent_weather_verification",
            "result": body,
            "sha256": {
                "official_observation": sha256_bytes(official_observation_bytes),
                "sensor_observation": sha256_bytes(sensor_observation_bytes),
                "assurance_profile": sha256_bytes(profile_bytes),
                "official_descriptor": sha256_bytes(official_descriptor_bytes),
                "sensor_descriptor": sha256_bytes(sensor_descriptor_bytes),
                "verification_request": sha256_bytes(request_bytes),
                "official_response": sha256_bytes(official_response_bytes),
                "sensor_response": sha256_bytes(sensor_response_bytes),
                "assurance_evaluation": sha256_bytes(evaluation_bytes),
            },
            "boundaries": {
                "external_truth_verified": False,
                "provider_precedence_inferred": False,
                "values_averaged": False,
                "production_output_released": False,
                "action_authorized": False,
                "action_executed": False,
            },
        }
    }
    _write(FILES["scenario"], scenario)
    return {
        "profile": profile.to_dict(),
        "official_descriptor": official_descriptor.to_dict(),
        "sensor_descriptor": sensor_descriptor.to_dict(),
        "request": request.to_dict(),
        "official_response": official_response.to_dict(),
        "sensor_response": sensor_response.to_dict(),
        "evaluation": evaluation,
        "scenario": scenario,
    }


if __name__ == "__main__":
    build()
    print("GT29 weather Provider conflict bundle generated")
