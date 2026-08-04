"""Build the fixed GT31 human weather adjudication bundle.

All data are fictional. The builder binds the GT30 three-source conflict, one
fictional context-evidence packet, one human-review Provider response, and the
existing GT28 takeoff Control Evaluation. Human review may make the scoped
weather conclusion eligible, but it never publishes production output,
authorizes takeoff, sends a command, or executes a flight action.
"""

from __future__ import annotations

import json
from pathlib import Path

from geotask_core.v1.control_evaluation import load_control_evaluation
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

INPUTS = {
    "gt30_official_response": CORE / "verification_response_authoritative_weather_gt30.json",
    "gt30_sensor_response": CORE / "verification_response_onsite_sensor_gt30.json",
    "gt30_lidar_response": CORE / "verification_response_mobile_lidar_gt30.json",
    "gt30_profile": CORE / "assurance_profile_weather_three_source_gt30.json",
    "gt30_evaluation": CORE / "assurance_evaluation_weather_three_source_gt30.json",
    "gt28_control": CORE / "takeoff_authorization_control_evaluation_gt28.json",
}

FILES = {
    "context": CORE / "weather_context_evidence_gt31.json",
    "profile": CORE / "assurance_profile_human_weather_adjudication_gt31.json",
    "descriptor": CORE / "verification_provider_descriptor_human_weather_reviewer_gt31.json",
    "request": CORE / "verification_request_human_weather_adjudication_gt31.json",
    "response": CORE / "verification_response_human_weather_adjudication_gt31.json",
    "evaluation": CORE / "assurance_evaluation_human_weather_adjudication_gt31.json",
    "scenario": CORE / "gt31_human_weather_adjudication.json",
}


def _json_bytes(path: Path) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    return json.loads(raw), raw


def _write(path: Path, payload: dict) -> bytes:
    raw = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.write_bytes(raw)
    return raw


def _validate_context_evidence(payload: dict, input_bytes: dict[str, bytes]) -> None:
    body = payload.get("weather_context_evidence")
    assert isinstance(body, dict)
    assert body["evidence_id"] == "fictional-east-weather-context-gt31"
    assert body["reason_code"] == "shared_local_test_interference"
    assert body["selected_ambient_wind_speed_mps"] == 8
    assert body["mission_wind_limit_mps"] == 12
    assert body["weather_suitable"] is True
    assert body["responses_retained"] == [
        "weather-response-authoritative-gt30",
        "weather-response-onsite-sensor-gt30",
        "weather-response-mobile-lidar-gt30",
    ]
    assert body["responses_not_applicable_to_mission_claim"] == [
        "weather-response-onsite-sensor-gt30",
        "weather-response-mobile-lidar-gt30",
    ]
    assert body["responses_deleted"] == []
    assert body["source_sha256"] == {
        "official_response": sha256_bytes(input_bytes["gt30_official_response"]),
        "sensor_response": sha256_bytes(input_bytes["gt30_sensor_response"]),
        "lidar_response": sha256_bytes(input_bytes["gt30_lidar_response"]),
    }
    assert body["fictional_context_only"] is True
    assert body["external_truth_verified"] is False
    assert body["action_authorized"] is False
    assert body["action_executed"] is False


