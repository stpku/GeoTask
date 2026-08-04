from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.control_evaluation import (
    evaluate_control_profile,
    load_control_evaluation,
)
from geotask_core.v1.observation import load_observation
from geotask_core.v1.result import GeotaskResult
from geotask_core.v1.verification_session import (
    VerificationSessionFormatError,
    load_verification_session,
    validate_verification_session_bindings,
)
from geotask_core.v1.world_state import load_world_state


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "examples" / "core"
SCENARIO = CORE / "gt28_takeoff_authorization_gate.json"
TASK = CORE / "gt28_uav_takeoff_authorization_gate.yaml"
WORLD_STATE = CORE / "world_state_uav_takeoff_gate_gt28.json"
ROUTE_OBSERVATION = CORE / "observation_uav_route_preflight_gt28.json"
WEATHER_OBSERVATION = CORE / "observation_weather_preflight_gt28.json"
AUTH_OBSERVATION = CORE / "observation_takeoff_authorization_inventory_gt28.json"
EXECUTION = CORE / "takeoff_preflight_execution_result_gt28.json"
CONTROL = CORE / "takeoff_authorization_control_evaluation_gt28.json"
SESSION = CORE / "verification_session_takeoff_gate_gt28.json"
BUILDER_PATH = CORE / "gt28_build_takeoff_gate.py"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_builder():
    spec = importlib.util.spec_from_file_location("gt28_builder", BUILDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILDER = _load_builder()


def _dependencies():
    return (
        load_world_state(_json(WORLD_STATE)),
        GeotaskResult.from_dict(_json(EXECUTION)),
        load_control_evaluation(_json(CONTROL)),
        load_verification_session(_json(SESSION)),
    )


def test_gt28_fixed_artifacts_are_strict_and_schema_valid() -> None:
    document = load_geotask(TASK)
    assert [
        item
        for item in validate_document(document)
        if item.get("severity", "error") == "error"
    ] == []
    for path in (ROUTE_OBSERVATION, WEATHER_OBSERVATION, AUTH_OBSERVATION):
        load_observation(_json(path))
    world_state, execution, control, session = _dependencies()
    assert world_state.revision == 1
    assert execution.execution.status == "completed"
    assert control.state == "unknown"
    assert session.state == "blocked"

    for schema_name, payload in (
        ("geotask-observation-v0.1.schema.json", _json(ROUTE_OBSERVATION)),
        ("geotask-observation-v0.1.schema.json", _json(WEATHER_OBSERVATION)),
        ("geotask-observation-v0.1.schema.json", _json(AUTH_OBSERVATION)),
        ("geotask-world-state-v0.1.schema.json", _json(WORLD_STATE)),
        ("geotask-result-v1.0.schema.json", _json(EXECUTION)),
        ("geotask-control-evaluation-v1.0.schema.json", _json(CONTROL)),
        ("geotask-verification-session-v0.1.schema.json", _json(SESSION)),
    ):
        schema = _json(ROOT / "schemas" / schema_name)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(payload)


def test_gt28_builder_reproduces_fixed_artifacts_and_fingerprints() -> None:
    bundle = BUILDER.build_gt28_takeoff_gate(SCENARIO)
    expected = _json(SCENARIO)["scenario"]["expected"]
    assert bundle["bytes"]["execution_result"] == EXECUTION.read_bytes()
    assert bundle["bytes"]["control_evaluation"] == CONTROL.read_bytes()
    assert bundle["bytes"]["verification_session"] == SESSION.read_bytes()
    assert bundle["world_state"].semantic_fingerprint() == expected[
        "world_state_semantic_fingerprint"
    ]
    assert hashlib.sha256(bundle["bytes"]["control_evaluation"]).hexdigest() == expected[
        "control_evaluation_content_sha256"
    ]
    assert bundle["verification_session"].semantic_fingerprint() == expected[
        "verification_session_semantic_fingerprint"
    ]


def test_gt28_route_and_weather_pass_but_five_authorizations_remain_unknown() -> None:
    _, execution, control, _ = _dependencies()
    assert execution.outputs == {
        "route_intersects_restricted_zone": False,
        "altitude_within_operating_corridor": True,
        "weather_window_valid": True,
    }
    assert control.context.values["wind_speed_mps"] == 8
    assert control.context.values["max_wind_mps"] == 12
    assert set(control.unknown_identifiers) == {
        "airspace_authorized",
        "operator_authorized",
        "departure_site_authorized",
        "weather_release_authorized",
        "mission_authorized",
    }
    assert control.blocked_outputs == (
        "automatic_takeoff_authorization",
        "takeoff_command",
    )
    assert control.action_executed is False


def test_gt28_session_separates_precheck_eligibility_from_takeoff_authority() -> None:
    _, _, _, session = _dependencies()
    eligibility = {item.output_ref: item.state for item in session.action_eligibility}
    assert eligibility == {
        "automatic_takeoff_authorization": "blocked",
        "route_weather_precheck": "eligible",
        "takeoff_command": "blocked",
    }
    assert session.recheck_triggers[0].state == "unknown"
    assert session.recheck_triggers[0].affected_output_refs == (
        "automatic_takeoff_authorization",
        "takeoff_command",
    )


def test_gt28_exact_session_binding_rejects_tampered_control_bytes() -> None:
    world_state, _, _, session = _dependencies()
    contents = {
        "task-takeoff-gate-gt28": TASK.read_bytes(),
        "execution-takeoff-gate-gt28": EXECUTION.read_bytes(),
        "control-takeoff-gate-gt28": CONTROL.read_bytes(),
    }
    validate_verification_session_bindings(session, world_state, contents)
    contents["control-takeoff-gate-gt28"] += b"\n"
    with pytest.raises(VerificationSessionFormatError, match="SHA-256 mismatch"):
        validate_verification_session_bindings(session, world_state, contents)


def test_gt28_even_complete_authorization_context_does_not_execute_action() -> None:
    document = canonicalize(load_geotask(TASK))
    execution = GeotaskResult.from_dict(_json(EXECUTION))
    control = evaluate_control_profile(
        document,
        execution,
        {
            "wind_speed_mps": 8,
            "max_wind_mps": 12,
            "airspace_authorized": True,
            "operator_authorized": True,
            "departure_site_authorized": True,
            "weather_release_authorized": True,
            "mission_authorized": True,
        },
    )
    assert control.state == "satisfied"
    assert control.gate_satisfied is True
    assert control.blocked_outputs == ()
    assert control.eligible_outputs == (
        "automatic_takeoff_authorization",
        "takeoff_command",
    )
    assert control.action_executed is False
    assert control.evaluations[0].action_executed is False


def test_gt28_candidate_actions_fail_closed() -> None:
    scenario = _json(SCENARIO)["scenario"]
    candidates = {
        item["id"]: item["expected_state"] for item in scenario["candidate_actions"]
    }
    assert candidates == {
        "automatic_takeoff": "contradicted",
        "infer_authorization": "contradicted",
        "hold_and_request_authorization_bundle": "verified",
    }
    boundary = scenario["safety_boundary"]
    assert boundary["route_and_weather_preconditions_verified"] is True
    assert boundary["authorization_bundle_complete"] is False
    assert boundary["eligible_output_released"] is False
    assert boundary["automatic_takeoff_authorized"] is False
    assert boundary["takeoff_command_sent"] is False
    assert boundary["action_executed"] is False
