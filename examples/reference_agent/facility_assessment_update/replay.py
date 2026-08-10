#!/usr/bin/env python3
"""Replay the GeoTask Reference Agent v0.1 facility-assessment update.

The example is intentionally fictional and read-only. It composes existing public
GeoTask primitives to demonstrate the product lifecycle rather than introducing a
new GT case or a new Core artifact type.

The replay performs four kinds of work:
1. strict Observation and World State loading;
2. deterministic local distance recomputation through the public v1 executor;
3. explicit evidence freshness/conflict handling and bounded impact declaration;
4. public Control Evaluation proving that eligible output is not production action.

It never fetches live data, writes an industry database, publishes a report, or
executes a real-world action.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

# Make the replay runnable from a source checkout as well as an installed package.
# A materialized activation workspace may live at any filesystem depth, so never
# assume a fixed number of parents. Only inject a source path when a checkout is
# actually discoverable; otherwise the installed `geotask_core` package is used.
_SRC_ROOT = next(
    (
        parent / "src"
        for parent in Path(__file__).resolve().parents
        if (parent / "src" / "geotask_core").is_dir()
    ),
    None,
)
if _SRC_ROOT is not None and str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.control_evaluation import evaluate_control_profile
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
from geotask_core.v1.executor import execute_canonical
from geotask_core.v1.impact_graph import (
    ImpactGraph,
    load_impact_graph,
    validate_impact_graph_bindings,
)
from geotask_core.v1.observation import Observation, load_observation
from geotask_core.v1.world_state import WorldState, load_world_state


BASE_DIR = Path(__file__).resolve().parent
TASK_PATH = BASE_DIR / "task.yaml"
REQUEST_PATH = BASE_DIR / "request.txt"
WORLD_STATE_PATH = BASE_DIR / "world_state_before.json"
SCENARIO_DIR = BASE_DIR / "scenarios"
SCENARIO_NAMES = (
    "success",
    "missing_evidence",
    "conflicting_evidence",
    "stale_evidence",
    "contradicted",
)


class ReferenceAgentReplayError(ValueError):
    """Raised when the fixed Reference Agent scenario is internally inconsistent."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _pretty_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: object, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReferenceAgentReplayError(f"{path} must be an object")
    return value


