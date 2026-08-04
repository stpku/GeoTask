#!/usr/bin/env python3
"""Build the fictional GT27 bounded weather reevaluation artifact bundle.

The case uses caller-declared region/time dependencies to reevaluate two of four
missions after one wind-speed Observation. It does not discover dependencies,
fetch weather, run a generic weather operator, prove excluded missions permanently
safe, release production outputs, authorize actions, or execute actions.
"""

from __future__ import annotations

import argparse
import copy
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
from geotask_core.v1.impact_graph import (
    ImpactGraph,
    load_impact_graph,
    validate_impact_graph_bindings,
)
from geotask_core.v1.incremental_reevaluation_result import (
    IncrementalReevaluationResult,
    load_incremental_reevaluation_result,
    validate_incremental_reevaluation_result_bindings,
)
from geotask_core.v1.observation import Observation, load_observation
from geotask_core.v1.result import GeotaskResult
from geotask_core.v1.world_state import WorldState, load_world_state


class GT27BuildError(ValueError):
    """Raised when the GT27 scenario declaration is inconsistent."""


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise GT27BuildError(f"{path}: must be an object")
    return value


def _sequence(value: object, path: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise GT27BuildError(f"{path}: must be an array")
    return value


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GT27BuildError(f"{path}: must be a non-empty string")
    return value


def _integer(value: object, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise GT27BuildError(f"{path}: must be an integer")
    return value


def _boolean(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise GT27BuildError(f"{path}: must be a boolean")
    return value


def _pretty_bytes(payload: Mapping[str, object]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _case_path(scenario_path: Path, filename: object, path: str) -> Path:
    base = scenario_path.parent.resolve()
    candidate = (base / _string(filename, path)).resolve()
    if candidate.parent != base:
        raise GT27BuildError(f"{path}: must stay in {base}")
    return candidate


def _attribute_value(world_state: WorldState, object_id: str, attribute_name: str) -> object:
    world_object = next((item for item in world_state.objects if item.id == object_id), None)
    if world_object is None:
        raise GT27BuildError(f"unknown object {object_id!r}")
    attribute = next((item for item in world_object.attributes if item.name == attribute_name), None)
    if attribute is None:
        raise GT27BuildError(f"unknown attribute {object_id}.{attribute_name}")
    return attribute.value


def _relation_value(world_state: WorldState, relation_id: str) -> object:
    relation = next((item for item in world_state.relations if item.id == relation_id), None)
    if relation is None:
        raise GT27BuildError(f"unknown relation {relation_id!r}")
    return relation.value


def _mission_map(scenario: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    missions: dict[str, Mapping[str, object]] = {}
    for index, raw in enumerate(_sequence(scenario.get("missions"), "scenario.missions")):
        mission = _mapping(raw, f"scenario.missions[{index}]")
        mission_id = _string(mission.get("id"), f"scenario.missions[{index}].id")
        if mission_id in missions:
            raise GT27BuildError(f"scenario.missions[{index}].id: duplicates {mission_id!r}")
        missions[mission_id] = mission
    return missions


def _load_inputs(
    scenario_path: Path,
    scenario: Mapping[str, object],
) -> tuple[Observation, bytes, WorldState, bytes, dict[str, object]]:
    observation_path = _case_path(
        scenario_path, scenario.get("observation"), "scenario.observation"
    )
    observation_bytes = observation_path.read_bytes()
    observation = load_observation(json.loads(observation_bytes))

    base_path = _case_path(
        scenario_path, scenario.get("base_world_state"), "scenario.base_world_state"
    )
    base_bytes = base_path.read_bytes()
    base_payload = json.loads(base_bytes)
    base_world_state = load_world_state(base_payload)
    return observation, observation_bytes, base_world_state, base_bytes, base_payload


def _build_successor(
    scenario: Mapping[str, object],
    observation: Observation,
    base_payload: Mapping[str, object],
) -> tuple[WorldState, bytes]:
    payload = copy.deepcopy(base_payload)
    body = _mapping(payload.get("world_state"), "world_state")
    body["revision"] = 8
    body["as_of"] = "2026-08-04T14:00:05+08:00"
    body["materialized_at"] = "2026-08-04T14:00:08+08:00"
    body["observation_refs"] = [observation.observation_id]

    objects = _sequence(body.get("objects"), "world_state.objects")
    weather = next(
        (
            _mapping(item, "weather object")
            for item in objects
            if _mapping(item, "world_state object").get("id") == "weather-cell-east"
        ),
        None,
    )
    if weather is None:
        raise GT27BuildError("base state is missing weather-cell-east")
    attributes = _sequence(weather.get("attributes"), "weather-cell-east.attributes")
    wind = next(
        (
            _mapping(item, "wind attribute")
            for item in attributes
            if _mapping(item, "weather attribute").get("name") == "wind_speed_mps"
        ),
        None,
    )
    if wind is None:
        raise GT27BuildError("base state is missing wind_speed_mps")
    wind["value"] = 12

    relations = _sequence(body.get("relations"), "world_state.relations")
    for relation_id, value in (
        ("mission-a-weather-suitable", False),
        ("mission-d-weather-suitable", True),
    ):
        relation = next(
            (
                _mapping(item, "weather relation")
                for item in relations
                if _mapping(item, "world_state relation").get("id") == relation_id
            ),
            None,
        )
        if relation is None:
            raise GT27BuildError(f"base state is missing {relation_id!r}")
        relation["value"] = value

    successor = load_world_state(payload)
    return successor, _pretty_bytes(successor.to_dict())


def _build_discrepancy(
    scenario: Mapping[str, object],
    observation: Observation,
    observation_bytes: bytes,
    base_world_state: WorldState,
) -> tuple[DiscrepancyReport, bytes]:
    scope = _mapping(scenario.get("declared_scope"), "scenario.declared_scope")
    update = _mapping(scenario.get("weather_update"), "scenario.weather_update")
    payload = {
        "discrepancy_report": {
            "schema_id": "https://stpku.github.io/GeoTask/schemas/geotask-discrepancy-report-v0.1.schema.json",
            "schema_version": "0.1",
            "report_id": "gt27-weather-wind-speed-discrepancy",
            "recorded_at": "2026-08-04T14:00:05+08:00",
            "state": "confirmed",
            "severity": "high",
            "reason": "The east-zone wind speed changed from 6 to 12 metres per second, invalidating reuse of two mission-specific wind checks while two unrelated mission results remain reusable.",
            "world_state": {
                "world_state_id": base_world_state.world_state_id,
                "revision": base_world_state.revision,
                "as_of": base_world_state.as_of,
                "semantic_fingerprint": base_world_state.semantic_fingerprint(),
            },
            "observation_refs": [observation.observation_id],
            "evidence_refs": [observation.source.reference],
            "artifact_refs": [
                {
                    "ref_id": "weather-observation-gt27",
                    "artifact_id": "geotask.observation",
                    "schema_version": "0.1",
                    "instance_id": observation.observation_id,
                    "content_sha256": _sha256(observation_bytes),
                }
            ],
            "discrepancies": [
                {
                    "id": "east-wind-speed-value-mismatch",
                    "kind": "value_mismatch",
                    "state": "confirmed",
                    "severity": "high",
                    "subject_kind": "attribute",
                    "subject_path": "/objects/weather-cell-east/attributes/wind_speed_mps/value",
                    "summary": "The current east-zone wind value is stale relative to the new fictional sensor Observation.",
                    "reason": "The prior operating assumption was 6 m/s, while the 14:00 base snapshot has already absorbed the new 12 m/s Observation but still retains stale dependent mission results.",
                    "basis_refs": ["weather-observation-gt27"],
                    "observation_refs": [observation.observation_id],
                    "evidence_refs": [observation.source.reference],
                    "expected": update.get("old_wind_mps"),
                    "observed": update.get("new_wind_mps"),
                    "impact": {
                        "state": "confirmed",
                        "reason": "Only east-zone missions at or after the update time are declared affected; mission A and mission D require recheck.",
                        "affected_paths": [
                            "/relations/mission-a-weather-suitable/value",
                            "/relations/mission-d-weather-suitable/value",
                        ],
                        "affected_assertion_refs": [
                            "mission_a_wind_within_limit",
                            "mission_d_wind_within_limit",
                        ],
                        "affected_output_refs": [],
                        "affected_action_refs": [],
                    },
                    "correction_scope": {
                        "state": "allowed",
                        "reason": "Update the east wind value and recompute only mission A and mission D suitability; preserve mission B and mission C results.",
                        "mutable_paths": list(
                            _sequence(scope.get("mutable_paths"), "declared_scope.mutable_paths")
                        ),
                        "immutable_paths": list(
                            _sequence(scope.get("immutable_paths"), "declared_scope.immutable_paths")
                        ),
                    },
                }
            ],
        }
    }
    report = load_discrepancy_report(payload)
    validate_discrepancy_report_bindings(
        report,
        base_world_state,
        {"weather-observation-gt27": observation_bytes},
    )
    return report, _pretty_bytes(report.to_dict())


def _build_correction(
    scenario: Mapping[str, object],
    observation: Observation,
    base_world_state: WorldState,
    base_bytes: bytes,
    report: DiscrepancyReport,
    report_bytes: bytes,
) -> tuple[CorrectionRequest, bytes]:
    update = _mapping(scenario.get("weather_update"), "scenario.weather_update")
    payload = {
        "correction_request": {
            "schema_id": "https://stpku.github.io/GeoTask/schemas/geotask-correction-request-v0.1.schema.json",
            "schema_version": "0.1",
            "request_id": "gt27-weather-bounded-reevaluation-request",
            "created_at": "2026-08-04T14:00:06+08:00",
            "state": "required",
            "reason": "Materialize revision 8 with the updated east-zone wind value and recompute only mission A and mission D weather suitability.",
            "base_world_state": {
                "ref_id": "base-world-state-gt27",
                "artifact_id": "geotask.world-state",
                "schema_version": "0.1",
                "world_state_id": base_world_state.world_state_id,
                "revision": base_world_state.revision,
                "as_of": base_world_state.as_of,
                "semantic_fingerprint": base_world_state.semantic_fingerprint(),
                "content_sha256": _sha256(base_bytes),
            },
            "discrepancy_report_refs": [
                {
                    "ref_id": "discrepancy-weather-gt27",
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
                    "id": "wind-speed-mismatch",
                    "report_ref": "discrepancy-weather-gt27",
                    "discrepancy_id": "east-wind-speed-value-mismatch",
                }
            ],
            "changes": [
                {
                    "id": "recompute-east-wind-speed",
                    "discrepancy_ref": "wind-speed-mismatch",
                    "subject_kind": "attribute",
                    "target_path": "/objects/weather-cell-east/attributes/wind_speed_mps/value",
                    "operation": "recompute",
                    "reason": "Carry the already observed 12 m/s wind value into the successor snapshot before reevaluating dependent missions.",
                    "basis_refs": ["discrepancy-weather-gt27"],
                    "observation_refs": [observation.observation_id],
                    "evidence_refs": [observation.source.reference],
                    "input_fields": [
                        "observation_id",
                        "observed_at",
                        "wind_speed_mps",
                        "source_reference",
                    ],
                    "acceptance_criterion_refs": [
                        "wind-path-recomputed",
                        "successor-world-state-valid",
                    ],
                    "before": update.get("new_wind_mps"),
                },
                {
                    "id": "recompute-mission-a-wind-suitability",
                    "discrepancy_ref": "wind-speed-mismatch",
                    "subject_kind": "relation",
                    "target_path": "/relations/mission-a-weather-suitable/value",
                    "operation": "recompute",
                    "reason": "Mission A is in the east zone after 14:00 and its 10 m/s threshold depends on the updated wind value.",
                    "basis_refs": ["discrepancy-weather-gt27"],
                    "observation_refs": [observation.observation_id],
                    "evidence_refs": [observation.source.reference],
                    "input_fields": [
                        "region_code",
                        "planned_time",
                        "wind_speed_mps",
                        "max_wind_mps",
                    ],
                    "acceptance_criterion_refs": [
                        "mission-a-path-recomputed",
                        "affected-weather-outputs-rechecked",
                        "wind-discrepancy-resolved",
                        "successor-world-state-valid",
                    ],
                    "before": True,
                },
                {
                    "id": "recompute-mission-d-wind-suitability",
                    "discrepancy_ref": "wind-speed-mismatch",
                    "subject_kind": "relation",
                    "target_path": "/relations/mission-d-weather-suitable/value",
                    "operation": "recompute",
                    "reason": "Mission D is also in the east zone after 14:00, so it must be rerun even though 12 m/s remains within its 15 m/s threshold.",
                    "basis_refs": ["discrepancy-weather-gt27"],
                    "observation_refs": [observation.observation_id],
                    "evidence_refs": [observation.source.reference],
                    "input_fields": [
                        "region_code",
                        "planned_time",
                        "wind_speed_mps",
                        "max_wind_mps",
                    ],
                    "acceptance_criterion_refs": [
                        "mission-d-path-recomputed",
                        "affected-weather-outputs-rechecked",
                        "wind-discrepancy-resolved",
                        "successor-world-state-valid",
                    ],
                    "before": True,
                },
            ],
            "review_requirements": [],
            "acceptance_criteria": [
                {
                    "id": "wind-path-recomputed",
                    "kind": "path_recomputed",
                    "reason": "The successor state must carry the observed wind value through an explicit recompute change.",
                    "target_path": "/objects/weather-cell-east/attributes/wind_speed_mps/value",
                    "output_refs": [],
                },
                {
                    "id": "mission-a-path-recomputed",
                    "kind": "path_recomputed",
                    "reason": "Mission A wind suitability must be recomputed from the updated wind and its own threshold.",
                    "target_path": "/relations/mission-a-weather-suitable/value",
                    "output_refs": [],
                },
                {
                    "id": "mission-d-path-recomputed",
                    "kind": "path_recomputed",
                    "reason": "Mission D wind suitability must be recomputed even when the boolean result remains true.",
                    "target_path": "/relations/mission-d-weather-suitable/value",
                    "output_refs": [],
                },
                {
                    "id": "successor-world-state-valid",
                    "kind": "artifact_valid",
                    "reason": "The revision-8 successor snapshot must pass the registered World State validator.",
                    "artifact_id": "geotask.world-state",
                    "output_refs": [],
                },
                {
                    "id": "affected-weather-outputs-rechecked",
                    "kind": "recheck_completed",
                    "reason": "Both affected mission weather assessments must be rerun before their outputs are released.",
                    "output_refs": [
                        "mission_a_weather_assessment",
                        "mission_d_weather_assessment",
                    ],
                },
                {
                    "id": "wind-discrepancy-resolved",
                    "kind": "discrepancy_resolved",
                    "reason": "The successor state must no longer retain 6 m/s as the current east-zone wind value.",
                    "discrepancy_ref": "wind-speed-mismatch",
                    "output_refs": [],
                },
            ],
            "output_contract": {
                "artifact_id": "geotask.world-state",
                "schema_version": "0.1",
                "world_state_id": base_world_state.world_state_id,
                "minimum_revision": 8,
                "preserve_immutable_paths": True,
                "require_semantic_fingerprint": True,
            },
            "blocked_outputs": [
                "mission_a_weather_assessment",
                "mission_d_weather_assessment",
            ],
            "blocked_actions": [],
            "resume_when": "successor_world_state_valid == true and affected_weather_outputs_rechecked == true",
            "next_action": "materialize_successor_state",
        }
    }
    request = load_correction_request(payload)
    validate_correction_request_bindings(
        request,
        base_world_state,
        {"discrepancy-weather-gt27": report},
        {
            "base-world-state-gt27": base_bytes,
            "discrepancy-weather-gt27": report_bytes,
        },
    )
    return request, _pretty_bytes(request.to_dict())


def _build_graph(
    base_world_state: WorldState,
    base_bytes: bytes,
    report: DiscrepancyReport,
    report_bytes: bytes,
    request: CorrectionRequest,
    request_bytes: bytes,
) -> tuple[ImpactGraph, bytes]:
    payload = {
        "impact_graph": {
            "schema_id": "https://stpku.github.io/GeoTask/schemas/geotask-impact-graph-v0.1.schema.json",
            "schema_version": "0.1",
            "graph_id": "gt27-weather-mission-impact-graph",
            "recorded_at": "2026-08-04T14:00:07+08:00",
            "state": "blocked",
            "reason": "The declared impact scope links one wind discrepancy to three bounded changes, two mission assertion rechecks, and two blocked weather-assessment outputs, excluding the west-zone and pre-update missions.",
            "world_state": {
                "ref_id": "base-world-state-gt27",
                "artifact_id": "geotask.world-state",
                "schema_version": "0.1",
                "world_state_id": base_world_state.world_state_id,
                "revision": base_world_state.revision,
                "as_of": base_world_state.as_of,
                "semantic_fingerprint": base_world_state.semantic_fingerprint(),
                "content_sha256": _sha256(base_bytes),
            },
            "artifact_refs": [
                {
                    "ref_id": "correction-weather-gt27",
                    "artifact_id": "geotask.correction-request",
                    "schema_version": "0.1",
                    "instance_id": request.request_id,
                    "content_sha256": _sha256(request_bytes),
                },
                {
                    "ref_id": "discrepancy-weather-gt27",
                    "artifact_id": "geotask.discrepancy-report",
                    "schema_version": "0.1",
                    "instance_id": report.report_id,
                    "content_sha256": _sha256(report_bytes),
                },
            ],
            "entity_refs": [
                {
                    "id": "entity-wind-discrepancy",
                    "kind": "discrepancy",
                    "artifact_ref": "discrepancy-weather-gt27",
                    "entity_id": "east-wind-speed-value-mismatch",
                },
                {
                    "id": "entity-change-wind",
                    "kind": "correction_change",
                    "artifact_ref": "correction-weather-gt27",
                    "entity_id": "recompute-east-wind-speed",
                },
                {
                    "id": "entity-change-mission-a",
                    "kind": "correction_change",
                    "artifact_ref": "correction-weather-gt27",
                    "entity_id": "recompute-mission-a-wind-suitability",
                },
                {
                    "id": "entity-change-mission-d",
                    "kind": "correction_change",
                    "artifact_ref": "correction-weather-gt27",
                    "entity_id": "recompute-mission-d-wind-suitability",
                },
            ],
            "root_node_refs": ["node-wind-discrepancy"],
            "nodes": [
                {
                    "id": "node-wind-discrepancy",
                    "kind": "discrepancy",
                    "identity": "entity-wind-discrepancy",
                    "impact_state": "root",
                    "reason": "The confirmed east wind mismatch is the root of the declared scope.",
                    "basis_refs": ["discrepancy-weather-gt27"],
                    "entity_ref": "entity-wind-discrepancy",
                },
                {
                    "id": "node-change-wind",
                    "kind": "correction_change",
                    "identity": "entity-change-wind",
                    "impact_state": "affected",
                    "reason": "The stale wind value must be replaced in revision 8.",
                    "basis_refs": ["correction-weather-gt27", "discrepancy-weather-gt27"],
                    "entity_ref": "entity-change-wind",
                },
                {
                    "id": "node-change-mission-a",
                    "kind": "correction_change",
                    "identity": "entity-change-mission-a",
                    "impact_state": "affected",
                    "reason": "Mission A suitability must be recomputed from the updated wind.",
                    "basis_refs": ["correction-weather-gt27", "discrepancy-weather-gt27"],
                    "entity_ref": "entity-change-mission-a",
                },
                {
                    "id": "node-change-mission-d",
                    "kind": "correction_change",
                    "identity": "entity-change-mission-d",
                    "impact_state": "affected",
                    "reason": "Mission D suitability must be rerun even if the boolean remains true.",
                    "basis_refs": ["correction-weather-gt27", "discrepancy-weather-gt27"],
                    "entity_ref": "entity-change-mission-d",
                },
                {
                    "id": "node-wind-path",
                    "kind": "world_state_path",
                    "identity": "/objects/weather-cell-east/attributes/wind_speed_mps/value",
                    "impact_state": "affected",
                    "reason": "The east-zone wind input changes from 6 to 12 m/s.",
                    "basis_refs": ["correction-weather-gt27", "discrepancy-weather-gt27"],
                },
                {
                    "id": "node-mission-a-path",
                    "kind": "world_state_path",
                    "identity": "/relations/mission-a-weather-suitable/value",
                    "impact_state": "affected",
                    "reason": "Mission A suitability is an affected derived path.",
                    "basis_refs": ["correction-weather-gt27", "discrepancy-weather-gt27"],
                },
                {
                    "id": "node-mission-d-path",
                    "kind": "world_state_path",
                    "identity": "/relations/mission-d-weather-suitable/value",
                    "impact_state": "affected",
                    "reason": "Mission D suitability is an affected derived path even when its value is unchanged.",
                    "basis_refs": ["correction-weather-gt27", "discrepancy-weather-gt27"],
                },
                {
                    "id": "node-assert-mission-a",
                    "kind": "assertion",
                    "identity": "mission_a_wind_within_limit",
                    "impact_state": "requires_recheck",
                    "reason": "Mission A is in the east zone after the update and must be rechecked.",
                    "basis_refs": ["correction-weather-gt27", "discrepancy-weather-gt27"],
                },
                {
                    "id": "node-assert-mission-d",
                    "kind": "assertion",
                    "identity": "mission_d_wind_within_limit",
                    "impact_state": "requires_recheck",
                    "reason": "Mission D is in the east zone after the update and must also be rechecked.",
                    "basis_refs": ["correction-weather-gt27", "discrepancy-weather-gt27"],
                },
                {
                    "id": "node-output-mission-a",
                    "kind": "output",
                    "identity": "mission_a_weather_assessment",
                    "impact_state": "blocked",
                    "reason": "Mission A weather assessment remains blocked until its assertion recheck completes.",
                    "basis_refs": ["correction-weather-gt27", "discrepancy-weather-gt27"],
                },
                {
                    "id": "node-output-mission-d",
                    "kind": "output",
                    "identity": "mission_d_weather_assessment",
                    "impact_state": "blocked",
                    "reason": "Mission D weather assessment remains blocked until its assertion recheck completes.",
                    "basis_refs": ["correction-weather-gt27", "discrepancy-weather-gt27"],
                },
            ],
            "edges": [
                {
                    "id": "edge-discrepancy-requires-wind-change",
                    "kind": "requires",
                    "from_node": "node-wind-discrepancy",
                    "to_node": "node-change-wind",
                    "state": "confirmed",
                    "reason": "The discrepancy requires replacement of the stale wind input.",
                    "basis_refs": ["correction-weather-gt27", "discrepancy-weather-gt27"],
                },
                {
                    "id": "edge-wind-change-updates-path",
                    "kind": "changes",
                    "from_node": "node-change-wind",
                    "to_node": "node-wind-path",
                    "state": "confirmed",
                    "reason": "The declared replacement targets the wind-speed path.",
                    "basis_refs": ["correction-weather-gt27"],
                },
                {
                    "id": "edge-discrepancy-requires-mission-a-change",
                    "kind": "requires",
                    "from_node": "node-wind-discrepancy",
                    "to_node": "node-change-mission-a",
                    "state": "confirmed",
                    "reason": "The declared discrepancy scope requires Mission A to be recomputed because it is in the east zone after 14:00.",
                    "basis_refs": ["correction-weather-gt27", "discrepancy-weather-gt27"],
                },
                {
                    "id": "edge-discrepancy-requires-mission-d-change",
                    "kind": "requires",
                    "from_node": "node-wind-discrepancy",
                    "to_node": "node-change-mission-d",
                    "state": "confirmed",
                    "reason": "The declared discrepancy scope requires Mission D to be recomputed because it is in the east zone after 14:00.",
                    "basis_refs": ["correction-weather-gt27", "discrepancy-weather-gt27"],
                },
                {
                    "id": "edge-mission-a-change-updates-path",
                    "kind": "changes",
                    "from_node": "node-change-mission-a",
                    "to_node": "node-mission-a-path",
                    "state": "confirmed",
                    "reason": "The Mission A recompute change targets its suitability path.",
                    "basis_refs": ["correction-weather-gt27"],
                },
                {
                    "id": "edge-mission-d-change-updates-path",
                    "kind": "changes",
                    "from_node": "node-change-mission-d",
                    "to_node": "node-mission-d-path",
                    "state": "confirmed",
                    "reason": "The Mission D recompute change targets its suitability path.",
                    "basis_refs": ["correction-weather-gt27"],
                },
                {
                    "id": "edge-wind-path-affects-mission-a-path",
                    "kind": "affects",
                    "from_node": "node-wind-path",
                    "to_node": "node-mission-a-path",
                    "state": "confirmed",
                    "reason": "Mission A suitability depends on the east-zone wind input.",
                    "basis_refs": ["correction-weather-gt27", "discrepancy-weather-gt27"],
                },
                {
                    "id": "edge-wind-path-affects-mission-d-path",
                    "kind": "affects",
                    "from_node": "node-wind-path",
                    "to_node": "node-mission-d-path",
                    "state": "confirmed",
                    "reason": "Mission D suitability depends on the east-zone wind input.",
                    "basis_refs": ["correction-weather-gt27", "discrepancy-weather-gt27"],
                },
                {
                    "id": "edge-mission-a-path-requires-recheck",
                    "kind": "requires_recheck",
                    "from_node": "node-mission-a-path",
                    "to_node": "node-assert-mission-a",
                    "state": "confirmed",
                    "reason": "The changed Mission A path requires its assertion to be rerun.",
                    "basis_refs": ["correction-weather-gt27", "discrepancy-weather-gt27"],
                },
                {
                    "id": "edge-mission-d-path-requires-recheck",
                    "kind": "requires_recheck",
                    "from_node": "node-mission-d-path",
                    "to_node": "node-assert-mission-d",
                    "state": "confirmed",
                    "reason": "The Mission D path requires recheck even when the result remains true.",
                    "basis_refs": ["correction-weather-gt27", "discrepancy-weather-gt27"],
                },
                {
                    "id": "edge-mission-a-assertion-blocks-output",
                    "kind": "blocks",
                    "from_node": "node-assert-mission-a",
                    "to_node": "node-output-mission-a",
                    "state": "confirmed",
                    "reason": "Mission A weather assessment remains blocked until its assertion recheck completes.",
                    "basis_refs": ["correction-weather-gt27", "discrepancy-weather-gt27"],
                },
                {
                    "id": "edge-mission-d-assertion-blocks-output",
                    "kind": "blocks",
                    "from_node": "node-assert-mission-d",
                    "to_node": "node-output-mission-d",
                    "state": "confirmed",
                    "reason": "Mission D weather assessment remains blocked until its assertion recheck completes.",
                    "basis_refs": ["correction-weather-gt27", "discrepancy-weather-gt27"],
                },
            ],
            "reevaluation_targets": [
                {
                    "id": "target-mission-a-wind",
                    "node_ref": "node-assert-mission-a",
                    "state": "required",
                    "reason": "Rerun Mission A wind suitability against the successor state.",
                    "input_node_refs": ["node-wind-path", "node-mission-a-path"],
                    "prerequisite_node_refs": ["node-change-wind", "node-change-mission-a"],
                    "basis_refs": ["correction-weather-gt27", "discrepancy-weather-gt27"],
                },
                {
                    "id": "target-mission-d-wind",
                    "node_ref": "node-assert-mission-d",
                    "state": "required",
                    "reason": "Rerun Mission D wind suitability against the successor state.",
                    "input_node_refs": ["node-wind-path", "node-mission-d-path"],
                    "prerequisite_node_refs": ["node-change-wind", "node-change-mission-d"],
                    "basis_refs": ["correction-weather-gt27", "discrepancy-weather-gt27"],
                },
                {
                    "id": "target-output-mission-a",
                    "node_ref": "node-output-mission-a",
                    "state": "blocked",
                    "reason": "Mission A weather assessment cannot be released until the affected assertion completes.",
                    "input_node_refs": ["node-assert-mission-a"],
                    "prerequisite_node_refs": ["node-change-wind", "node-change-mission-a"],
                    "basis_refs": ["correction-weather-gt27", "discrepancy-weather-gt27"],
                },
                {
                    "id": "target-output-mission-d",
                    "node_ref": "node-output-mission-d",
                    "state": "blocked",
                    "reason": "Mission D weather assessment cannot be released until the affected assertion completes.",
                    "input_node_refs": ["node-assert-mission-d"],
                    "prerequisite_node_refs": ["node-change-wind", "node-change-mission-d"],
                    "basis_refs": ["correction-weather-gt27", "discrepancy-weather-gt27"],
                },
            ],
            "blocked_outputs": [
                "mission_a_weather_assessment",
                "mission_d_weather_assessment",
            ],
            "blocked_actions": [],
        }
    }
    graph = load_impact_graph(payload)
    validate_impact_graph_bindings(
        graph,
        base_world_state,
        {"discrepancy-weather-gt27": report},
        {"correction-weather-gt27": request},
        {
            "base-world-state-gt27": base_bytes,
            "discrepancy-weather-gt27": report_bytes,
            "correction-weather-gt27": request_bytes,
        },
    )
    return graph, _pretty_bytes(graph.to_dict())


def _build_execution(
    scenario: Mapping[str, object],
    observation: Observation,
) -> tuple[GeotaskResult, bytes]:
    missions = _mission_map(scenario)
    wind = _integer(
        _mapping(scenario.get("weather_update"), "scenario.weather_update").get(
            "new_wind_mps"
        ),
        "weather_update.new_wind_mps",
    )
    checks: list[dict[str, object]] = []
    outputs: dict[str, object] = {}
    for mission_id, assertion_id in (
        ("mission-a-delivery", "mission_a_wind_within_limit"),
        ("mission-d-emergency", "mission_d_wind_within_limit"),
    ):
        mission = missions[mission_id]
        limit = _integer(mission.get("max_wind_mps"), f"missions.{mission_id}.max_wind_mps")
        value = wind <= limit
        checks.append(
            {
                "assertion_id": assertion_id,
                "operator": "gt27_case_wind_threshold",
                "object_refs": ["weather-cell-east", mission_id],
                "executor": "local",
                "value": value,
                "unit": "",
                "status": "verified",
                "assurance_level": "local_deterministic",
                "deterministic": True,
                "evidence_refs": [observation.source.reference],
                "error": None,
            }
        )
        outputs[assertion_id] = value
    payload = {
        "geotask_result": {
            "schema_version": "1.0",
            "task_id": "gt27-weather-affected-mission-recheck",
            "execution": {
                "mode": "local_only",
                "status": "completed",
                "started_at": "2026-08-04T14:00:09+08:00",
                "finished_at": "2026-08-04T14:00:10+08:00",
            },
            "checks": checks,
            "outputs": outputs,
            "summary": {
                "total_checks": 2,
                "verified": 2,
                "contradicted": 0,
                "need_review": 0,
                "invalid": 0,
            },
            "overall": {
                "status": "verified",
                "assurance_level": "local_deterministic",
            },
            "warnings": [
                "gt27_case_wind_threshold is a case-specific deterministic comparison, not a registered generic GeoTask weather operator."
            ],
            "errors": [],
        }
    }
    execution = GeotaskResult.from_dict(payload)
    return execution, _pretty_bytes(execution.to_dict())


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


def _build_incremental_result(
    base_world_state: WorldState,
    base_bytes: bytes,
    successor_world_state: WorldState,
    successor_bytes: bytes,
    report: DiscrepancyReport,
    report_bytes: bytes,
    request: CorrectionRequest,
    request_bytes: bytes,
    graph: ImpactGraph,
    graph_bytes: bytes,
    execution: GeotaskResult,
    execution_bytes: bytes,
) -> tuple[IncrementalReevaluationResult, bytes]:
    payload = {
        "incremental_reevaluation_result": {
            "schema_id": "https://stpku.github.io/GeoTask/schemas/geotask-incremental-reevaluation-result-v0.1.schema.json",
            "schema_version": "0.1",
            "result_id": "gt27-weather-bounded-incremental-reevaluation",
            "recorded_at": "2026-08-04T14:00:12+08:00",
            "state": "completed",
            "reason": "Only mission A and mission D were reevaluated against revision 8; mission A changed from suitable to unsuitable, mission D remained suitable after recheck, and mission B and mission C were preserved outside the declared target set.",
            "base_world_state": {
                "ref_id": "base-world-state-gt27",
                "artifact_id": "geotask.world-state",
                "schema_version": "0.1",
                "world_state_id": base_world_state.world_state_id,
                "revision": base_world_state.revision,
                "as_of": base_world_state.as_of,
                "semantic_fingerprint": base_world_state.semantic_fingerprint(),
                "content_sha256": _sha256(base_bytes),
            },
            "successor_world_state": {
                "ref_id": "successor-world-state-gt27",
                "artifact_id": "geotask.world-state",
                "schema_version": "0.1",
                "world_state_id": successor_world_state.world_state_id,
                "revision": successor_world_state.revision,
                "as_of": successor_world_state.as_of,
                "semantic_fingerprint": successor_world_state.semantic_fingerprint(),
                "content_sha256": _sha256(successor_bytes),
            },
            "impact_graph_ref": _artifact_ref(
                "impact-graph-weather-gt27",
                "geotask.impact-graph",
                "0.1",
                graph.graph_id,
                graph_bytes,
            ),
            "correction_request_refs": [
                _artifact_ref(
                    "correction-weather-gt27",
                    "geotask.correction-request",
                    "0.1",
                    request.request_id,
                    request_bytes,
                )
            ],
            "discrepancy_report_refs": [
                _artifact_ref(
                    "discrepancy-weather-gt27",
                    "geotask.discrepancy-report",
                    "0.1",
                    report.report_id,
                    report_bytes,
                )
            ],
            "execution_result_refs": [
                _artifact_ref(
                    "execution-weather-gt27",
                    "geotask.execution-result",
                    "1.0",
                    execution.task_id,
                    execution_bytes,
                )
            ],
            "node_results": [
                {
                    "id": "result-node-wind-discrepancy",
                    "node_ref": "node-wind-discrepancy",
                    "state": "resolved",
                    "reason": "Revision 8 contains 12 m/s instead of the stale 6 m/s value.",
                    "basis_refs": [
                        "successor-world-state-gt27",
                        "discrepancy-weather-gt27",
                        "correction-weather-gt27",
                    ],
                },
                {
                    "id": "result-node-change-wind",
                    "node_ref": "node-change-wind",
                    "state": "recomputed",
                    "reason": "The already observed east-zone wind path was explicitly carried into revision 8.",
                    "previous": 12,
                    "current": 12,
                    "basis_refs": [
                        "base-world-state-gt27",
                        "successor-world-state-gt27",
                        "correction-weather-gt27",
                    ],
                },
                {
                    "id": "result-node-change-mission-a",
                    "node_ref": "node-change-mission-a",
                    "state": "recomputed",
                    "reason": "Mission A suitability was recomputed from 12 m/s and its 10 m/s threshold.",
                    "previous": True,
                    "current": False,
                    "basis_refs": [
                        "base-world-state-gt27",
                        "successor-world-state-gt27",
                        "correction-weather-gt27",
                    ],
                },
                {
                    "id": "result-node-change-mission-d",
                    "node_ref": "node-change-mission-d",
                    "state": "recomputed",
                    "reason": "Mission D suitability was rerun from 12 m/s and its 15 m/s threshold.",
                    "previous": True,
                    "current": True,
                    "basis_refs": [
                        "base-world-state-gt27",
                        "successor-world-state-gt27",
                        "correction-weather-gt27",
                    ],
                },
                {
                    "id": "result-node-wind-path",
                    "node_ref": "node-wind-path",
                    "state": "recomputed",
                    "reason": "The successor wind path explicitly preserves the observed 12 m/s value.",
                    "previous": 12,
                    "current": 12,
                    "basis_refs": [
                        "base-world-state-gt27",
                        "successor-world-state-gt27",
                        "correction-weather-gt27",
                    ],
                },
                {
                    "id": "result-node-mission-a-path",
                    "node_ref": "node-mission-a-path",
                    "state": "recomputed",
                    "reason": "Mission A suitability changed from true to false.",
                    "previous": True,
                    "current": False,
                    "basis_refs": [
                        "base-world-state-gt27",
                        "successor-world-state-gt27",
                        "correction-weather-gt27",
                    ],
                },
                {
                    "id": "result-node-mission-d-path",
                    "node_ref": "node-mission-d-path",
                    "state": "recomputed",
                    "reason": "Mission D suitability was recomputed and remained true.",
                    "previous": True,
                    "current": True,
                    "basis_refs": [
                        "base-world-state-gt27",
                        "successor-world-state-gt27",
                        "correction-weather-gt27",
                    ],
                },
                {
                    "id": "result-node-assert-mission-a",
                    "node_ref": "node-assert-mission-a",
                    "state": "recomputed",
                    "reason": "The bound execution result reports Mission A wind suitability as false.",
                    "previous": True,
                    "current": False,
                    "basis_refs": [
                        "base-world-state-gt27",
                        "successor-world-state-gt27",
                        "execution-weather-gt27",
                    ],
                },
                {
                    "id": "result-node-assert-mission-d",
                    "node_ref": "node-assert-mission-d",
                    "state": "recomputed",
                    "reason": "The bound execution result reports Mission D wind suitability as true.",
                    "previous": True,
                    "current": True,
                    "basis_refs": [
                        "base-world-state-gt27",
                        "successor-world-state-gt27",
                        "execution-weather-gt27",
                    ],
                },
                {
                    "id": "result-node-output-mission-a",
                    "node_ref": "node-output-mission-a",
                    "state": "released",
                    "reason": "Mission A weather assessment was released after its affected assertion completed.",
                    "basis_refs": [
                        "successor-world-state-gt27",
                        "correction-weather-gt27",
                        "execution-weather-gt27",
                    ],
                },
                {
                    "id": "result-node-output-mission-d",
                    "node_ref": "node-output-mission-d",
                    "state": "released",
                    "reason": "Mission D weather assessment was released after its affected assertion completed.",
                    "basis_refs": [
                        "successor-world-state-gt27",
                        "correction-weather-gt27",
                        "execution-weather-gt27",
                    ],
                },
            ],
            "target_results": [
                {
                    "id": "result-target-mission-a-wind",
                    "target_ref": "target-mission-a-wind",
                    "node_ref": "node-assert-mission-a",
                    "node_result_ref": "result-node-assert-mission-a",
                    "state": "completed",
                    "reason": "Mission A was reevaluated against revision 8 and changed to false.",
                    "basis_refs": [
                        "impact-graph-weather-gt27",
                        "successor-world-state-gt27",
                        "execution-weather-gt27",
                    ],
                },
                {
                    "id": "result-target-mission-d-wind",
                    "target_ref": "target-mission-d-wind",
                    "node_ref": "node-assert-mission-d",
                    "node_result_ref": "result-node-assert-mission-d",
                    "state": "completed",
                    "reason": "Mission D was reevaluated against revision 8 and remained true.",
                    "basis_refs": [
                        "impact-graph-weather-gt27",
                        "successor-world-state-gt27",
                        "execution-weather-gt27",
                    ],
                },
                {
                    "id": "result-target-output-mission-a",
                    "target_ref": "target-output-mission-a",
                    "node_ref": "node-output-mission-a",
                    "node_result_ref": "result-node-output-mission-a",
                    "state": "completed",
                    "reason": "Mission A weather assessment target completed after the assertion recheck.",
                    "basis_refs": [
                        "impact-graph-weather-gt27",
                        "successor-world-state-gt27",
                        "execution-weather-gt27",
                    ],
                },
                {
                    "id": "result-target-output-mission-d",
                    "target_ref": "target-output-mission-d",
                    "node_ref": "node-output-mission-d",
                    "node_result_ref": "result-node-output-mission-d",
                    "state": "completed",
                    "reason": "Mission D weather assessment target completed after the assertion recheck.",
                    "basis_refs": [
                        "impact-graph-weather-gt27",
                        "successor-world-state-gt27",
                        "execution-weather-gt27",
                    ],
                },
            ],
            "acceptance_results": [
                {
                    "id": "accept-wind-path-recomputed",
                    "request_ref": "correction-weather-gt27",
                    "criterion_id": "wind-path-recomputed",
                    "state": "satisfied",
                    "reason": "Revision 8 explicitly carries the observed 12 m/s value through the wind recompute change.",
                    "node_result_refs": [
                        "result-node-change-wind",
                        "result-node-wind-path",
                    ],
                    "target_result_refs": [],
                    "basis_refs": [
                        "correction-weather-gt27",
                        "successor-world-state-gt27",
                    ],
                },
                {
                    "id": "accept-mission-a-path-recomputed",
                    "request_ref": "correction-weather-gt27",
                    "criterion_id": "mission-a-path-recomputed",
                    "state": "satisfied",
                    "reason": "The Mission A change and successor path are both recorded as recomputed.",
                    "node_result_refs": [
                        "result-node-change-mission-a",
                        "result-node-mission-a-path",
                    ],
                    "target_result_refs": [],
                    "basis_refs": [
                        "correction-weather-gt27",
                        "successor-world-state-gt27",
                    ],
                },
                {
                    "id": "accept-mission-d-path-recomputed",
                    "request_ref": "correction-weather-gt27",
                    "criterion_id": "mission-d-path-recomputed",
                    "state": "satisfied",
                    "reason": "The Mission D change and successor path are both recorded as recomputed.",
                    "node_result_refs": [
                        "result-node-change-mission-d",
                        "result-node-mission-d-path",
                    ],
                    "target_result_refs": [],
                    "basis_refs": [
                        "correction-weather-gt27",
                        "successor-world-state-gt27",
                    ],
                },
                {
                    "id": "accept-successor-world-state-valid",
                    "request_ref": "correction-weather-gt27",
                    "criterion_id": "successor-world-state-valid",
                    "state": "satisfied",
                    "reason": "The bound revision-8 World State passes strict loading and fingerprint checks.",
                    "node_result_refs": [],
                    "target_result_refs": [],
                    "basis_refs": [
                        "correction-weather-gt27",
                        "successor-world-state-gt27",
                    ],
                },
                {
                    "id": "accept-affected-weather-outputs-rechecked",
                    "request_ref": "correction-weather-gt27",
                    "criterion_id": "affected-weather-outputs-rechecked",
                    "state": "satisfied",
                    "reason": "Both affected mission weather outputs completed after their assertion rechecks.",
                    "node_result_refs": [
                        "result-node-output-mission-a",
                        "result-node-output-mission-d",
                    ],
                    "target_result_refs": [
                        "result-target-output-mission-a",
                        "result-target-output-mission-d",
                    ],
                    "basis_refs": [
                        "correction-weather-gt27",
                        "successor-world-state-gt27",
                        "execution-weather-gt27",
                    ],
                },
                {
                    "id": "accept-wind-discrepancy-resolved",
                    "request_ref": "correction-weather-gt27",
                    "criterion_id": "wind-discrepancy-resolved",
                    "state": "satisfied",
                    "reason": "The discrepancy node is resolved by the 12 m/s successor value.",
                    "node_result_refs": ["result-node-wind-discrepancy"],
                    "target_result_refs": [],
                    "basis_refs": [
                        "correction-weather-gt27",
                        "discrepancy-weather-gt27",
                        "successor-world-state-gt27",
                    ],
                },
            ],
            "discrepancy_results": [
                {
                    "id": "result-east-wind-speed-mismatch",
                    "request_ref": "correction-weather-gt27",
                    "discrepancy_ref": "wind-speed-mismatch",
                    "state": "resolved",
                    "reason": "Revision 8 contains 12 m/s and the two declared affected assertions completed.",
                    "node_result_refs": ["result-node-wind-discrepancy"],
                    "basis_refs": [
                        "discrepancy-weather-gt27",
                        "correction-weather-gt27",
                        "successor-world-state-gt27",
                        "execution-weather-gt27",
                    ],
                }
            ],
            "output_gates": [
                {
                    "output_ref": "mission_a_weather_assessment",
                    "state": "released",
                    "reason": "Mission A weather assessment was released after its output target completed and all correction criteria were satisfied.",
                    "target_result_refs": ["result-target-output-mission-a"],
                    "criterion_result_refs": [
                        "accept-wind-path-recomputed",
                        "accept-mission-a-path-recomputed",
                        "accept-mission-d-path-recomputed",
                        "accept-successor-world-state-valid",
                        "accept-affected-weather-outputs-rechecked",
                        "accept-wind-discrepancy-resolved",
                    ],
                },
                {
                    "output_ref": "mission_d_weather_assessment",
                    "state": "released",
                    "reason": "Mission D weather assessment was released after its output target completed and all correction criteria were satisfied.",
                    "target_result_refs": ["result-target-output-mission-d"],
                    "criterion_result_refs": [
                        "accept-wind-path-recomputed",
                        "accept-mission-a-path-recomputed",
                        "accept-mission-d-path-recomputed",
                        "accept-successor-world-state-valid",
                        "accept-affected-weather-outputs-rechecked",
                        "accept-wind-discrepancy-resolved",
                    ],
                },
            ],
            "action_gates": [],
            "next_action": "none",
        }
    }
    result = load_incremental_reevaluation_result(payload)
    validate_incremental_reevaluation_result_bindings(
        result,
        base_world_state,
        successor_world_state,
        graph,
        {"correction-weather-gt27": request},
        {"discrepancy-weather-gt27": report},
        {"execution-weather-gt27": execution},
        {
            "base-world-state-gt27": base_bytes,
            "successor-world-state-gt27": successor_bytes,
            "impact-graph-weather-gt27": graph_bytes,
            "correction-weather-gt27": request_bytes,
            "discrepancy-weather-gt27": report_bytes,
            "execution-weather-gt27": execution_bytes,
        },
    )
    return result, _pretty_bytes(result.to_dict())


def _validate_case_scope(
    scenario: Mapping[str, object],
    base_world_state: WorldState,
    successor_world_state: WorldState,
    graph: ImpactGraph,
    result: IncrementalReevaluationResult,
) -> None:
    missions = _mission_map(scenario)
    expected_targets = {
        _string(item, f"reevaluation_targets[{index}]")
        for index, item in enumerate(
            _sequence(
                _mapping(scenario.get("declared_scope"), "scenario.declared_scope").get(
                    "reevaluation_targets"
                ),
                "scenario.declared_scope.reevaluation_targets",
            )
        )
    }
    excluded_targets = {
        _string(item, f"excluded_targets[{index}]")
        for index, item in enumerate(
            _sequence(
                _mapping(scenario.get("declared_scope"), "scenario.declared_scope").get(
                    "excluded_targets"
                ),
                "scenario.declared_scope.excluded_targets",
            )
        )
    }
    graph_assertions = {
        node.identity for node in graph.nodes if node.kind == "assertion"
    }
    if graph_assertions != expected_targets:
        raise GT27BuildError("Impact Graph assertion scope does not match declared targets")
    if graph_assertions & excluded_targets:
        raise GT27BuildError("excluded mission assertions entered the Impact Graph")
    if len(result.target_results) != 4:
        raise GT27BuildError("GT27 requires two assertion targets and two output-release targets")
    assertion_target_results = {
        item.target_ref
        for item in result.target_results
        if item.target_ref in {"target-mission-a-wind", "target-mission-d-wind"}
    }
    if assertion_target_results != {"target-mission-a-wind", "target-mission-d-wind"}:
        raise GT27BuildError("GT27 must complete exactly the two declared mission assertion targets")

    for mission_id, relation_id in (
        ("mission-a-delivery", "mission-a-weather-suitable"),
        ("mission-b-inspection", "mission-b-weather-suitable"),
        ("mission-c-survey", "mission-c-weather-suitable"),
        ("mission-d-emergency", "mission-d-weather-suitable"),
    ):
        mission = missions[mission_id]
        expected_previous = _boolean(mission.get("previous"), f"missions.{mission_id}.previous")
        expected_current = _boolean(mission.get("current"), f"missions.{mission_id}.current")
        if _relation_value(base_world_state, relation_id) != expected_previous:
            raise GT27BuildError(f"base relation mismatch for {mission_id}")
        if _relation_value(successor_world_state, relation_id) != expected_current:
            raise GT27BuildError(f"successor relation mismatch for {mission_id}")

    if _attribute_value(base_world_state, "weather-cell-east", "wind_speed_mps") != 12:
        raise GT27BuildError("base snapshot must already contain the observed 12 m/s wind value")
    if _attribute_value(successor_world_state, "weather-cell-east", "wind_speed_mps") != 12:
        raise GT27BuildError("successor wind must equal 12 m/s")


def build_gt27_incremental_reevaluation(
    scenario_path: str | Path,
) -> dict[str, object]:
    path = Path(scenario_path).resolve()
    root = _mapping(json.loads(path.read_text(encoding="utf-8")), "root")
    scenario = _mapping(root.get("scenario"), "scenario")
    observation, observation_bytes, base_world_state, base_bytes, base_payload = _load_inputs(
        path, scenario
    )
    successor_world_state, successor_bytes = _build_successor(
        scenario, observation, base_payload
    )
    report, report_bytes = _build_discrepancy(
        scenario, observation, observation_bytes, base_world_state
    )
    request, request_bytes = _build_correction(
        scenario,
        observation,
        base_world_state,
        base_bytes,
        report,
        report_bytes,
    )
    graph, graph_bytes = _build_graph(
        base_world_state,
        base_bytes,
        report,
        report_bytes,
        request,
        request_bytes,
    )
    execution, execution_bytes = _build_execution(scenario, observation)
    result, result_bytes = _build_incremental_result(
        base_world_state,
        base_bytes,
        successor_world_state,
        successor_bytes,
        report,
        report_bytes,
        request,
        request_bytes,
        graph,
        graph_bytes,
        execution,
        execution_bytes,
    )
    _validate_case_scope(
        scenario, base_world_state, successor_world_state, graph, result
    )
    return {
        "base_world_state": base_world_state,
        "successor_world_state": successor_world_state,
        "discrepancy_report": report,
        "correction_request": request,
        "impact_graph": graph,
        "execution_result": execution,
        "incremental_result": result,
        "bytes": {
            "successor_world_state": successor_bytes,
            "discrepancy_report": report_bytes,
            "correction_request": request_bytes,
            "impact_graph": graph_bytes,
            "execution_result": execution_bytes,
            "incremental_result": result_bytes,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "scenario",
        nargs="?",
        default=str(Path(__file__).with_name("gt27_weather_incremental_reevaluation.json")),
    )
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    scenario_path = Path(args.scenario).resolve()
    bundle = build_gt27_incremental_reevaluation(scenario_path)
    if args.write:
        scenario = _mapping(
            _mapping(
                json.loads(scenario_path.read_text(encoding="utf-8")), "root"
            ).get("scenario"),
            "scenario",
        )
        filenames = {
            "successor_world_state": scenario.get("successor_world_state"),
            "discrepancy_report": scenario.get("discrepancy_report"),
            "correction_request": scenario.get("correction_request"),
            "impact_graph": scenario.get("impact_graph"),
            "execution_result": scenario.get("execution_result"),
            "incremental_result": scenario.get("incremental_result"),
        }
        for key, filename in filenames.items():
            target = _case_path(scenario_path, filename, f"scenario.{key}")
            target.write_bytes(bundle["bytes"][key])
    else:
        result = bundle["incremental_result"]
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
