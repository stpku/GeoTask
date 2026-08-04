"""Build the fixed GT30 three-source weather conflict bundle.

All data are fictional. The builder reuses the two GT29 provider inputs, adds one
independent mobile lidar source, and proves that a two-to-one value split does
not silently become majority voting under Assurance Profile v0.1.
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
    "lidar_observation": CORE / "observation_weather_mobile_lidar_gt30.json",
    "profile": CORE / "assurance_profile_weather_three_source_gt30.json",
    "official_descriptor": CORE / "verification_provider_descriptor_authoritative_weather_gt29.json",
    "sensor_descriptor": CORE / "verification_provider_descriptor_onsite_sensor_gt29.json",
    "lidar_descriptor": CORE / "verification_provider_descriptor_mobile_lidar_gt30.json",
    "request": CORE / "verification_request_weather_three_source_gt30.json",
    "official_response": CORE / "verification_response_authoritative_weather_gt30.json",
    "sensor_response": CORE / "verification_response_onsite_sensor_gt30.json",
    "lidar_response": CORE / "verification_response_mobile_lidar_gt30.json",
    "evaluation": CORE / "assurance_evaluation_weather_three_source_gt30.json",
    "scenario": CORE / "gt30_three_source_weather_conflict.json",
}


def _json_bytes(path: Path) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    return json.loads(raw), raw


def _write(path: Path, payload: dict) -> bytes:
    raw = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.write_bytes(raw)
    return raw


def build() -> dict[str, dict]:
    official_observation_payload, official_observation_bytes = _json_bytes(
        FILES["official_observation"]
    )
    sensor_observation_payload, sensor_observation_bytes = _json_bytes(
        FILES["sensor_observation"]
    )
    load_observation(official_observation_payload)
    load_observation(sensor_observation_payload)

    lidar_observation_payload = {
        "observation": {
            "schema_id": "https://stpku.github.io/GeoTask/schemas/geotask-observation-v0.1.schema.json",
            "schema_version": "0.1",
            "observation_id": "obs-weather-mobile-lidar-gt30",
            "observed_at": "2026-08-04T14:06:00+08:00",
            "received_at": "2026-08-04T14:06:00+08:00",
            "source": {
                "kind": "sensor",
                "reference": "weather:fictional/east/mobile-lidar-c",
                "sha256": "c" * 64,
            },
            "producer": {
                "id": "fictional-mobile-lidar-unit",
                "kind": "sensor",
                "version": "0.1.0",
            },
            "claims": [
                {
                    "id": "east-current-wind-speed-mobile-lidar",
                    "subject_ref": "weather-cell-east-gt30",
                    "predicate": "wind_speed_mps",
                    "basis": "direct_observation",
                    "value": 13,
                    "uncertainty": {
                        "kind": "standard_deviation",
                        "value": 0.4,
                        "unit": "meter_per_second",
                    },
                    "valid_until": "2026-08-04T14:11:00+08:00",
                    "evidence_refs": ["weather:fictional/east/mobile-lidar-c"],
                }
            ],
        }
    }
    load_observation(lidar_observation_payload)
    lidar_observation_bytes = _write(FILES["lidar_observation"], lidar_observation_payload)

    profile_payload = {
        "assurance_profile": {
            "profile_version": "0.1",
            "profile_id": "gt30-three-source-exact-consensus",
            "title": "GT30 three-source exact-consensus weather assurance",
            "minimum_provider_count": 3,
            "minimum_independent_groups": 3,
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
            "next_action_on_insufficient_assurance": "request_explicit_weather_adjudication",
            "action_authorized": False,
            "action_executed": False,
        }
    }
    profile = load_assurance_profile(profile_payload)
    profile_bytes = _write(FILES["profile"], profile.to_dict())

    official_descriptor_payload, official_descriptor_bytes = _json_bytes(
        FILES["official_descriptor"]
    )
    sensor_descriptor_payload, sensor_descriptor_bytes = _json_bytes(
        FILES["sensor_descriptor"]
    )
    official_descriptor = load_verification_provider_descriptor(official_descriptor_payload)
    sensor_descriptor = load_verification_provider_descriptor(sensor_descriptor_payload)

    lidar_descriptor_payload = {
        "verification_provider_descriptor": {
            "interface_version": "0.1",
            "provider_id": "geotask.provider.mock-mobile-wind-lidar",
            "provider_version": "0.1.0",
            "title": "Mock Mobile Wind Lidar Provider",
            "provider_type": "sensor_data_provider",
            "implementation_kind": "mock",
            "production_ready": False,
            "capabilities": ["weather.current_wind_speed"],
            "supported_methods": ["measure_current_wind_speed"],
            "independence_group": "fictional-mobile-lidar-network",
            "reproducibility": "repeatable",
            "calibration_status": "calibrated",
            "valid_until": "2026-08-05T00:00:00+08:00",
            "audit_supported": True,
            "credentials_managed_externally": True,
            "external_side_effects_allowed": False,
        }
    }
    lidar_descriptor = load_verification_provider_descriptor(lidar_descriptor_payload)
    lidar_descriptor_bytes = _write(FILES["lidar_descriptor"], lidar_descriptor.to_dict())

    request_payload = {
        "verification_request": {
            "request_version": "0.1",
            "request_id": "verify-east-current-wind-speed-three-source-gt30",
            "created_at": "2026-08-04T14:06:10+08:00",
            "subject": {
                "claim_id": "east-current-wind-speed",
                "claim_type": "weather.wind_speed",
                "value": None,
                "unit": "meter_per_second",
                "observed_at": "2026-08-04T14:06:00+08:00",
                "valid_until": "2026-08-04T14:11:00+08:00",
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
                {
                    "ref_id": "mobile-lidar-observation",
                    "artifact_id": "geotask.observation",
                    "sha256": sha256_bytes(lidar_observation_bytes),
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
            "deadline": "2026-08-04T14:09:00+08:00",
            "external_side_effects_allowed": False,
            "action_authorized": False,
        }
    }
    request = load_verification_request(request_payload)
    request_bytes = _write(FILES["request"], request.to_dict())

    descriptors = [
        ("official", official_descriptor, official_descriptor_bytes),
        ("sensor", sensor_descriptor, sensor_descriptor_bytes),
        ("lidar", lidar_descriptor, lidar_descriptor_bytes),
    ]
    for _, descriptor, _ in descriptors:
        contract = validate_verification_request_contract(descriptor, request)
        assert contract["verification_provider_contract"]["valid"] is True

    def response_payload(
        *,
        response_id: str,
        descriptor,
        descriptor_bytes: bytes,
        value: int,
        observed_at: str,
        valid_until: str,
        evidence_ref: str,
        completed_at: str,
    ) -> dict:
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
                "completed_at": completed_at,
                "independently_verified": False,
                "production_output_released": False,
                "action_authorized": False,
                "action_executed": False,
            }
        }

    response_specs = [
        (
            "official_response",
            "weather-response-authoritative-gt30",
            official_descriptor,
            official_descriptor_bytes,
            8,
            "2026-08-04T14:00:00+08:00",
            "2026-08-04T14:15:00+08:00",
            "weather:fictional/east/a",
            "2026-08-04T14:06:20+08:00",
        ),
        (
            "sensor_response",
            "weather-response-onsite-sensor-gt30",
            sensor_descriptor,
            sensor_descriptor_bytes,
            13,
            "2026-08-04T14:04:00+08:00",
            "2026-08-04T14:09:00+08:00",
            "weather:fictional/east/b",
            "2026-08-04T14:06:21+08:00",
        ),
        (
            "lidar_response",
            "weather-response-mobile-lidar-gt30",
            lidar_descriptor,
            lidar_descriptor_bytes,
            13,
            "2026-08-04T14:06:00+08:00",
            "2026-08-04T14:11:00+08:00",
            "weather:fictional/east/mobile-lidar-c",
            "2026-08-04T14:06:22+08:00",
        ),
    ]
    responses = []
    response_bytes: dict[str, bytes] = {}
    for (
        key,
        response_id,
        descriptor,
        descriptor_bytes,
        value,
        observed_at,
        valid_until,
        evidence_ref,
        completed_at,
    ) in response_specs:
        response = load_verification_response(
            response_payload(
                response_id=response_id,
                descriptor=descriptor,
                descriptor_bytes=descriptor_bytes,
                value=value,
                observed_at=observed_at,
                valid_until=valid_until,
                evidence_ref=evidence_ref,
                completed_at=completed_at,
            )
        )
        validate_verification_response_bindings(
            response,
            request=request,
            request_bytes=request_bytes,
            descriptor=descriptor,
            descriptor_bytes=descriptor_bytes,
        )
        response_bytes[key] = _write(FILES[key], response.to_dict())
        responses.append((descriptor, response))

    evaluation = evaluate_verification_assurance(
        profile,
        request=request,
        bound_results=responses,
        evaluated_at="2026-08-04T14:06:30+08:00",
    )
    evaluation_bytes = _write(FILES["evaluation"], evaluation)
    body = evaluation["assurance_evaluation"]
    assert body["state"] == "unknown"
    assert body["reason"] == "independent_provider_conflict"
    assert body["provider_count"] == 3
    assert body["usable_provider_count"] == 3
    assert body["independent_group_count"] == 3
    assert body["next_action"] == "request_explicit_weather_adjudication"
    assert body["action_executed"] is False

    scenario = {
        "scenario": {
            "id": "gt30-three-source-weather-conflict",
            "title_zh": "第三个独立气象来源加入后，冲突就自动解决了吗？",
            "title_en": "Does a third independent weather source automatically resolve the conflict?",
            "facts": {
                "authoritative_weather_wind_speed_mps": 8,
                "onsite_sensor_wind_speed_mps": 13,
                "mobile_lidar_wind_speed_mps": 13,
                "mission_wind_limit_mps": 12,
                "provider_count": 3,
                "usable_provider_count": 3,
                "independent_group_count": 3,
                "agreeing_provider_count_for_13_mps": 2,
            },
            "incorrect_actions": [
                "apply_implicit_majority_vote",
                "discard_minority_source_without_adjudication",
                "convert_two_matching_values_to_verified",
                "authorize_takeoff_from_two_of_three_sources",
            ],
            "required_action": "request_explicit_weather_adjudication",
            "result": body,
            "sha256": {
                "official_observation": sha256_bytes(official_observation_bytes),
                "sensor_observation": sha256_bytes(sensor_observation_bytes),
                "lidar_observation": sha256_bytes(lidar_observation_bytes),
                "assurance_profile": sha256_bytes(profile_bytes),
                "official_descriptor": sha256_bytes(official_descriptor_bytes),
                "sensor_descriptor": sha256_bytes(sensor_descriptor_bytes),
                "lidar_descriptor": sha256_bytes(lidar_descriptor_bytes),
                "verification_request": sha256_bytes(request_bytes),
                "official_response": sha256_bytes(response_bytes["official_response"]),
                "sensor_response": sha256_bytes(response_bytes["sensor_response"]),
                "lidar_response": sha256_bytes(response_bytes["lidar_response"]),
                "assurance_evaluation": sha256_bytes(evaluation_bytes),
            },
            "boundaries": {
                "majority_policy_declared": False,
                "minority_source_discarded": False,
                "provider_precedence_inferred": False,
                "external_truth_verified": False,
                "production_output_released": False,
                "action_authorized": False,
                "action_executed": False,
            },
        }
    }
    _write(FILES["scenario"], scenario)
    return {
        "profile": profile.to_dict(),
        "request": request.to_dict(),
        "responses": [response.to_dict() for _, response in responses],
        "evaluation": evaluation,
        "scenario": scenario,
    }


if __name__ == "__main__":
    build()
    print("GT30 three-source weather conflict bundle generated")
