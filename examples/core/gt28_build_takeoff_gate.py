from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping

from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.control_evaluation import (
    ControlEvaluationResult,
    evaluate_control_profile,
    load_control_evaluation,
)
from geotask_core.v1.executor import execute_canonical
from geotask_core.v1.observation import load_observation
from geotask_core.v1.result import GeotaskResult
from geotask_core.v1.verification_session import (
    VerificationSession,
    load_verification_session,
    validate_verification_session_bindings,
)
from geotask_core.v1.world_state import WorldState, load_world_state


CORE = Path(__file__).resolve().parent
DEFAULT_SCENARIO = CORE / "gt28_takeoff_authorization_gate.json"


class GT28BuildError(ValueError):
    pass


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _pretty_bytes(payload: Mapping[str, object]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _scenario_payload(path: Path) -> Mapping[str, object]:
    payload = _json(path)
    scenario = payload.get("scenario")
    if not isinstance(scenario, Mapping):
        raise GT28BuildError("scenario must be a mapping")
    return scenario


def _files(scenario: Mapping[str, object]) -> Mapping[str, object]:
    files = scenario.get("files")
    if not isinstance(files, Mapping):
        raise GT28BuildError("scenario.files must be a mapping")
    return files


def _path(base: Path, files: Mapping[str, object], key: str) -> Path:
    value = files.get(key)
    if not isinstance(value, str) or not value.strip():
        raise GT28BuildError(f"scenario.files.{key} must be a non-empty string")
    return base / value


def _build_execution(task_path: Path) -> tuple[object, GeotaskResult, bytes]:
    raw_document = load_geotask(task_path)
    errors = [
        item
        for item in validate_document(raw_document)
        if item.get("severity", "error") == "error"
    ]
    if errors:
        raise GT28BuildError(f"task validation failed: {errors}")
    document = canonicalize(raw_document)
    generated = execute_canonical(document).to_dict()
    execution = generated["geotask_result"]["execution"]
    execution["started_at"] = "2026-08-04T14:00:06+08:00"
    execution["finished_at"] = "2026-08-04T14:00:07+08:00"
    result = GeotaskResult.from_dict(generated)
    return document, result, _pretty_bytes(result.to_dict())


def _build_control(
    scenario: Mapping[str, object],
    document: object,
    execution: GeotaskResult,
) -> tuple[ControlEvaluationResult, bytes]:
    preconditions = scenario.get("preconditions")
    if not isinstance(preconditions, Mapping):
        raise GT28BuildError("scenario.preconditions must be a mapping")
    domain_state = {
        "wind_speed_mps": preconditions.get("wind_speed_mps"),
        "max_wind_mps": preconditions.get("max_wind_mps"),
    }
    control = evaluate_control_profile(document, execution, domain_state)
    payload = control.to_dict()
    loaded = load_control_evaluation(payload)
    return loaded, _pretty_bytes(loaded.to_dict())


def _artifact_ref(
    ref_id: str,
    artifact_id: str,
    schema_version: str,
    instance_id: str,
    content: bytes,
) -> dict[str, object]:
    return {
        "ref_id": ref_id,
        "artifact_id": artifact_id,
        "schema_version": schema_version,
        "instance_id": instance_id,
        "content_sha256": _sha256(content),
    }


def _build_session(
    world_state: WorldState,
    task_bytes: bytes,
    execution: GeotaskResult,
    execution_bytes: bytes,
    control: ControlEvaluationResult,
    control_bytes: bytes,
) -> tuple[VerificationSession, bytes]:
    payload = {
        "verification_session": {
            "schema_id": "https://stpku.github.io/GeoTask/schemas/geotask-verification-session-v0.1.schema.json",
            "schema_version": "0.1",
            "session_id": "gt28-fictional-takeoff-authorization-gate",
            "recorded_at": "2026-08-04T14:00:09+08:00",
            "state": "blocked",
            "reason": "Route, altitude, weather window, and wind preconditions pass, but five independent authorization fields remain unknown, so automatic takeoff stays blocked.",
            "world_state": {
                "world_state_id": world_state.world_state_id,
                "revision": world_state.revision,
                "as_of": world_state.as_of,
                "semantic_fingerprint": world_state.semantic_fingerprint(),
            },
            "observation_refs": [
                "obs-takeoff-authorization-inventory-gt28",
                "obs-uav-route-preflight-gt28",
                "obs-weather-preflight-gt28",
            ],
            "task_refs": [
                _artifact_ref(
                    "task-takeoff-gate-gt28",
                    "geotask.document",
                    "1.0",
                    execution.task_id,
                    task_bytes,
                )
            ],
            "execution_result_refs": [
                _artifact_ref(
                    "execution-takeoff-gate-gt28",
                    "geotask.execution-result",
                    "1.0",
                    execution.task_id,
                    execution_bytes,
                )
            ],
            "control_evaluation_refs": [
                _artifact_ref(
                    "control-takeoff-gate-gt28",
                    "geotask.control-evaluation",
                    "1.0",
                    control.task_id,
                    control_bytes,
                )
            ],
            "state_transition_refs": [],
            "discrepancy_refs": [],
            "action_eligibility": [
                {
                    "output_ref": "route_weather_precheck",
                    "state": "eligible",
                    "reason": "The fixed execution result verifies that the route avoids the restricted zone, the altitude overlaps the operating corridor, the weather window is valid, and 8 m/s is within the 12 m/s limit.",
                    "basis_refs": [
                        "task-takeoff-gate-gt28",
                        "execution-takeoff-gate-gt28",
                    ],
                    "observation_refs": [
                        "obs-uav-route-preflight-gt28",
                        "obs-weather-preflight-gt28",
                    ],
                },
                {
                    "output_ref": "automatic_takeoff_authorization",
                    "state": "blocked",
                    "reason": "Safe route and acceptable weather do not substitute for airspace, operator, departure-site, weather-release, and mission authorization.",
                    "basis_refs": [
                        "task-takeoff-gate-gt28",
                        "execution-takeoff-gate-gt28",
                        "control-takeoff-gate-gt28",
                    ],
                    "observation_refs": [
                        "obs-takeoff-authorization-inventory-gt28",
                        "obs-uav-route-preflight-gt28",
                        "obs-weather-preflight-gt28",
                    ],
                },
                {
                    "output_ref": "takeoff_command",
                    "state": "blocked",
                    "reason": "No command may be emitted while automatic takeoff authorization is unresolved.",
                    "basis_refs": [
                        "task-takeoff-gate-gt28",
                        "execution-takeoff-gate-gt28",
                        "control-takeoff-gate-gt28",
                    ],
                    "observation_refs": [
                        "obs-takeoff-authorization-inventory-gt28",
                        "obs-uav-route-preflight-gt28",
                        "obs-weather-preflight-gt28",
                    ],
                },
            ],
            "recheck_triggers": [
                {
                    "id": "authorization-bundle-complete-gt28",
                    "condition": "airspace_authorized == true AND operator_authorized == true AND departure_site_authorized == true AND weather_release_authorized == true AND mission_authorized == true",
                    "state": "unknown",
                    "reason": "All five authorization identifiers are absent from the current control context and must be supplied before another eligibility check.",
                    "affected_output_refs": [
                        "automatic_takeoff_authorization",
                        "takeoff_command",
                    ],
                    "basis_refs": [
                        "control-takeoff-gate-gt28"
                    ],
                    "observation_refs": [
                        "obs-takeoff-authorization-inventory-gt28"
                    ],
                }
            ],
        }
    }
    session = load_verification_session(payload)
    session_bytes = _pretty_bytes(session.to_dict())
    validate_verification_session_bindings(
        session,
        world_state,
        {
            "task-takeoff-gate-gt28": task_bytes,
            "execution-takeoff-gate-gt28": execution_bytes,
            "control-takeoff-gate-gt28": control_bytes,
        },
    )
    return session, session_bytes


def _validate_case_scope(
    scenario: Mapping[str, object],
    world_state: WorldState,
    execution: GeotaskResult,
    control: ControlEvaluationResult,
    session: VerificationSession,
) -> None:
    expected = scenario.get("expected")
    if not isinstance(expected, Mapping):
        raise GT28BuildError("scenario.expected must be a mapping")

    outputs = execution.outputs
    required_outputs = {
        "route_intersects_restricted_zone": False,
        "altitude_within_operating_corridor": True,
        "weather_window_valid": True,
    }
    if outputs != required_outputs:
        raise GT28BuildError(f"unexpected preflight outputs: {outputs}")
    if execution.execution.status != expected.get("execution_status"):
        raise GT28BuildError("execution status mismatch")
    if control.state != expected.get("control_state"):
        raise GT28BuildError("control state mismatch")
    if session.state != expected.get("session_state"):
        raise GT28BuildError("session state mismatch")

    required_authorizations = scenario.get("required_authorizations")
    if not isinstance(required_authorizations, list):
        raise GT28BuildError("scenario.required_authorizations must be a list")
    if set(control.unknown_identifiers) != set(required_authorizations):
        raise GT28BuildError("unknown authorization scope mismatch")
    if len(control.unknown_identifiers) != expected.get("unknown_authorization_count"):
        raise GT28BuildError("unknown authorization count mismatch")
    if control.blocked_outputs != (
        "automatic_takeoff_authorization",
        "takeoff_command",
    ):
        raise GT28BuildError("control must keep both high-risk outputs blocked")
    if control.action_executed is not False:
        raise GT28BuildError("public control evaluation must never execute action")

    eligibility = {item.output_ref: item.state for item in session.action_eligibility}
    if eligibility != {
        "automatic_takeoff_authorization": "blocked",
        "route_weather_precheck": "eligible",
        "takeoff_command": "blocked",
    }:
        raise GT28BuildError(f"unexpected action eligibility: {eligibility}")
    if world_state.semantic_fingerprint() != expected.get(
        "world_state_semantic_fingerprint"
    ) and expected.get("world_state_semantic_fingerprint") != "PENDING":
        raise GT28BuildError("world-state fingerprint mismatch")
    if session.semantic_fingerprint() != expected.get(
        "verification_session_semantic_fingerprint"
    ) and expected.get("verification_session_semantic_fingerprint") != "PENDING":
        raise GT28BuildError("verification-session fingerprint mismatch")


def build_gt28_takeoff_gate(
    scenario_path: Path = DEFAULT_SCENARIO,
) -> dict[str, object]:
    scenario_path = scenario_path.resolve()
    base = scenario_path.parent
    scenario = _scenario_payload(scenario_path)
    files = _files(scenario)

    task_path = _path(base, files, "task")
    world_state_path = _path(base, files, "world_state")
    route_observation_path = _path(base, files, "route_observation")
    weather_observation_path = _path(base, files, "weather_observation")
    authorization_observation_path = _path(base, files, "authorization_observation")

    for path in (
        route_observation_path,
        weather_observation_path,
        authorization_observation_path,
    ):
        load_observation(_json(path))

    world_state = load_world_state(_json(world_state_path))
    task_bytes = task_path.read_bytes()
    document, execution, execution_bytes = _build_execution(task_path)
    control, control_bytes = _build_control(scenario, document, execution)
    session, session_bytes = _build_session(
        world_state,
        task_bytes,
        execution,
        execution_bytes,
        control,
        control_bytes,
    )
    _validate_case_scope(scenario, world_state, execution, control, session)

    expected = scenario.get("expected")
    if isinstance(expected, Mapping):
        expected_hash = expected.get("control_evaluation_content_sha256")
        actual_hash = _sha256(control_bytes)
        if expected_hash not in {"PENDING", actual_hash}:
            raise GT28BuildError("control-evaluation content hash mismatch")

    return {
        "scenario": scenario,
        "world_state": world_state,
        "execution_result": execution,
        "control_evaluation": control,
        "verification_session": session,
        "bytes": {
            "execution_result": execution_bytes,
            "control_evaluation": control_bytes,
            "verification_session": session_bytes,
        },
    }


def _write_bundle(bundle: Mapping[str, object], scenario_path: Path) -> None:
    scenario = bundle["scenario"]
    if not isinstance(scenario, Mapping):
        raise GT28BuildError("bundle scenario missing")
    files = _files(scenario)
    base = scenario_path.resolve().parent
    raw = bundle["bytes"]
    if not isinstance(raw, Mapping):
        raise GT28BuildError("bundle bytes missing")
    for key in ("execution_result", "control_evaluation", "verification_session"):
        content = raw.get(key)
        if not isinstance(content, bytes):
            raise GT28BuildError(f"bundle bytes missing for {key}")
        _path(base, files, key).write_bytes(content)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the fixed GT28 takeoff gate artifacts.")
    parser.add_argument("scenario", nargs="?", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    bundle = build_gt28_takeoff_gate(args.scenario)
    if args.write:
        _write_bundle(bundle, args.scenario)
    else:
        print(
            json.dumps(
                {
                    "world_state_semantic_fingerprint": bundle[
                        "world_state"
                    ].semantic_fingerprint(),
                    "control_evaluation_content_sha256": _sha256(
                        bundle["bytes"]["control_evaluation"]
                    ),
                    "verification_session_semantic_fingerprint": bundle[
                        "verification_session"
                    ].semantic_fingerprint(),
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