def _sequence(value: object, path: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ReferenceAgentReplayError(f"{path} must be an array")
    return value


def _timestamp(value: object, path: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ReferenceAgentReplayError(f"{path} must be a timezone-aware timestamp")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ReferenceAgentReplayError(f"{path} must include a timezone offset")
    return parsed


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ReferenceAgentReplayError(f"{path}: root must be an object")
    return value


def _load_task() -> dict[str, Any]:
    value = yaml.safe_load(TASK_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ReferenceAgentReplayError("task.yaml root must be an object")
    return value


def _build_observation(raw: Mapping[str, Any]) -> Observation:
    coordinates = list(_sequence(raw.get("coordinates"), "evidence.coordinates"))
    if len(coordinates) != 2 or any(
        isinstance(item, bool) or not isinstance(item, (int, float)) for item in coordinates
    ):
        raise ReferenceAgentReplayError("evidence.coordinates must contain two numbers")

    source_reference = str(raw.get("source_reference", ""))
    source_version = str(raw.get("source_version", ""))
    observation_id = str(raw.get("observation_id", ""))
    producer_id = str(raw.get("producer_id", ""))
    if not all((source_reference, source_version, observation_id, producer_id)):
        raise ReferenceAgentReplayError("evidence identity fields must be non-empty")

    source_hash = hashlib.sha256(
        (source_reference + "|" + source_version + "|" + json.dumps(coordinates)).encode("utf-8")
    ).hexdigest()
    payload = {
        "observation": {
            "schema_id": "https://stpku.github.io/GeoTask/schemas/geotask-observation-v0.1.schema.json",
            "schema_version": "0.1",
            "observation_id": observation_id,
            "observed_at": raw.get("observed_at"),
            "received_at": raw.get("received_at"),
            "source": {
                "kind": "map",
                "reference": source_reference,
                "sha256": source_hash,
            },
            "producer": {
                "id": producer_id,
                "kind": "organization",
                "version": source_version,
            },
            "claims": [
                {
                    "id": f"{observation_id}-position-xy",
                    "subject_ref": "mapped-obstacle-01",
                    "predicate": "position_xy",
                    "basis": "direct_observation",
                    "value": {
                        "x": float(coordinates[0]),
                        "y": float(coordinates[1]),
                        "unit": "meter",
                    },
                    "valid_until": raw.get("valid_until"),
                    "evidence_refs": [source_reference],
                }
            ],
        }
    }
    return load_observation(payload)


def _evidence_resolution(
    scenario: Mapping[str, Any],
) -> tuple[str, Observation | None, list[Observation], str]:
    evaluation_time = _timestamp(scenario.get("evaluation_time"), "scenario.evaluation_time")
    observations = [
        _build_observation(_mapping(item, f"scenario.evidence[{index}]"))
        for index, item in enumerate(_sequence(scenario.get("evidence"), "scenario.evidence"))
    ]
    if not observations:
        return "missing", None, [], "No obstacle evidence was supplied."

    fresh: list[Observation] = []
    stale: list[Observation] = []
    for observation in observations:
        claim = observation.claims[0]
        if claim.valid_until is None:
            stale.append(observation)
            continue
        valid_until = _timestamp(claim.valid_until, f"{observation.observation_id}.valid_until")
        if valid_until < evaluation_time:
            stale.append(observation)
        else:
            fresh.append(observation)

    if not fresh:
        return (
            "stale",
            None,
            observations,
            "Obstacle evidence exists, but none remains valid at the declared evaluation time.",
        )

    coordinate_fingerprints = {
        _sha256(observation.claims[0].value) for observation in fresh
    }
    if len(coordinate_fingerprints) > 1:
        return (
            "conflicted",
            None,
            observations,
            "Fresh independent obstacle observations disagree and no precedence or adjudication policy is declared.",
        )

    accepted = sorted(fresh, key=lambda item: item.observation_id)[0]
    return (
        "verified",
        accepted,
        observations,
        "Fresh evidence is internally unambiguous for this fixed scenario; external truth is still not fetched by Core.",
    )


def _execute_distance(
    task_payload: Mapping[str, Any],
    accepted_observation: Observation | None,
):
    candidate = copy.deepcopy(dict(task_payload))
    if accepted_observation is not None:
        claim_value = _mapping(accepted_observation.claims[0].value, "accepted claim value")
        candidate["objects"]["mapped_obstacle"]["coordinates"] = [
            claim_value["x"],
            claim_value["y"],
        ]
    canonical = canonicalize(candidate)
    result = execute_canonical(canonical)
    check = next(
        (item for item in result.checks if item.assertion_id == "obstacle_distance_m"),
        None,
    )
    if check is None or not isinstance(check.value, (int, float)):
        raise ReferenceAgentReplayError("distance_2d did not produce obstacle_distance_m")
    return canonical, result, float(check.value), check


def _attribute(object_payload: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    for raw in _sequence(object_payload.get("attributes"), f"{object_payload.get('id')}.attributes"):
        item = _mapping(raw, "world_state attribute")
        if item.get("name") == name:
            return item
    raise ReferenceAgentReplayError(f"attribute {name!r} not found on {object_payload.get('id')!r}")


def _materialize_observation_state(
    base_payload: Mapping[str, Any],
    scenario: Mapping[str, Any],
    accepted: Observation,
) -> WorldState:
    """Apply only the accepted observation, leaving dependent assessment values stale."""

    payload = copy.deepcopy(dict(base_payload))
    body = _mapping(payload.get("world_state"), "world_state")
    body["revision"] = int(body["revision"]) + 1
    body["as_of"] = scenario.get("evaluation_time")
    body["materialized_at"] = scenario.get("materialized_at")
    body["observation_refs"] = sorted(
        set(_sequence(body.get("observation_refs"), "world_state.observation_refs"))
        | {accepted.observation_id}
    )
    body["evidence_refs"] = sorted(
        set(_sequence(body.get("evidence_refs"), "world_state.evidence_refs"))
        | {accepted.source.reference}
    )

    objects = [
        _mapping(item, "world_state object")
        for item in _sequence(body.get("objects"), "world_state.objects")
    ]
    obstacle = next(item for item in objects if item.get("id") == "mapped-obstacle-01")
    claim_value = _mapping(accepted.claims[0].value, "accepted position")
    obstacle["verification_status"] = "asserted"
    obstacle["observation_refs"] = [accepted.observation_id]
    obstacle["evidence_refs"] = [accepted.source.reference]
    position = _attribute(obstacle, "position_xy")
    position["value"] = copy.deepcopy(dict(claim_value))
    position["basis"] = "direct_observation"
    position["verification_status"] = "asserted"
    position["observation_refs"] = [accepted.observation_id]
    position["evidence_refs"] = [accepted.source.reference]
    position["valid_until"] = accepted.claims[0].valid_until
    return load_world_state(payload)


def _materialize_reevaluated_successor(
    observation_state: WorldState,
    scenario: Mapping[str, Any],
    accepted: Observation,
    distance_m: float,
    min_distance_m: float,
) -> WorldState:
    """Recompute only the two assessment values declared by the bounded impact chain."""

    payload = copy.deepcopy(observation_state.to_dict())
    body = _mapping(payload.get("world_state"), "world_state")
    body["revision"] = observation_state.revision + 1
    body["materialized_at"] = scenario.get("materialized_at")
    objects = [
        _mapping(item, "world_state object")
        for item in _sequence(body.get("objects"), "world_state.objects")
    ]
    assessment = next(item for item in objects if item.get("id") == "assessment-FAC-001")
    for name, value in (
        ("obstacle_distance_m", distance_m),
        ("obstacle_clearance_pass", distance_m >= min_distance_m),
    ):
        attribute = _attribute(assessment, name)
        attribute["value"] = value
        attribute["basis"] = "derived"
        attribute["verification_status"] = "verified"
        attribute["observation_refs"] = [accepted.observation_id]
        attribute["evidence_refs"] = [accepted.source.reference]
    return load_world_state(payload)


def _normalized_check(check: object) -> dict[str, Any]:
    return {
        "assertion_id": getattr(check, "assertion_id"),
        "operator": getattr(check, "operator"),
        "object_refs": list(getattr(check, "object_refs")),
        "value": getattr(check, "value"),
        "unit": getattr(check, "unit"),
        "status": getattr(check, "status"),
        "assurance_level": getattr(check, "assurance_level"),
        "deterministic": getattr(check, "deterministic"),
        "evidence_refs": list(getattr(check, "evidence_refs")),
    }


def _impact_graph(evidence_state: str) -> dict[str, Any]:
    return {
        "graph_id": "reference-agent-facility-obstacle-impact",
        "state": "declared_bounded_scope",
        "root": f"obstacle_evidence:{evidence_state}",
        "affected_nodes": [
            {
                "kind": "world_state_path",
                "identity": "/objects/mapped-obstacle-01/attributes/position_xy/value",
                "effect": "update_or_verify",
            },
            {
                "kind": "assertion",
                "identity": "obstacle_distance_m",
                "effect": "recompute",
            },
            {
                "kind": "assessment",
                "identity": "assessment-FAC-001.obstacle_clearance_pass",
                "effect": "reevaluate",
            },
            {
                "kind": "report_section",
                "identity": "report-v4.safety.obstacle_clearance",
                "effect": "refresh_gate",
            },
            {
                "kind": "review_target",
                "identity": "review:FAC-001:obstacle-clearance",
                "effect": "human_review",
            },
        ],
        "reused_nodes": [
            "assessment-FAC-001.accessibility_score",
            "assessment-FAC-001.service_capability_score",
            "report-v4.operator_summary",
        ],
        "automatic_dependency_discovery": False,
        "automatic_global_recompute": False,
    }


def _build_registered_impact_bundle(
    observation_state: WorldState,
    accepted: Observation,
    distance_m: float,
    min_distance_m: float,
    scenario: Mapping[str, Any],
) -> dict[str, Any]:
    """Build and validate registered Discrepancy, Correction, and Impact artifacts."""

    observation_state_bytes = _pretty_bytes(observation_state.to_dict())
    observation_bytes = _pretty_bytes(accepted.to_dict())
    distance_path = "/objects/assessment-FAC-001/attributes/obstacle_distance_m/value"
    clearance_path = "/objects/assessment-FAC-001/attributes/obstacle_clearance_pass/value"
    accessibility_path = "/objects/assessment-FAC-001/attributes/accessibility_score/value"
    service_path = "/objects/assessment-FAC-001/attributes/service_capability_score/value"
    recorded_at = str(scenario.get("materialized_at"))

    discrepancy_payload = {
        "discrepancy_report": {
            "schema_id": "https://stpku.github.io/GeoTask/schemas/geotask-discrepancy-report-v0.1.schema.json",
            "schema_version": "0.1",
            "report_id": f"reference-agent-{scenario.get('id')}-obstacle-distance-discrepancy",
            "recorded_at": recorded_at,
            "state": "confirmed",
            "severity": "high",
            "reason": "The accepted obstacle observation has entered the current state, while the stored obstacle-distance assessment still reflects the previous obstacle position.",
            "world_state": {
                "world_state_id": observation_state.world_state_id,
                "revision": observation_state.revision,
                "as_of": observation_state.as_of,
                "semantic_fingerprint": observation_state.semantic_fingerprint(),
            },
            "observation_refs": [accepted.observation_id],
            "evidence_refs": [accepted.source.reference],
            "artifact_refs": [
                {
                    "ref_id": "accepted-obstacle-observation",
                    "artifact_id": "geotask.observation",
                    "schema_version": "0.1",
                    "instance_id": accepted.observation_id,
                    "content_sha256": _sha256_bytes(observation_bytes),
                }
            ],
            "discrepancies": [
                {
                    "id": "obstacle-distance-stale-after-observation",
                    "kind": "value_mismatch",
                    "state": "confirmed",
                    "severity": "high",
                    "subject_kind": "attribute",
                    "subject_path": distance_path,
                    "summary": "The stored obstacle distance is stale after the accepted obstacle-position update.",
                    "reason": "The observation-state snapshot intentionally updates only the obstacle position. The previous 80 m assessment must be recomputed rather than silently reused.",
                    "basis_refs": ["accepted-obstacle-observation"],
                    "observation_refs": [accepted.observation_id],
                    "evidence_refs": [accepted.source.reference],
                    "expected": distance_m,
                    "observed": 80,
                    "impact": {
                        "state": "confirmed",
                        "reason": "Only obstacle distance, obstacle-clearance assessment, their report section, and review gate are declared affected.",
                        "affected_paths": [distance_path, clearance_path],
                        "affected_assertion_refs": ["obstacle_distance_m"],
                        "affected_output_refs": ["assessment_refresh", "report_refresh"],
                        "affected_action_refs": [],
                    },
                    "correction_scope": {
                        "state": "allowed",
                        "reason": "Recompute only obstacle-dependent assessment values; preserve unrelated assessment sections.",
                        "mutable_paths": [distance_path, clearance_path],
                        "immutable_paths": [accessibility_path, service_path],
                    },
                }
            ],
        }
    }
    report: DiscrepancyReport = load_discrepancy_report(discrepancy_payload)
    validate_discrepancy_report_bindings(
        report,
        observation_state,
        {"accepted-obstacle-observation": observation_bytes},
    )
    report_bytes = _pretty_bytes(report.to_dict())

    correction_payload = {
        "correction_request": {
            "schema_id": "https://stpku.github.io/GeoTask/schemas/geotask-correction-request-v0.1.schema.json",
            "schema_version": "0.1",
            "request_id": f"reference-agent-{scenario.get('id')}-bounded-assessment-recompute",
            "created_at": recorded_at,
            "state": "required",
            "reason": "Recompute only the obstacle-distance and obstacle-clearance assessment values; external Control Evaluation separately governs human review and report refresh.",
            "base_world_state": {
                "ref_id": "observation-state",
                "artifact_id": "geotask.world-state",
                "schema_version": "0.1",
                "world_state_id": observation_state.world_state_id,
                "revision": observation_state.revision,
                "as_of": observation_state.as_of,
                "semantic_fingerprint": observation_state.semantic_fingerprint(),
                "content_sha256": _sha256_bytes(observation_state_bytes),
            },
            "discrepancy_report_refs": [
                {
                    "ref_id": "obstacle-discrepancy",
                    "artifact_id": "geotask.discrepancy-report",
                    "schema_version": "0.1",
                    "instance_id": report.report_id,
                    "content_sha256": _sha256_bytes(report_bytes),
                }
            ],
            "supporting_artifact_refs": [],
            "observation_refs": [accepted.observation_id],
            "evidence_refs": [accepted.source.reference],
            "discrepancy_refs": [
                {
                    "id": "distance-stale-ref",
                    "report_ref": "obstacle-discrepancy",
                    "discrepancy_id": "obstacle-distance-stale-after-observation",
                }
            ],
            "changes": [
                {
                    "id": "recompute-obstacle-distance",
                    "discrepancy_ref": "distance-stale-ref",
                    "subject_kind": "attribute",
                    "target_path": distance_path,
                    "operation": "recompute",
                    "reason": "Recompute the facility-to-obstacle distance from the accepted obstacle position and the unchanged facility anchor.",
                    "basis_refs": ["obstacle-discrepancy"],
                    "observation_refs": [accepted.observation_id],
                    "evidence_refs": [accepted.source.reference],
                    "input_fields": ["facility_position_xy", "obstacle_position_xy"],
                    "acceptance_criterion_refs": [
                        "distance-path-recomputed",
                        "successor-world-state-valid",
                    ],
                    "before": 80,
                },
                {
                    "id": "recompute-obstacle-clearance",
                    "discrepancy_ref": "distance-stale-ref",
                    "subject_kind": "attribute",
                    "target_path": clearance_path,
                    "operation": "recompute",
                    "reason": "Recompute obstacle-clearance pass/fail from the new deterministic distance and the unchanged 50 m threshold.",
                    "basis_refs": ["obstacle-discrepancy"],
                    "observation_refs": [accepted.observation_id],
                    "evidence_refs": [accepted.source.reference],
                    "input_fields": ["obstacle_distance_m", "min_obstacle_distance_m"],
                    "acceptance_criterion_refs": [
                        "clearance-path-recomputed",
                        "successor-world-state-valid",
                    ],
                    "before": True,
                },
            ],
            "review_requirements": [],
            "acceptance_criteria": [
                {
                    "id": "distance-path-recomputed",
                    "kind": "path_recomputed",
                    "reason": "The successor state must contain a newly recomputed obstacle-distance value.",
                    "target_path": distance_path,
                    "output_refs": [],
                },
                {
                    "id": "clearance-path-recomputed",
                    "kind": "path_recomputed",
                    "reason": "The successor state must contain a newly recomputed obstacle-clearance result.",
                    "target_path": clearance_path,
                    "output_refs": [],
                },
                {
                    "id": "successor-world-state-valid",
                    "kind": "artifact_valid",
                    "reason": "The reevaluated successor must pass the registered World State validator.",
                    "artifact_id": "geotask.world-state",
                    "output_refs": [],
                },
                {
                    "id": "distance-discrepancy-resolved",
                    "kind": "discrepancy_resolved",
                    "reason": "The stale obstacle-distance discrepancy must be resolved by the successor state.",
                    "discrepancy_ref": "distance-stale-ref",
                    "output_refs": [],
                },
                {
                    "id": "affected-outputs-rechecked",
                    "kind": "recheck_completed",
                    "reason": "Only the affected assessment/report outputs must complete recheck before release.",
                    "output_refs": ["assessment_refresh", "report_refresh"],
                },
            ],
            "output_contract": {
                "artifact_id": "geotask.world-state",
                "schema_version": "0.1",
                "world_state_id": observation_state.world_state_id,
                "minimum_revision": observation_state.revision + 1,
                "preserve_immutable_paths": True,
                "require_semantic_fingerprint": True,
            },
            "blocked_outputs": ["assessment_refresh", "report_refresh"],
            "blocked_actions": [],
            "resume_when": "successor_world_state_valid == true and affected_outputs_rechecked == true",
            "next_action": "materialize_successor_state",
        }
    }
    request: CorrectionRequest = load_correction_request(correction_payload)
    validate_correction_request_bindings(
        request,
        observation_state,
        {"obstacle-discrepancy": report},
        {
            "observation-state": observation_state_bytes,
            "obstacle-discrepancy": report_bytes,
        },
    )
    request_bytes = _pretty_bytes(request.to_dict())

    impact_payload = {
        "impact_graph": {
            "schema_id": "https://stpku.github.io/GeoTask/schemas/geotask-impact-graph-v0.1.schema.json",
            "schema_version": "0.1",
            "graph_id": f"reference-agent-{scenario.get('id')}-impact-graph",
            "recorded_at": recorded_at,
            "state": "blocked",
            "reason": "One accepted obstacle observation affects only the obstacle-distance assertion, clearance assessment, review target, and report refresh chain.",
            "world_state": {
                "ref_id": "observation-state",
                "artifact_id": "geotask.world-state",
                "schema_version": "0.1",
                "world_state_id": observation_state.world_state_id,
                "revision": observation_state.revision,
                "as_of": observation_state.as_of,
                "semantic_fingerprint": observation_state.semantic_fingerprint(),
                "content_sha256": _sha256_bytes(observation_state_bytes),
            },
            "artifact_refs": [
                {
                    "ref_id": "obstacle-correction",
                    "artifact_id": "geotask.correction-request",
                    "schema_version": "0.1",
                    "instance_id": request.request_id,
                    "content_sha256": _sha256_bytes(request_bytes),
                },
                {
                    "ref_id": "obstacle-discrepancy",
                    "artifact_id": "geotask.discrepancy-report",
                    "schema_version": "0.1",
                    "instance_id": report.report_id,
                    "content_sha256": _sha256_bytes(report_bytes),
                },
            ],
            "entity_refs": [
                {
                    "id": "entity-distance-discrepancy",
                    "kind": "discrepancy",
                    "artifact_ref": "obstacle-discrepancy",
                    "entity_id": "obstacle-distance-stale-after-observation",
                },
                {
                    "id": "entity-distance-change",
                    "kind": "correction_change",
                    "artifact_ref": "obstacle-correction",
                    "entity_id": "recompute-obstacle-distance",
                },
                {
                    "id": "entity-clearance-change",
                    "kind": "correction_change",
                    "artifact_ref": "obstacle-correction",
                    "entity_id": "recompute-obstacle-clearance",
                },
            ],
            "root_node_refs": ["node-distance-discrepancy"],
            "nodes": [
                {
                    "id": "node-distance-discrepancy",
                    "kind": "discrepancy",
                    "identity": "entity-distance-discrepancy",
                    "impact_state": "root",
                    "reason": "The accepted obstacle position makes the previous 80 m assessment stale.",
                    "basis_refs": ["obstacle-discrepancy"],
                    "entity_ref": "entity-distance-discrepancy",
                },
                {
                    "id": "node-distance-change",
                    "kind": "correction_change",
                    "identity": "entity-distance-change",
                    "impact_state": "affected",
                    "reason": "Obstacle distance must be recomputed.",
                    "basis_refs": ["obstacle-correction", "obstacle-discrepancy"],
                    "entity_ref": "entity-distance-change",
                },
                {
                    "id": "node-distance-path",
                    "kind": "world_state_path",
                    "identity": distance_path,
                    "impact_state": "affected",
                    "reason": "Only the obstacle-distance assessment path changes first.",
                    "basis_refs": ["obstacle-correction", "obstacle-discrepancy"],
                },
                {
                    "id": "node-distance-assertion",
                    "kind": "assertion",
                    "identity": "obstacle_distance_m",
                    "impact_state": "requires_recheck",
                    "reason": "The public distance_2d assertion must be rerun against the accepted position.",
                    "basis_refs": ["obstacle-correction", "obstacle-discrepancy"],
                },
                {
                    "id": "node-clearance-change",
                    "kind": "correction_change",
                    "identity": "entity-clearance-change",
                    "impact_state": "affected",
                    "reason": "Obstacle clearance must be recomputed from the new distance.",
                    "basis_refs": ["obstacle-correction", "obstacle-discrepancy"],
                    "entity_ref": "entity-clearance-change",
                },
                {
                    "id": "node-clearance-path",
                    "kind": "world_state_path",
                    "identity": clearance_path,
                    "impact_state": "affected",
                    "reason": "Only the obstacle-clearance assessment path is downstream of the distance.",
                    "basis_refs": ["obstacle-correction", "obstacle-discrepancy"],
                },
                {
                    "id": "node-assessment-output",
                    "kind": "output",
                    "identity": "assessment_refresh",
                    "impact_state": "blocked",
                    "reason": "Assessment refresh is gated by bounded recomputation and review.",
                    "basis_refs": ["obstacle-correction", "obstacle-discrepancy"],
                },
                {
                    "id": "node-report-output",
                    "kind": "output",
                    "identity": "report_refresh",
                    "impact_state": "blocked",
                    "reason": "Report refresh remains an external workflow action after review.",
                    "basis_refs": ["obstacle-correction", "obstacle-discrepancy"],
                },
            ],
            "edges": [
                {
                    "id": "edge-discrepancy-requires-distance-change",
                    "kind": "requires",
                    "from_node": "node-distance-discrepancy",
                    "to_node": "node-distance-change",
                    "state": "confirmed",
                    "reason": "The stale assessment requires bounded distance recomputation.",
                    "basis_refs": ["obstacle-correction", "obstacle-discrepancy"],
                },
                {
                    "id": "edge-distance-change-updates-path",
                    "kind": "changes",
                    "from_node": "node-distance-change",
                    "to_node": "node-distance-path",
                    "state": "confirmed",
                    "reason": "The distance correction targets the distance path.",
                    "basis_refs": ["obstacle-correction"],
                },
                {
                    "id": "edge-distance-path-requires-assertion",
                    "kind": "requires_recheck",
                    "from_node": "node-distance-path",
                    "to_node": "node-distance-assertion",
                    "state": "confirmed",
                    "reason": "The affected distance path requires deterministic assertion replay.",
                    "basis_refs": ["obstacle-correction", "obstacle-discrepancy"],
                },
                {
                    "id": "edge-discrepancy-requires-clearance-change",
                    "kind": "requires",
                    "from_node": "node-distance-discrepancy",
                    "to_node": "node-clearance-change",
                    "state": "confirmed",
                    "reason": "The same stale obstacle assessment requires bounded clearance recomputation after distance changes.",
                    "basis_refs": ["obstacle-correction", "obstacle-discrepancy"],
                },
                {
                    "id": "edge-clearance-change-updates-path",
                    "kind": "changes",
                    "from_node": "node-clearance-change",
                    "to_node": "node-clearance-path",
                    "state": "confirmed",
                    "reason": "The clearance correction targets the clearance path.",
                    "basis_refs": ["obstacle-correction"],
                },
                {
                    "id": "edge-distance-path-affects-clearance-path",
                    "kind": "affects",
                    "from_node": "node-distance-path",
                    "to_node": "node-clearance-path",
                    "state": "confirmed",
                    "reason": "The clearance result depends on the recomputed distance and unchanged threshold.",
                    "basis_refs": ["obstacle-correction", "obstacle-discrepancy"],
                },
                {
                    "id": "edge-clearance-path-affects-assessment-output",
                    "kind": "affects",
                    "from_node": "node-clearance-path",
                    "to_node": "node-assessment-output",
                    "state": "confirmed",
                    "reason": "The affected clearance path determines whether the bounded assessment output may be refreshed.",
                    "basis_refs": ["obstacle-correction", "obstacle-discrepancy"],
                },
                {
                    "id": "edge-distance-assertion-affects-assessment-output",
                    "kind": "affects",
                    "from_node": "node-distance-assertion",
                    "to_node": "node-assessment-output",
                    "state": "confirmed",
                    "reason": "The deterministic distance recheck is an explicit prerequisite for refreshing the affected assessment output.",
                    "basis_refs": ["obstacle-correction", "obstacle-discrepancy"],
                },
                {
                    "id": "edge-assessment-blocks-report",
                    "kind": "blocks",
                    "from_node": "node-assessment-output",
                    "to_node": "node-report-output",
                    "state": "confirmed",
                    "reason": "The report output remains blocked while the affected assessment output is blocked.",
                    "basis_refs": ["obstacle-correction", "obstacle-discrepancy"],
                },
            ],
            "reevaluation_targets": [
                {
                    "id": "target-distance-assertion",
                    "node_ref": "node-distance-assertion",
                    "state": "required",
                    "reason": "Rerun deterministic obstacle distance.",
                    "input_node_refs": ["node-distance-path"],
                    "prerequisite_node_refs": ["node-distance-change"],
                    "basis_refs": ["obstacle-correction", "obstacle-discrepancy"],
                },
                {
                    "id": "target-assessment-refresh",
                    "node_ref": "node-assessment-output",
                    "state": "blocked",
                    "reason": "Refresh only the affected assessment output after bounded reevaluation.",
                    "input_node_refs": ["node-distance-assertion", "node-clearance-path"],
                    "prerequisite_node_refs": ["node-distance-change", "node-clearance-change"],
                    "basis_refs": ["obstacle-correction", "obstacle-discrepancy"],
                },
                {
                    "id": "target-report-refresh",
                    "node_ref": "node-report-output",
                    "state": "blocked",
                    "reason": "The registered Core impact chain blocks report refresh until the affected assessment is recomputed; the separate Control Evaluation adds the human-review gate.",
                    "input_node_refs": ["node-assessment-output"],
                    "prerequisite_node_refs": ["node-clearance-change"],
                    "basis_refs": ["obstacle-correction", "obstacle-discrepancy"],
                },
            ],
            "blocked_outputs": ["assessment_refresh", "report_refresh"],
            "blocked_actions": [],
        }
    }
    graph: ImpactGraph = load_impact_graph(impact_payload)
    validate_impact_graph_bindings(
        graph,
        observation_state,
        {"obstacle-discrepancy": report},
        {"obstacle-correction": request},
        {
            "observation-state": observation_state_bytes,
            "obstacle-discrepancy": report_bytes,
            "obstacle-correction": request_bytes,
        },
    )
    graph_bytes = _pretty_bytes(graph.to_dict())
    return {
        "discrepancy_report": report.to_dict(),
        "discrepancy_report_sha256": _sha256_bytes(report_bytes),
        "correction_request": request.to_dict(),
        "correction_request_sha256": _sha256_bytes(request_bytes),
        "impact_graph": graph.to_dict(),
        "impact_graph_sha256": _sha256_bytes(graph_bytes),
        "registered_artifacts_validated": True,
    }


def _evidence_request(task_payload: Mapping[str, Any], evidence_state: str) -> dict[str, Any] | None:
    if evidence_state == "verified":
        return None
    request = copy.deepcopy(
        _mapping(
            _mapping(task_payload.get("extensions"), "task.extensions").get("evidence_request"),
            "task.extensions.evidence_request",
        )
    )
    request["state"] = "required"
    request["scenario_reason"] = {
        "missing": "No evidence was supplied.",
        "stale": "Supplied evidence is outside its declared validity window.",
        "conflicted": "Fresh evidence conflicts and no resolution policy is declared.",
    }[evidence_state]
    if evidence_state == "conflicted":
        request["next_action"] = "request_explicit_conflict_adjudication"
        request["resume_when"] = "conflict_resolved == true AND evidence_verified == true"
    return request


def replay_scenario(
    scenario_name: str = "success",
    *,
    scenario_path: Path | None = None,
) -> dict[str, Any]:
    if scenario_path is None and scenario_name not in SCENARIO_NAMES:
        raise ReferenceAgentReplayError(
            f"unknown scenario {scenario_name!r}; choose one of {', '.join(SCENARIO_NAMES)}"
        )

    task_payload = _load_task()
    source_path = scenario_path if scenario_path is not None else SCENARIO_DIR / f"{scenario_name}.json"
    scenario_payload = _load_json(source_path)
    scenario = _mapping(scenario_payload.get("scenario"), "scenario")
    declared_id = scenario.get("id")
    if not isinstance(declared_id, str) or not declared_id.strip():
        raise ReferenceAgentReplayError("scenario.id must be a non-empty string")
    if scenario_path is None and declared_id != scenario_name:
        raise ReferenceAgentReplayError("scenario id does not match filename")
    scenario_name = declared_id

    base_payload = _load_json(WORLD_STATE_PATH)
    base_world_state = load_world_state(base_payload)
    base_fingerprint = base_world_state.semantic_fingerprint()

    evidence_state, accepted, observations, evidence_reason = _evidence_resolution(scenario)
    canonical, execution_result, distance_m, distance_check = _execute_distance(
        task_payload, accepted
    )
    min_distance_m = float(scenario.get("min_obstacle_distance_m", 50))

    if accepted is None:
        verification_state = "conflicted" if evidence_state == "conflicted" else "unverifiable"
    elif distance_m < min_distance_m:
        verification_state = "contradicted"
    else:
        verification_state = "satisfied"

    domain_state: dict[str, object] = {
        "min_obstacle_distance_m": min_distance_m,
    }
    human_review_approved = scenario.get("human_review_approved")
    if isinstance(human_review_approved, bool):
        domain_state["human_review_approved"] = human_review_approved
    if accepted is not None:
        domain_state["evidence_verified"] = True
    control = evaluate_control_profile(canonical, execution_result, domain_state)

    observation_state: WorldState | None = None
    successor: WorldState | None = None
    registered_impact_bundle: dict[str, Any] | None = None
    if accepted is not None:
        observation_state = _materialize_observation_state(base_payload, scenario, accepted)
        registered_impact_bundle = _build_registered_impact_bundle(
            observation_state,
            accepted,
            distance_m,
            min_distance_m,
            scenario,
        )
        successor = _materialize_reevaluated_successor(
            observation_state,
            scenario,
            accepted,
            distance_m,
            min_distance_m,
        )

    observation_records = []
    for observation in observations:
        payload = observation.to_dict()
        observation_records.append(
            {
                "observation_id": observation.observation_id,
                "source_reference": observation.source.reference,
                "producer_id": observation.producer.id,
                "producer_version": observation.producer.version,
                "valid_until": observation.claims[0].valid_until,
                "claim_value": observation.claims[0].value,
                "content_sha256": _sha256(payload),
            }
        )

    report_update_eligible = (
        verification_state == "satisfied"
        and control.state == "satisfied"
        and control.gate_satisfied is True
    )

    request = _evidence_request(task_payload, evidence_state)
    if report_update_eligible:
        next_action = "external_workflow_may_refresh_report_after_explicit_write"
    elif verification_state == "contradicted":
        next_action = "retain_block_and_route_to_human_review"
    elif request is not None:
        next_action = str(request["next_action"])
    else:
        next_action = "hold_and_reverify"

    result: dict[str, Any] = {
        "reference_agent": {
            "schema_version": "0.1",
            "scenario": scenario_name,
            "request": REQUEST_PATH.read_text(encoding="utf-8").strip(),
            "proposal": {
                "task_id": canonical.metadata.id,
                "facility_id": "FAC-001",
                "scope": "obstacle_clearance_only",
                "proposal_is_world_state": False,
            },
            "baseline": {
                "world_state_id": base_world_state.world_state_id,
                "revision": base_world_state.revision,
                "semantic_fingerprint": base_fingerprint,
            },
            "evidence": {
                "state": evidence_state,
                "reason": evidence_reason,
                "accepted_observation_id": accepted.observation_id if accepted else None,
                "observations": observation_records,
                "external_truth_fetched_by_core": False,
            },
            "verification": {
                "state": verification_state,
                "distance_m": distance_m,
                "min_obstacle_distance_m": min_distance_m,
                "local_check": _normalized_check(distance_check),
            },
            "world_state_update": {
                "observation_state_materialized": observation_state is not None,
                "observation_state_revision": observation_state.revision if observation_state else None,
                "observation_state_semantic_fingerprint": observation_state.semantic_fingerprint()
                if observation_state
                else None,
                "observation_state": observation_state.to_dict() if observation_state else None,
                "successor_materialized": successor is not None,
                "baseline_immutable": base_world_state.semantic_fingerprint() == base_fingerprint,
                "successor_revision": successor.revision if successor else None,
                "successor_semantic_fingerprint": successor.semantic_fingerprint()
                if successor
                else None,
                "successor": successor.to_dict() if successor else None,
            },
            "impact_scope": _impact_graph(evidence_state),
            "registered_impact_bundle": registered_impact_bundle,
            "evidence_request": request,
            "control_evaluation": control.to_dict()["control_evaluation"],
            "decision_assurance": {
                "assessment_refresh_eligible": report_update_eligible,
                "report_update_eligible": report_update_eligible,
                "human_confirmation_required": True,
                "production_write_performed": False,
                "production_report_refreshed": False,
                "action_authorized": False,
                "action_executed": False,
                "next_action": next_action,
            },
        }
    }
    result["reference_agent"]["replay_fingerprint"] = _sha256(result)
    return result


def _assert_expected(scenario_name: str, result: Mapping[str, Any]) -> None:
    scenario = _mapping(
        _load_json(SCENARIO_DIR / f"{scenario_name}.json").get("scenario"), "scenario"
    )
    expected = _mapping(scenario.get("expected"), "scenario.expected")
    body = _mapping(result.get("reference_agent"), "reference_agent")
    verification = _mapping(body.get("verification"), "reference_agent.verification")
    control = _mapping(body.get("control_evaluation"), "reference_agent.control_evaluation")
    decision = _mapping(body.get("decision_assurance"), "reference_agent.decision_assurance")
    state_update = _mapping(body.get("world_state_update"), "reference_agent.world_state_update")

    actual = {
        "verification_state": verification.get("state"),
        "control_state": control.get("state"),
        "distance_m": verification.get("distance_m"),
        "report_update_eligible": decision.get("report_update_eligible"),
        "successor_materialized": state_update.get("successor_materialized"),
        "evidence_request_required": body.get("evidence_request") is not None,
    }
    for key, expected_value in expected.items():
        if actual.get(key) != expected_value:
            raise ReferenceAgentReplayError(
                f"scenario {scenario_name}: expected {key}={expected_value!r}, got {actual.get(key)!r}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--scenario",
        choices=SCENARIO_NAMES,
        help="fixed scenario to replay; defaults to success when no source is supplied",
    )
    source.add_argument(
        "--scenario-file",
        type=Path,
        help="developer-supplied scenario JSON using the same scenario envelope",
    )
    parser.add_argument(
        "--check-expected",
        action="store_true",
        help="compare a fixed built-in scenario to its acceptance fields",
    )
    args = parser.parse_args()
    if args.scenario_file is not None and args.check_expected:
        parser.error("--check-expected is only available with built-in fixed scenarios")
    scenario_name = args.scenario or "success"
    result = replay_scenario(scenario_name, scenario_path=args.scenario_file)
    if args.check_expected:
        _assert_expected(scenario_name, result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
