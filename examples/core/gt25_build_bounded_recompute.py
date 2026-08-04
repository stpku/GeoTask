#!/usr/bin/env python3
"""Build the fictional GT25 bounded safety-distance recompute bundle.

The case validates a caller-declared recompute scope. It derives only two UAV-
dependent corridor distances through the allowlisted ``subtract`` method and
preserves two explicitly reusable values. It does not discover dependency scope,
execute arbitrary code, materialize a successor World State, rerun assertions,
release outputs, verify external truth, authorize action, or execute action.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence

import yaml

from geotask_core.v1.correction_request import (
    CorrectionRequest,
    load_correction_request,
    validate_correction_request_bindings,
)
from geotask_core.v1.discrepancy_report import (
    DiscrepancyReport,
    load_discrepancy_report,
    validate_discrepancy_report_bindings,
)
from geotask_core.v1.observation import Observation, load_observation
from geotask_core.v1.recompute_derivation import (
    RecomputeDerivationResult,
    evaluate_recompute_derivations,
    load_recompute_derivation_result,
    validate_recompute_derivation_bindings,
)
from geotask_core.v1.world_state import WorldState, load_world_state


class GT25BuildError(ValueError):
    """Raised when the GT25 declared recompute or reuse scope is invalid."""


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise GT25BuildError(f"{path}: must be an object")
    return value


def _sequence(value: object, path: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise GT25BuildError(f"{path}: must be an array")
    return value


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GT25BuildError(f"{path}: must be a non-empty string")
    return value


def _case_file(scenario_path: Path, filename: object, path: str) -> Path:
    name = _string(filename, path)
    base = scenario_path.parent.resolve()
    candidate = (base / name).resolve()
    if candidate.parent != base:
        raise GT25BuildError(f"{path}: must stay in {base}")
    return candidate


def _pretty_bytes(payload: Mapping[str, object]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _resolve_world_state_value(world_state: WorldState, path: str) -> object:
    parts = path.strip("/").split("/")
    if parts[:1] == ["relations"] and len(parts) == 3 and parts[2] == "value":
        relation = next((item for item in world_state.relations if item.id == parts[1]), None)
        if relation is None:
            raise GT25BuildError(f"{path}: relation not found")
        return relation.value
    if (
        parts[:1] == ["objects"]
        and len(parts) == 5
        and parts[2] == "attributes"
        and parts[4] == "value"
    ):
        obj = next((item for item in world_state.objects if item.id == parts[1]), None)
        if obj is None:
            raise GT25BuildError(f"{path}: object not found")
        attribute = next((item for item in obj.attributes if item.name == parts[3]), None)
        if attribute is None:
            raise GT25BuildError(f"{path}: attribute not found")
        return attribute.value
    raise GT25BuildError(f"{path}: unsupported case path")


def _load_inputs(
    scenario_path: Path,
    scenario: Mapping[str, object],
) -> tuple[Observation, bytes, WorldState, bytes, Mapping[str, object], bytes]:
    observation_path = _case_file(
        scenario_path, scenario.get("observation"), "scenario.observation"
    )
    observation_bytes = observation_path.read_bytes()
    observation = load_observation(json.loads(observation_bytes))

    world_state_path = _case_file(
        scenario_path, scenario.get("world_state"), "scenario.world_state"
    )
    world_state_bytes = world_state_path.read_bytes()
    world_state = load_world_state(json.loads(world_state_bytes))

    task_path = _case_file(scenario_path, scenario.get("task"), "scenario.task")
    task_bytes = task_path.read_bytes()
    task_payload = _mapping(yaml.safe_load(task_bytes.decode("utf-8")), "task")

    if observation.observation_id not in world_state.observation_refs:
        raise GT25BuildError("world_state must include the position Observation")
    return observation, observation_bytes, world_state, world_state_bytes, task_payload, task_bytes


def _build_discrepancy(
    scenario: Mapping[str, object],
    observation: Observation,
    observation_bytes: bytes,
    world_state: WorldState,
    task_payload: Mapping[str, object],
    task_bytes: bytes,
) -> tuple[DiscrepancyReport, bytes]:
    config = _mapping(scenario.get("discrepancy"), "scenario.discrepancy")
    task_id = _string(_mapping(task_payload.get("geotask"), "task.geotask").get("id"), "task.geotask.id")
    payload = {
        "discrepancy_report": {
            "schema_id": "https://stpku.github.io/GeoTask/schemas/geotask-discrepancy-report-v0.1.schema.json",
            "schema_version": "0.1",
            "report_id": _string(config.get("report_id"), "scenario.discrepancy.report_id"),
            "recorded_at": _string(config.get("recorded_at"), "scenario.discrepancy.recorded_at"),
            "state": "confirmed",
            "severity": "high",
            "reason": "The latest UAV position is 130 metres, so the two prior UAV-dependent safety distances are stale while fixed-facility spacing and battery remain reusable.",
            "world_state": {
                "world_state_id": world_state.world_state_id,
                "revision": world_state.revision,
                "as_of": world_state.as_of,
                "semantic_fingerprint": world_state.semantic_fingerprint(),
            },
            "observation_refs": [observation.observation_id],
            "evidence_refs": [
                observation.source.reference,
                "task:fictional/gt25/corridor-safety-distance-recompute",
            ],
            "artifact_refs": [
                {
                    "ref_id": "observation-position-gt25",
                    "artifact_id": "geotask.observation",
                    "schema_version": "0.1",
                    "instance_id": observation.observation_id,
                    "content_sha256": _sha256(observation_bytes),
                },
                {
                    "ref_id": "task-gt25",
                    "artifact_id": "geotask.document",
                    "schema_version": "1.0",
                    "instance_id": task_id,
                    "content_sha256": _sha256(task_bytes),
                },
            ],
            "discrepancies": [
                {
                    "id": _string(config.get("finding_id"), "scenario.discrepancy.finding_id"),
                    "kind": "stale_claim",
                    "state": "confirmed",
                    "severity": "high",
                    "subject_kind": "relation",
                    "subject_path": "/relations/uav-alpha-crane-distance/value",
                    "summary": "The UAV-to-crane and UAV-to-tower distances still reflect the earlier 100-metre position.",
                    "reason": "The current position claim is 130 metres but the stored derived distances remain 50 and 160 metres.",
                    "basis_refs": ["observation-position-gt25", "task-gt25"],
                    "observation_refs": [observation.observation_id],
                    "evidence_refs": [
                        observation.source.reference,
                        "task:fictional/gt25/corridor-safety-distance-recompute",
                    ],
                    "observed": 50,
                    "impact": {
                        "state": "confirmed",
                        "reason": "Only the two UAV-dependent safety distances and their downstream corridor-safety conclusion require recompute and recheck.",
                        "affected_paths": [
                            "/relations/uav-alpha-crane-distance/value",
                            "/relations/uav-alpha-tower-distance/value",
                        ],
                        "affected_assertion_refs": [
                            "uav_crane_clearance",
                            "uav_tower_clearance",
                        ],
                        "affected_output_refs": ["corridor_safety_summary"],
                        "affected_action_refs": ["continue_corridor_inspection"],
                    },
                    "correction_scope": {
                        "state": "allowed",
                        "reason": "Recompute only UAV-dependent distances; preserve fixed-facility spacing and current battery state.",
                        "mutable_paths": [
                            "/relations/uav-alpha-crane-distance/value",
                            "/relations/uav-alpha-tower-distance/value",
                        ],
                        "immutable_paths": [
                            "/relations/crane-tower-distance/value",
                            "/objects/uav-alpha/attributes/battery_percent/value",
                        ],
                    },
                }
            ],
        }
    }
    report = load_discrepancy_report(payload)
    validate_discrepancy_report_bindings(
        report,
        world_state,
        {
            "observation-position-gt25": observation_bytes,
            "task-gt25": task_bytes,
        },
    )
    return report, _pretty_bytes(report.to_dict())


def _build_correction(
    scenario: Mapping[str, object],
    observation: Observation,
    world_state: WorldState,
    world_state_bytes: bytes,
    task_payload: Mapping[str, object],
    task_bytes: bytes,
    report: DiscrepancyReport,
    report_bytes: bytes,
) -> tuple[CorrectionRequest, bytes]:
    config = _mapping(scenario.get("correction"), "scenario.correction")
    task_id = _string(_mapping(task_payload.get("geotask"), "task.geotask").get("id"), "task.geotask.id")
    payload = {
        "correction_request": {
            "schema_id": "https://stpku.github.io/GeoTask/schemas/geotask-correction-request-v0.1.schema.json",
            "schema_version": "0.1",
            "request_id": _string(config.get("request_id"), "scenario.correction.request_id"),
            "created_at": _string(config.get("created_at"), "scenario.correction.created_at"),
            "state": "required",
            "reason": "Derive only the two UAV-dependent corridor distances and keep unrelated results unchanged until a successor state and safety recheck are complete.",
            "base_world_state": {
                "ref_id": "base-world-state-gt25",
                "artifact_id": "geotask.world-state",
                "schema_version": "0.1",
                "world_state_id": world_state.world_state_id,
                "revision": world_state.revision,
                "as_of": world_state.as_of,
                "semantic_fingerprint": world_state.semantic_fingerprint(),
                "content_sha256": _sha256(world_state_bytes),
            },
            "discrepancy_report_refs": [
                {
                    "ref_id": "discrepancy-gt25",
                    "artifact_id": "geotask.discrepancy-report",
                    "schema_version": "0.1",
                    "instance_id": report.report_id,
                    "content_sha256": _sha256(report_bytes),
                }
            ],
            "supporting_artifact_refs": [
                {
                    "ref_id": "task-gt25",
                    "artifact_id": "geotask.document",
                    "schema_version": "1.0",
                    "instance_id": task_id,
                    "content_sha256": _sha256(task_bytes),
                }
            ],
            "observation_refs": [observation.observation_id],
            "evidence_refs": [
                observation.source.reference,
                "task:fictional/gt25/corridor-safety-distance-recompute",
            ],
            "discrepancy_refs": [
                {
                    "id": "stale-distance-finding",
                    "report_ref": "discrepancy-gt25",
                    "discrepancy_id": "uav-dependent-distances-stale",
                }
            ],
            "changes": [
                {
                    "id": "recompute-uav-crane-distance",
                    "discrepancy_ref": "stale-distance-finding",
                    "subject_kind": "relation",
                    "target_path": "/relations/uav-alpha-crane-distance/value",
                    "operation": "recompute",
                    "reason": "Subtract the current UAV corridor position from the fixed crane position.",
                    "basis_refs": ["discrepancy-gt25", "task-gt25"],
                    "observation_refs": [observation.observation_id],
                    "evidence_refs": [observation.source.reference],
                    "input_fields": [
                        "obstacle_position",
                        "uav_position",
                        "calculation_method",
                        "verified_at",
                    ],
                    "acceptance_criterion_refs": [
                        "uav-crane-distance-recomputed",
                        "successor-world-state-valid",
                    ],
                    "before": 50,
                },
                {
                    "id": "recompute-uav-tower-distance",
                    "discrepancy_ref": "stale-distance-finding",
                    "subject_kind": "relation",
                    "target_path": "/relations/uav-alpha-tower-distance/value",
                    "operation": "recompute",
                    "reason": "Subtract the current UAV corridor position from the fixed tower position.",
                    "basis_refs": ["discrepancy-gt25", "task-gt25"],
                    "observation_refs": [observation.observation_id],
                    "evidence_refs": [observation.source.reference],
                    "input_fields": [
                        "obstacle_position",
                        "uav_position",
                        "calculation_method",
                        "verified_at",
                    ],
                    "acceptance_criterion_refs": [
                        "uav-tower-distance-recomputed",
                        "successor-world-state-valid",
                    ],
                    "before": 160,
                },
            ],
            "review_requirements": [],
            "acceptance_criteria": [
                {
                    "id": "uav-crane-distance-recomputed",
                    "kind": "path_recomputed",
                    "reason": "The successor state must contain the derived 20-metre UAV-to-crane distance.",
                    "target_path": "/relations/uav-alpha-crane-distance/value",
                    "output_refs": [],
                },
                {
                    "id": "uav-tower-distance-recomputed",
                    "kind": "path_recomputed",
                    "reason": "The successor state must contain the derived 130-metre UAV-to-tower distance.",
                    "target_path": "/relations/uav-alpha-tower-distance/value",
                    "output_refs": [],
                },
                {
                    "id": "successor-world-state-valid",
                    "kind": "artifact_valid",
                    "reason": "The successor snapshot must pass the World State validator and preserve immutable paths.",
                    "artifact_id": "geotask.world-state",
                    "output_refs": [],
                },
                {
                    "id": "stale-distance-discrepancy-resolved",
                    "kind": "discrepancy_resolved",
                    "reason": "The successor state and affected results must no longer reuse the stale 50- and 160-metre distances as current truth.",
                    "discrepancy_ref": "stale-distance-finding",
                    "output_refs": [],
                },
                {
                    "id": "corridor-safety-rechecked",
                    "kind": "recheck_completed",
                    "reason": "The corridor-safety output must be reevaluated before release.",
                    "output_refs": ["corridor_safety_summary"],
                },
            ],
            "output_contract": {
                "artifact_id": "geotask.world-state",
                "schema_version": "0.1",
                "world_state_id": world_state.world_state_id,
                "minimum_revision": 3,
                "preserve_immutable_paths": True,
                "require_semantic_fingerprint": True,
            },
            "blocked_outputs": ["corridor_safety_summary"],
            "blocked_actions": ["continue_corridor_inspection"],
            "resume_when": "successor_world_state_valid == true and corridor_safety_rechecked == true",
            "next_action": "materialize_successor_state",
        }
    }
    request = load_correction_request(payload)
    validate_correction_request_bindings(
        request,
        world_state,
        {"discrepancy-gt25": report},
        {
            "base-world-state-gt25": world_state_bytes,
            "discrepancy-gt25": report_bytes,
            "task-gt25": task_bytes,
        },
    )
    return request, _pretty_bytes(request.to_dict())


def _build_derivation(
    scenario: Mapping[str, object],
    observation: Observation,
    observation_bytes: bytes,
    world_state: WorldState,
    world_state_bytes: bytes,
    task_payload: Mapping[str, object],
    task_bytes: bytes,
    request: CorrectionRequest,
    request_bytes: bytes,
) -> tuple[RecomputeDerivationResult, bytes]:
    config = _mapping(scenario.get("derivation"), "scenario.derivation")
    task_id = _string(_mapping(task_payload.get("geotask"), "task.geotask").get("id"), "task.geotask.id")
    verified_at = _string(config.get("verified_at"), "scenario.derivation.verified_at")

    def item(
        *,
        identifier: str,
        change_id: str,
        target_path: str,
        obstacle_pointer: str,
        obstacle_value: int,
        result: int,
    ) -> dict[str, object]:
        return {
            "id": identifier,
            "change_id": change_id,
            "target_path": target_path,
            "state": "completed",
            "method": "subtract",
            "input_refs": ["obstacle_position", "uav_position"],
            "inputs": [
                {
                    "name": "obstacle_position",
                    "kind": "artifact_path",
                    "source_ref": "task-gt25",
                    "pointer": obstacle_pointer,
                    "value": obstacle_value,
                },
                {
                    "name": "uav_position",
                    "kind": "artifact_path",
                    "source_ref": "observation-position-gt25",
                    "pointer": "/observation/claims/0/value",
                    "value": 130,
                },
                {
                    "name": "calculation_method",
                    "kind": "literal",
                    "value": "subtract",
                },
                {
                    "name": "verified_at",
                    "kind": "literal",
                    "value": verified_at,
                },
            ],
            "result": result,
            "reason": "Apply the allowlisted subtract method to exact source values.",
            "basis_refs": [
                "correction-gt25",
                "observation-position-gt25",
                "task-gt25",
            ],
        }

    payload = {
        "recompute_derivation_result": {
            "schema_id": "https://stpku.github.io/GeoTask/schemas/geotask-recompute-derivation-result-v0.1.schema.json",
            "schema_version": "0.1",
            "derivation_id": _string(config.get("derivation_id"), "scenario.derivation.derivation_id"),
            "created_at": _string(config.get("created_at"), "scenario.derivation.created_at"),
            "state": "completed",
            "reason": "Derive exactly the two UAV-dependent distances from the position Observation and fixed obstacle coordinates.",
            "base_world_state": {
                "ref_id": "base-world-state-gt25",
                "artifact_id": "geotask.world-state",
                "schema_version": "0.1",
                "world_state_id": world_state.world_state_id,
                "revision": world_state.revision,
                "as_of": world_state.as_of,
                "semantic_fingerprint": world_state.semantic_fingerprint(),
                "content_sha256": _sha256(world_state_bytes),
            },
            "correction_request_ref": {
                "ref_id": "correction-gt25",
                "artifact_id": "geotask.correction-request",
                "schema_version": "0.1",
                "instance_id": request.request_id,
                "content_sha256": _sha256(request_bytes),
            },
            "source_artifact_refs": [
                {
                    "ref_id": "observation-position-gt25",
                    "artifact_id": "geotask.observation",
                    "schema_version": "0.1",
                    "instance_id": observation.observation_id,
                    "content_sha256": _sha256(observation_bytes),
                },
                {
                    "ref_id": "task-gt25",
                    "artifact_id": "geotask.document",
                    "schema_version": "1.0",
                    "instance_id": task_id,
                    "content_sha256": _sha256(task_bytes),
                },
            ],
            "derivations": [
                item(
                    identifier="derive-uav-crane-distance",
                    change_id="recompute-uav-crane-distance",
                    target_path="/relations/uav-alpha-crane-distance/value",
                    obstacle_pointer="/objects/crane/coordinates/0",
                    obstacle_value=150,
                    result=20,
                ),
                item(
                    identifier="derive-uav-tower-distance",
                    change_id="recompute-uav-tower-distance",
                    target_path="/relations/uav-alpha-tower-distance/value",
                    obstacle_pointer="/objects/communication_tower/coordinates/0",
                    obstacle_value=260,
                    result=130,
                ),
            ],
            "recompute_values": [
                {"change_id": "recompute-uav-crane-distance", "value": 20},
                {"change_id": "recompute-uav-tower-distance", "value": 130},
            ],
            "next_action": "materialize_successor_state",
            "successor_materialized": False,
            "reevaluation_executed": False,
            "outputs_released": False,
            "external_truth_verified": False,
            "action_authorized": False,
            "action_executed": False,
        }
    }
    result = load_recompute_derivation_result(payload)
    validate_recompute_derivation_bindings(
        result,
        world_state,
        request,
        {
            "observation-position-gt25": json.loads(observation_bytes),
            "task-gt25": task_payload,
        },
        {
            "base-world-state-gt25": world_state_bytes,
            "correction-gt25": request_bytes,
            "observation-position-gt25": observation_bytes,
            "task-gt25": task_bytes,
        },
    )
    evaluate_recompute_derivations(result)
    return result, _pretty_bytes(result.to_dict())


def _validate_scope(
    scenario: Mapping[str, object],
    world_state: WorldState,
    request: CorrectionRequest,
    result: RecomputeDerivationResult,
) -> None:
    scope = _mapping(scenario.get("declared_scope"), "scenario.declared_scope")
    recompute_paths = {
        _string(item, f"scenario.declared_scope.recompute_paths[{index}]")
        for index, item in enumerate(_sequence(scope.get("recompute_paths"), "scenario.declared_scope.recompute_paths"))
    }
    reuse_paths = {
        _string(item, f"scenario.declared_scope.reuse_paths[{index}]")
        for index, item in enumerate(_sequence(scope.get("reuse_paths"), "scenario.declared_scope.reuse_paths"))
    }
    actual_recompute = {
        item.target_path for item in request.changes if item.operation == "recompute"
    }
    if recompute_paths != actual_recompute:
        raise GT25BuildError(
            f"declared recompute scope mismatch: missing={sorted(recompute_paths - actual_recompute)}, extra={sorted(actual_recompute - recompute_paths)}"
        )
    if recompute_paths & reuse_paths:
        raise GT25BuildError("recompute and reuse scopes must be disjoint")
    if {item.target_path for item in result.derivations} != recompute_paths:
        raise GT25BuildError("derivations must cover the declared recompute paths exactly")
    expected_reuse = {
        "/relations/crane-tower-distance/value": 110,
        "/objects/uav-alpha/attributes/battery_percent/value": 48,
    }
    if reuse_paths != set(expected_reuse):
        raise GT25BuildError("declared reuse scope must exactly match the fixed reusable results")
    for path, expected in expected_reuse.items():
        if _resolve_world_state_value(world_state, path) != expected:
            raise GT25BuildError(f"{path}: reusable value changed")


def build_gt25_bounded_recompute(
    scenario_path: str | Path,
) -> tuple[
    WorldState,
    DiscrepancyReport,
    CorrectionRequest,
    RecomputeDerivationResult,
    bytes,
    bytes,
    bytes,
]:
    path = Path(scenario_path).resolve()
    root = _mapping(json.loads(path.read_text(encoding="utf-8")), "root")
    scenario = _mapping(root.get("scenario"), "scenario")
    observation, observation_bytes, world_state, world_state_bytes, task_payload, task_bytes = _load_inputs(path, scenario)
    report, report_bytes = _build_discrepancy(
        scenario, observation, observation_bytes, world_state, task_payload, task_bytes
    )
    request, request_bytes = _build_correction(
        scenario,
        observation,
        world_state,
        world_state_bytes,
        task_payload,
        task_bytes,
        report,
        report_bytes,
    )
    result, result_bytes = _build_derivation(
        scenario,
        observation,
        observation_bytes,
        world_state,
        world_state_bytes,
        task_payload,
        task_bytes,
        request,
        request_bytes,
    )
    _validate_scope(scenario, world_state, request, result)
    return world_state, report, request, result, report_bytes, request_bytes, result_bytes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "scenario",
        nargs="?",
        default=str(Path(__file__).with_name("gt25_corridor_safety_recompute.json")),
    )
    parser.add_argument("--discrepancy-output")
    parser.add_argument("--correction-output")
    parser.add_argument("--derivation-output")
    args = parser.parse_args()

    _, _, _, result, report_bytes, request_bytes, result_bytes = build_gt25_bounded_recompute(args.scenario)
    wrote = False
    if args.discrepancy_output:
        Path(args.discrepancy_output).write_bytes(report_bytes)
        wrote = True
    if args.correction_output:
        Path(args.correction_output).write_bytes(request_bytes)
        wrote = True
    if args.derivation_output:
        Path(args.derivation_output).write_bytes(result_bytes)
        wrote = True
    if not wrote:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
