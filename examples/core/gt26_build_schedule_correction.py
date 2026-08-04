#!/usr/bin/env python3
"""Build the fictional GT26 bounded schedule-correction artifacts.

The case validates one caller-declared mutable path and four immutable station
attributes. It does not fetch or compare real sources, apply the correction,
materialize a successor World State, rerun the mission check, release outputs,
verify external truth, authorize action, or execute action.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence

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
from geotask_core.v1.world_state import WorldState, load_world_state


class GT26BuildError(ValueError):
    """Raised when the GT26 bounded correction declaration is inconsistent."""


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise GT26BuildError(f"{path}: must be an object")
    return value


def _sequence(value: object, path: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise GT26BuildError(f"{path}: must be an array")
    return value


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GT26BuildError(f"{path}: must be a non-empty string")
    return value


def _pretty_bytes(payload: Mapping[str, object]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _case_path(scenario_path: Path, filename: object, path: str) -> Path:
    base = scenario_path.parent.resolve()
    candidate = (base / _string(filename, path)).resolve()
    if candidate.parent != base:
        raise GT26BuildError(f"{path}: must stay in {base}")
    return candidate


def _attribute_value(world_state: WorldState, object_id: str, attribute_name: str) -> object:
    obj = next((item for item in world_state.objects if item.id == object_id), None)
    if obj is None:
        raise GT26BuildError(f"unknown object {object_id!r}")
    attribute = next((item for item in obj.attributes if item.name == attribute_name), None)
    if attribute is None:
        raise GT26BuildError(f"unknown attribute {object_id}.{attribute_name}")
    return attribute.value


def _load_inputs(
    scenario_path: Path,
    scenario: Mapping[str, object],
) -> tuple[Observation, bytes, WorldState, bytes]:
    observation_path = _case_path(
        scenario_path, scenario.get("observation"), "scenario.observation"
    )
    observation_bytes = observation_path.read_bytes()
    observation = load_observation(json.loads(observation_bytes))

    world_path = _case_path(
        scenario_path, scenario.get("world_state"), "scenario.world_state"
    )
    world_bytes = world_path.read_bytes()
    world_state = load_world_state(json.loads(world_bytes))
    return observation, observation_bytes, world_state, world_bytes


def _build_report(
    scenario: Mapping[str, object],
    observation: Observation,
    observation_bytes: bytes,
    world_state: WorldState,
) -> tuple[DiscrepancyReport, bytes]:
    config = _mapping(scenario.get("discrepancy"), "scenario.discrepancy")
    expected = _mapping(scenario.get("expected"), "scenario.expected")
    scope = _mapping(scenario.get("declared_scope"), "scenario.declared_scope")
    old_schedule = expected.get("old_schedule")
    new_schedule = expected.get("new_schedule")
    mutable_paths = list(_sequence(scope.get("mutable_paths"), "scenario.declared_scope.mutable_paths"))
    immutable_paths = list(_sequence(scope.get("immutable_paths"), "scenario.declared_scope.immutable_paths"))

    payload = {
        "discrepancy_report": {
            "schema_id": "https://stpku.github.io/GeoTask/schemas/geotask-discrepancy-report-v0.1.schema.json",
            "schema_version": "0.1",
            "report_id": _string(config.get("report_id"), "scenario.discrepancy.report_id"),
            "recorded_at": _string(config.get("recorded_at"), "scenario.discrepancy.recorded_at"),
            "state": "confirmed",
            "severity": "high",
            "reason": "A new fictional notice narrows the station schedule from 08:00-22:00 to 09:00-18:00, so the 20:30 mission availability result is stale while unrelated station attributes remain reusable.",
            "world_state": {
                "world_state_id": world_state.world_state_id,
                "revision": world_state.revision,
                "as_of": world_state.as_of,
                "semantic_fingerprint": world_state.semantic_fingerprint(),
            },
            "observation_refs": [observation.observation_id],
            "evidence_refs": [observation.source.reference],
            "artifact_refs": [
                {
                    "ref_id": "schedule-notice-gt26",
                    "artifact_id": "geotask.observation",
                    "schema_version": "0.1",
                    "instance_id": observation.observation_id,
                    "content_sha256": _sha256(observation_bytes),
                }
            ],
            "discrepancies": [
                {
                    "id": _string(config.get("finding_id"), "scenario.discrepancy.finding_id"),
                    "kind": "value_mismatch",
                    "state": "confirmed",
                    "severity": "high",
                    "subject_kind": "attribute",
                    "subject_path": "/objects/flight-service-station-east/attributes/operating_schedule/value",
                    "summary": "The station operating schedule stored in the current state no longer matches the new fictional notice.",
                    "reason": "The current state ends service at 22:00, while the new notice ends service at 18:00 from 2026-08-04 18:00 onward.",
                    "basis_refs": ["schedule-notice-gt26"],
                    "observation_refs": [observation.observation_id],
                    "evidence_refs": [observation.source.reference],
                    "expected": new_schedule,
                    "observed": old_schedule,
                    "impact": {
                        "state": "confirmed",
                        "reason": "Only the schedule path and the derived 20:30 mission availability conclusion require correction or recheck.",
                        "affected_paths": [
                            "/objects/flight-service-station-east/attributes/operating_schedule/value",
                            "/relations/mission-27-station-service-availability/value",
                        ],
                        "affected_assertion_refs": ["mission_27_service_time_within_schedule"],
                        "affected_output_refs": ["mission_27_service_availability"],
                        "affected_action_refs": ["dispatch_mission_27"],
                    },
                    "correction_scope": {
                        "state": "allowed",
                        "reason": "Replace only the operating schedule and preserve station identity, location, radio frequency, service types, and contact channel.",
                        "mutable_paths": mutable_paths,
                        "immutable_paths": immutable_paths,
                    },
                }
            ],
        }
    }
    report = load_discrepancy_report(payload)
    validate_discrepancy_report_bindings(
        report,
        world_state,
        {"schedule-notice-gt26": observation_bytes},
    )
    return report, _pretty_bytes(report.to_dict())


def _build_request(
    scenario: Mapping[str, object],
    observation: Observation,
    world_state: WorldState,
    world_bytes: bytes,
    report: DiscrepancyReport,
    report_bytes: bytes,
) -> tuple[CorrectionRequest, bytes]:
    config = _mapping(scenario.get("correction"), "scenario.correction")
    scope = _mapping(scenario.get("declared_scope"), "scenario.declared_scope")
    expected = _mapping(scenario.get("expected"), "scenario.expected")
    old_schedule = expected.get("old_schedule")
    new_schedule = expected.get("new_schedule")
    mutable_path = _string(
        _sequence(scope.get("mutable_paths"), "scenario.declared_scope.mutable_paths")[0],
        "scenario.declared_scope.mutable_paths[0]",
    )

    payload = {
        "correction_request": {
            "schema_id": "https://stpku.github.io/GeoTask/schemas/geotask-correction-request-v0.1.schema.json",
            "schema_version": "0.1",
            "request_id": _string(config.get("request_id"), "scenario.correction.request_id"),
            "created_at": _string(config.get("created_at"), "scenario.correction.created_at"),
            "state": "required",
            "reason": "Replace only the stale operating schedule, preserve four unrelated station attributes, and keep mission availability blocked until a successor state is materialized and the 20:30 check is rerun.",
            "base_world_state": {
                "ref_id": "base-world-state-gt26",
                "artifact_id": "geotask.world-state",
                "schema_version": "0.1",
                "world_state_id": world_state.world_state_id,
                "revision": world_state.revision,
                "as_of": world_state.as_of,
                "semantic_fingerprint": world_state.semantic_fingerprint(),
                "content_sha256": _sha256(world_bytes),
            },
            "discrepancy_report_refs": [
                {
                    "ref_id": "discrepancy-gt26",
                    "artifact_id": "geotask.discrepancy-report",
                    "schema_version": "0.1",
                    "instance_id": report.report_id,
                    "content_sha256": _sha256(report_bytes),
                }
            ],
            "supporting_artifact_refs": [],
            "observation_refs": [observation.observation_id],
            "evidence_refs": [observation.source.reference],
            "discrepancy_refs": [
                {
                    "id": "schedule-mismatch-finding",
                    "report_ref": "discrepancy-gt26",
                    "discrepancy_id": "station-operating-schedule-mismatch",
                }
            ],
            "changes": [
                {
                    "id": "replace-station-operating-schedule",
                    "discrepancy_ref": "schedule-mismatch-finding",
                    "subject_kind": "attribute",
                    "target_path": mutable_path,
                    "operation": "replace",
                    "reason": "Replace the stale schedule with the exact schedule value declared by the bound notice Observation.",
                    "basis_refs": ["discrepancy-gt26"],
                    "observation_refs": [observation.observation_id],
                    "evidence_refs": [observation.source.reference],
                    "input_fields": [],
                    "acceptance_criterion_refs": [
                        "schedule-path-equals-notice",
                        "successor-world-state-valid",
                    ],
                    "before": old_schedule,
                    "after": new_schedule,
                }
            ],
            "review_requirements": [],
            "acceptance_criteria": [
                {
                    "id": "schedule-path-equals-notice",
                    "kind": "path_equals",
                    "reason": "The successor state must contain the exact 09:00-18:00 schedule from the notice.",
                    "target_path": mutable_path,
                    "expected": new_schedule,
                    "output_refs": [],
                },
                {
                    "id": "schedule-discrepancy-resolved",
                    "kind": "discrepancy_resolved",
                    "reason": "The successor state must no longer retain the 08:00-22:00 schedule as current truth.",
                    "discrepancy_ref": "schedule-mismatch-finding",
                    "output_refs": [],
                },
                {
                    "id": "successor-world-state-valid",
                    "kind": "artifact_valid",
                    "reason": "The successor snapshot must pass the registered World State validator and preserve immutable paths.",
                    "artifact_id": "geotask.world-state",
                    "output_refs": [],
                },
                {
                    "id": "mission-availability-rechecked",
                    "kind": "recheck_completed",
                    "reason": "The 20:30 mission service-availability result must be rerun before release.",
                    "output_refs": ["mission_27_service_availability"],
                },
            ],
            "output_contract": {
                "artifact_id": "geotask.world-state",
                "schema_version": "0.1",
                "world_state_id": world_state.world_state_id,
                "minimum_revision": 5,
                "preserve_immutable_paths": True,
                "require_semantic_fingerprint": True
            },
            "blocked_outputs": list(_sequence(scope.get("blocked_outputs"), "scenario.declared_scope.blocked_outputs")),
            "blocked_actions": list(_sequence(scope.get("blocked_actions"), "scenario.declared_scope.blocked_actions")),
            "resume_when": "successor_world_state_valid == true and mission_27_service_availability_rechecked == true",
            "next_action": "materialize_successor_state",
        }
    }
    request = load_correction_request(payload)
    validate_correction_request_bindings(
        request,
        world_state,
        {"discrepancy-gt26": report},
        {
            "base-world-state-gt26": world_bytes,
            "discrepancy-gt26": report_bytes,
        },
    )
    return request, _pretty_bytes(request.to_dict())


def _validate_case_scope(
    scenario: Mapping[str, object],
    observation: Observation,
    world_state: WorldState,
    report: DiscrepancyReport,
    request: CorrectionRequest,
) -> None:
    scope = _mapping(scenario.get("declared_scope"), "scenario.declared_scope")
    expected = _mapping(scenario.get("expected"), "scenario.expected")
    mutable = {
        _string(item, f"mutable_paths[{index}]")
        for index, item in enumerate(_sequence(scope.get("mutable_paths"), "mutable_paths"))
    }
    immutable = {
        _string(item, f"immutable_paths[{index}]")
        for index, item in enumerate(_sequence(scope.get("immutable_paths"), "immutable_paths"))
    }
    if len(mutable) != 1:
        raise GT26BuildError("GT26 requires exactly one mutable schedule path")
    if mutable & immutable:
        raise GT26BuildError("mutable and immutable paths must be disjoint")
    finding = report.discrepancies[0]
    if set(finding.correction_scope.mutable_paths) != mutable:
        raise GT26BuildError("report mutable scope does not match scenario")
    if set(finding.correction_scope.immutable_paths) != immutable:
        raise GT26BuildError("report immutable scope does not match scenario")
    change = request.changes[0]
    if change.target_path not in mutable or change.operation != "replace":
        raise GT26BuildError("correction must replace the single mutable schedule path")
    claim_value = observation.claims[0].value
    if change.after != claim_value or change.after != expected.get("new_schedule"):
        raise GT26BuildError("correction after value must exactly match the notice claim")
    if change.before != expected.get("old_schedule"):
        raise GT26BuildError("correction before value must match the stored schedule")
    preserved = _mapping(expected.get("preserved_values"), "expected.preserved_values")
    for name, value in preserved.items():
        if _attribute_value(world_state, "flight-service-station-east", name) != value:
            raise GT26BuildError(f"preserved attribute {name!r} changed")
    if set(request.blocked_outputs) != set(scope.get("blocked_outputs", [])):
        raise GT26BuildError("blocked outputs mismatch")
    if set(request.blocked_actions) != set(scope.get("blocked_actions", [])):
        raise GT26BuildError("blocked actions mismatch")


def build_gt26_schedule_correction(
    scenario_path: str | Path,
) -> tuple[WorldState, DiscrepancyReport, CorrectionRequest, bytes, bytes]:
    path = Path(scenario_path).resolve()
    root = _mapping(json.loads(path.read_text(encoding="utf-8")), "root")
    scenario = _mapping(root.get("scenario"), "scenario")
    scope = _mapping(scenario.get("declared_scope"), "scenario.declared_scope")
    mutable_paths = _sequence(
        scope.get("mutable_paths"), "scenario.declared_scope.mutable_paths"
    )
    immutable_paths = _sequence(
        scope.get("immutable_paths"), "scenario.declared_scope.immutable_paths"
    )
    if len(mutable_paths) != 1:
        raise GT26BuildError("GT26 requires exactly one mutable schedule path")
    if set(mutable_paths) & set(immutable_paths):
        raise GT26BuildError("mutable and immutable paths must be disjoint")
    observation, observation_bytes, world_state, world_bytes = _load_inputs(path, scenario)
    report, report_bytes = _build_report(
        scenario, observation, observation_bytes, world_state
    )
    request, request_bytes = _build_request(
        scenario, observation, world_state, world_bytes, report, report_bytes
    )
    _validate_case_scope(scenario, observation, world_state, report, request)
    return world_state, report, request, report_bytes, request_bytes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "scenario",
        nargs="?",
        default=str(Path(__file__).with_name("gt26_flight_service_station_schedule_correction.json")),
    )
    parser.add_argument("--discrepancy-output")
    parser.add_argument("--correction-output")
    args = parser.parse_args()
    _, _, request, report_bytes, request_bytes = build_gt26_schedule_correction(args.scenario)
    wrote = False
    if args.discrepancy_output:
        Path(args.discrepancy_output).write_bytes(report_bytes)
        wrote = True
    if args.correction_output:
        Path(args.correction_output).write_bytes(request_bytes)
        wrote = True
    if not wrote:
        print(json.dumps(request.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