def build() -> dict[str, dict]:
    input_payloads: dict[str, dict] = {}
    input_bytes: dict[str, bytes] = {}
    for key, path in INPUTS.items():
        payload, raw = _json_bytes(path)
        input_payloads[key] = payload
        input_bytes[key] = raw

    for key in (
        "gt30_official_response",
        "gt30_sensor_response",
        "gt30_lidar_response",
    ):
        load_verification_response(input_payloads[key])
    gt30_profile = load_assurance_profile(input_payloads["gt30_profile"])
    gt30_evaluation = input_payloads["gt30_evaluation"]["assurance_evaluation"]
    assert gt30_evaluation["state"] == "unknown"
    assert gt30_evaluation["next_action"] == "request_explicit_weather_adjudication"

    takeoff_control = load_control_evaluation(input_payloads["gt28_control"])
    assert takeoff_control.state == "unknown"
    assert takeoff_control.context.values["wind_speed_mps"] == 8
    assert takeoff_control.blocked_outputs == (
        "automatic_takeoff_authorization",
        "takeoff_command",
    )
    assert takeoff_control.action_executed is False

    context_payload = {
        "weather_context_evidence": {
            "evidence_version": "0.1",
            "evidence_id": "fictional-east-weather-context-gt31",
            "created_at": "2026-08-04T14:07:00+08:00",
            "scope": "fictional-east-mission-corridor",
            "reason_code": "shared_local_test_interference",
            "reason_zh": "现场传感器和移动测风激光雷达受到同一局部测试气流影响；三份响应全部保留，仅调整两份13米/秒读数对任务走廊环境风速命题的适用范围。",
            "selected_ambient_wind_speed_mps": 8,
            "mission_wind_limit_mps": 12,
            "weather_suitable": True,
            "responses_retained": [
                "weather-response-authoritative-gt30",
                "weather-response-onsite-sensor-gt30",
                "weather-response-mobile-lidar-gt30",
            ],
            "responses_not_applicable_to_mission_claim": [
                "weather-response-onsite-sensor-gt30",
                "weather-response-mobile-lidar-gt30",
            ],
            "responses_deleted": [],
            "source_sha256": {
                "official_response": sha256_bytes(input_bytes["gt30_official_response"]),
                "sensor_response": sha256_bytes(input_bytes["gt30_sensor_response"]),
                "lidar_response": sha256_bytes(input_bytes["gt30_lidar_response"]),
            },
            "fictional_context_only": True,
            "external_truth_verified": False,
            "action_authorized": False,
            "action_executed": False,
        }
    }
    _validate_context_evidence(context_payload, input_bytes)
    context_bytes = _write(FILES["context"], context_payload)

    profile_payload = {
        "assurance_profile": {
            "profile_version": "0.1",
            "profile_id": "gt31-human-weather-adjudication",
            "title": "GT31 explicit human weather adjudication",
            "minimum_provider_count": 1,
            "minimum_independent_groups": 1,
            "allowed_provider_types": ["human_review"],
            "require_fresh_results": True,
            "max_result_age_seconds": 900,
            "require_reproducible": True,
            "accepted_reproducibility": ["repeatable"],
            "require_calibration": True,
            "accepted_calibration_states": ["not_applicable"],
            "conflict_policy": "unknown",
            "eligible_output": "weather_condition_verified",
            "blocked_outputs": ["weather_condition_pending_review"],
            "blocked_actions": ["takeoff_command"],
            "next_action_on_insufficient_assurance": "request_additional_human_weather_review",
            "action_authorized": False,
            "action_executed": False,
        }
    }
    profile = load_assurance_profile(profile_payload)
    profile_bytes = _write(FILES["profile"], profile.to_dict())

    descriptor_payload = {
        "verification_provider_descriptor": {
            "interface_version": "0.1",
            "provider_id": "geotask.provider.mock-human-weather-reviewer",
            "provider_version": "0.1.0",
            "title": "Mock Human Weather Reviewer",
            "provider_type": "human_review",
            "implementation_kind": "mock",
            "production_ready": False,
            "capabilities": ["weather.conflict_adjudication"],
            "supported_methods": ["adjudicate_current_wind_speed"],
            "independence_group": "fictional-human-weather-review-board",
            "reproducibility": "repeatable",
            "calibration_status": "not_applicable",
            "valid_until": "2026-08-05T00:00:00+08:00",
            "audit_supported": True,
            "credentials_managed_externally": True,
            "external_side_effects_allowed": False,
        }
    }
    descriptor = load_verification_provider_descriptor(descriptor_payload)
    descriptor_bytes = _write(FILES["descriptor"], descriptor.to_dict())

    request_payload = {
        "verification_request": {
            "request_version": "0.1",
            "request_id": "adjudicate-east-current-wind-speed-gt31",
            "created_at": "2026-08-04T14:07:10+08:00",
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
                    "ref_id": "gt30-authoritative-weather-response",
                    "artifact_id": "geotask.verification-response",
                    "sha256": sha256_bytes(input_bytes["gt30_official_response"]),
                },
                {
                    "ref_id": "gt30-onsite-sensor-response",
                    "artifact_id": "geotask.verification-response",
                    "sha256": sha256_bytes(input_bytes["gt30_sensor_response"]),
                },
                {
                    "ref_id": "gt30-mobile-lidar-response",
                    "artifact_id": "geotask.verification-response",
                    "sha256": sha256_bytes(input_bytes["gt30_lidar_response"]),
                },
                {
                    "ref_id": "gt30-assurance-profile",
                    "artifact_id": "geotask.assurance-profile",
                    "sha256": sha256_bytes(input_bytes["gt30_profile"]),
                },
                {
                    "ref_id": "gt30-assurance-evaluation",
                    "artifact_id": "example.assurance-evaluation",
                    "sha256": sha256_bytes(input_bytes["gt30_evaluation"]),
                },
                {
                    "ref_id": "fictional-weather-context-evidence",
                    "artifact_id": "example.fictional-context-evidence",
                    "sha256": sha256_bytes(context_bytes),
                },
            ],
            "verification_method": "adjudicate_current_wind_speed",
            "required_capabilities": ["weather.conflict_adjudication"],
            "allowed_provider_types": ["human_review"],
            "assurance_profile_ref": {
                "profile_id": profile.profile_id,
                "sha256": sha256_bytes(profile_bytes),
            },
            "deadline": "2026-08-04T14:10:00+08:00",
            "external_side_effects_allowed": False,
            "action_authorized": False,
        }
    }
    request = load_verification_request(request_payload)
    request_bytes = _write(FILES["request"], request.to_dict())
    contract = validate_verification_request_contract(descriptor, request)
    assert contract["verification_provider_contract"]["valid"] is True

    response_payload = {
        "verification_response": {
            "response_version": "0.1",
            "response_id": "weather-response-human-adjudication-gt31",
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
                "value": 8,
                "unit": "meter_per_second",
                "observed_at": "2026-08-04T14:06:00+08:00",
                "valid_until": "2026-08-04T14:11:00+08:00",
            },
            "verification_method": request.verification_method,
            "evidence_refs": [
                f"context-evidence:sha256:{sha256_bytes(context_bytes)}",
                "gt30-response:weather-response-authoritative-gt30",
                "gt30-response:weather-response-onsite-sensor-gt30",
                "gt30-response:weather-response-mobile-lidar-gt30",
            ],
            "assurance_declarations": {
                "independence_group": descriptor.independence_group,
                "reproducibility": descriptor.reproducibility,
                "calibration_status": descriptor.calibration_status,
                "confidence": None,
            },
            "diagnostics": [],
            "completed_at": "2026-08-04T14:08:00+08:00",
            "independently_verified": False,
            "production_output_released": False,
            "action_authorized": False,
            "action_executed": False,
        }
    }
    response = load_verification_response(response_payload)
    assert response.state == "verified"
    assert response.value == 8
    assert response.unit == "meter_per_second"
    validate_verification_response_bindings(
        response,
        request=request,
        request_bytes=request_bytes,
        descriptor=descriptor,
        descriptor_bytes=descriptor_bytes,
    )
    response_bytes = _write(FILES["response"], response.to_dict())

    evaluation = evaluate_verification_assurance(
        profile,
        request=request,
        bound_results=[(descriptor, response)],
        evaluated_at="2026-08-04T14:08:30+08:00",
    )
    evaluation_bytes = _write(FILES["evaluation"], evaluation)
    assurance = evaluation["assurance_evaluation"]
    assert assurance["state"] == "verified"
    assert assurance["reason"] == "assurance_requirements_satisfied"
    assert assurance["eligible_outputs"] == ["weather_condition_verified"]
    assert assurance["blocked_outputs"] == []
    assert assurance["blocked_actions"] == ["takeoff_command"]
    assert assurance["production_output_released"] is False
    assert assurance["action_authorized"] is False
    assert assurance["action_executed"] is False

    scenario = {
        "scenario": {
            "id": "gt31-human-weather-adjudication",
            "title_zh": "人工复核解决气象冲突后，天气合格就能自动起飞吗？",
            "title_en": "After human review resolves the weather conflict, may the aircraft take off automatically?",
            "facts": {
                "gt30_values_mps": [8, 13, 13],
                "human_selected_wind_speed_mps": 8,
                "mission_wind_limit_mps": 12,
                "weather_suitable": True,
                "retained_response_count": 3,
                "not_applicable_response_count": 2,
                "deleted_response_count": 0,
            },
            "adjudication": {
                "policy": "explicit_human_review",
                "reason_code": "shared_local_test_interference",
                "selected_claim": "east-current-wind-speed=8 meter_per_second",
                "majority_vote_used": False,
                "conflicting_responses_preserved": True,
                "provider_self_assured": False,
            },
            "layered_gate": {
                "evidence_adjudication": "completed",
                "weather_conclusion": "eligible",
                "takeoff_authorization": "blocked",
                "takeoff_command": "blocked",
                "missing_authorizations": list(takeoff_control.unknown_identifiers),
            },
            "incorrect_actions": [
                "treat_human_response_as_self_assured",
                "delete_conflicting_sensor_responses",
                "equate_weather_eligibility_with_takeoff_authorization",
                "send_takeoff_command_after_weather_review",
            ],
            "required_action": "request_remaining_takeoff_authorizations",
            "assurance_evaluation": assurance,
            "takeoff_control_evaluation": {
                "state": takeoff_control.state,
                "blocked_outputs": list(takeoff_control.blocked_outputs),
                "unknown_identifiers": list(takeoff_control.unknown_identifiers),
                "action_executed": takeoff_control.action_executed,
            },
            "sha256": {
                "context_evidence": sha256_bytes(context_bytes),
                "assurance_profile": sha256_bytes(profile_bytes),
                "human_descriptor": sha256_bytes(descriptor_bytes),
                "verification_request": sha256_bytes(request_bytes),
                "human_response": sha256_bytes(response_bytes),
                "assurance_evaluation": sha256_bytes(evaluation_bytes),
                **{key: sha256_bytes(raw) for key, raw in input_bytes.items()},
            },
            "boundaries": {
                "human_provider_self_assured": False,
                "conflicting_responses_deleted": False,
                "external_truth_verified_by_core": False,
                "weather_output_eligible": True,
                "production_output_released": False,
                "automatic_takeoff_authorization_eligible": False,
                "action_authorized": False,
                "action_executed": False,
            },
        }
    }
    _write(FILES["scenario"], scenario)
    return {
        "context": context_payload,
        "profile": profile.to_dict(),
        "descriptor": descriptor.to_dict(),
        "request": request.to_dict(),
        "response": response.to_dict(),
        "evaluation": evaluation,
        "scenario": scenario,
    }


if __name__ == "__main__":
    build()
    print("GT31 human weather adjudication bundle generated")
