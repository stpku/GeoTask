#!/usr/bin/env python3
"""Build the fictional GT24 temporary no-fly-zone impact scope.

This case-specific builder binds one fictional notice Observation to a World State,
records the stale clearance as a Discrepancy Report, and authors a finite Impact
Graph for the caller-declared affected route, mission, approval, and launch action.
It validates exact bytes and declared graph scope. It does not compute geometry,
discover impact, execute propagation, rerun checks, release outputs, verify external
truth, or authorize an action.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence

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
from geotask_core.v1.observation import Observation, load_observation
from geotask_core.v1.world_state import WorldState, load_world_state


class GT24BuildError(ValueError):
    """Raised when the explicit GT24 impact declaration is incomplete."""


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise GT24BuildError(f"{path}: must be an object")
    return value


def _sequence(value: object, path: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise GT24BuildError(f"{path}: must be an array")
    return value


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GT24BuildError(f"{path}: must be a non-empty string")
    return value


def _case_file(scenario_path: Path, filename: object, path: str) -> Path:
    name = _string(filename, path)
    base = scenario_path.parent.resolve()
    candidate = (base / name).resolve()
    if candidate.parent != base:
        raise GT24BuildError(f"{path}: must stay in {base}")
    return candidate


def _pretty_bytes(payload: Mapping[str, object]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _relation_value(world_state: WorldState, relation_id: str) -> object:
    matches = [item for item in world_state.relations if item.id == relation_id]
    if len(matches) != 1:
        raise GT24BuildError(f"relation {relation_id!r}: must exist exactly once")
    return matches[0].value


def _load_inputs(
    scenario_path: Path,
    scenario: Mapping[str, object],
) -> tuple[Observation, bytes, WorldState, bytes]:
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

    if observation.observation_id not in world_state.observation_refs:
        raise GT24BuildError(
            "world_state.observation_refs: must include the temporary no-fly-zone Observation"
        )
    if observation.source.reference not in world_state.evidence_refs:
        raise GT24BuildError(
            "world_state.evidence_refs: must include the temporary no-fly-zone notice"
        )
    return observation, observation_bytes, world_state, world_state_bytes


def _build_discrepancy(
    scenario: Mapping[str, object],
    observation: Observation,
    observation_bytes: bytes,
    world_state: WorldState,
) -> tuple[DiscrepancyReport, bytes]:
    config = _mapping(scenario.get("discrepancy"), "scenario.discrepancy")
    observation_ref_id = "notice-observation-gt24"
    payload = {
        "discrepancy_report": {
            "schema_id": "https://stpku.github.io/GeoTask/schemas/geotask-discrepancy-report-v0.1.schema.json",
            "schema_version": "0.1",
            "report_id": _string(config.get("report_id"), "scenario.discrepancy.report_id"),
            "recorded_at": _string(
                config.get("recorded_at"), "scenario.discrepancy.recorded_at"
            ),
            "state": "confirmed",
            "severity": "high",
            "reason": (
                "The temporary no-fly-zone notice makes the earlier medical-route "
                "dispatch and approval conclusions stale, while the independent "
                "inspection route remains outside the declared impact scope."
            ),
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
                    "ref_id": observation_ref_id,
                    "artifact_id": "geotask.observation",
                    "schema_version": "0.1",
                    "instance_id": observation.observation_id,
                    "content_sha256": _sha256(observation_bytes),
                }
            ],
            "discrepancies": [
                {
                    "id": _string(
                        config.get("finding_id"), "scenario.discrepancy.finding_id"
                    ),
                    "kind": "stale_claim",
                    "state": "confirmed",
                    "severity": "high",
                    "subject_kind": "attribute",
                    "subject_path": _string(
                        config.get("subject_path"),
                        "scenario.discrepancy.subject_path",
                    ),
                    "summary": (
                        "The medical mission clearance predates an active temporary "
                        "no-fly zone intersecting its declared route."
                    ),
                    "reason": (
                        "The World State records route-medical-a as intersecting the "
                        "active zone during the mission window, so prior dispatch and "
                        "approval conclusions cannot be reused without recheck."
                    ),
                    "basis_refs": [observation_ref_id],
                    "observation_refs": [observation.observation_id],
                    "evidence_refs": [observation.source.reference],
                    "observed": "clear_before_zone_notice",
                    "impact": {
                        "state": "confirmed",
                        "reason": (
                            "The declared dependency chain reaches the medical route "
                            "assertions, mission dispatch output, approval output, and "
                            "launch action, but not the independent inspection chain."
                        ),
                        "affected_paths": [
                            "/relations/route-medical-a-zone-riverside/value",
                            "/objects/mission-medical-17/attributes/dispatch_clearance/value",
                            "/objects/approval-medical-17/attributes/decision/value",
                        ],
                        "affected_assertion_refs": [
                            "route_medical_a_avoids_active_no_fly_zone",
                            "mission_medical_17_dispatch_allowed",
                        ],
                        "affected_output_refs": [
                            "mission_medical_17_dispatch_clearance",
                            "approval_medical_17_release_decision",
                        ],
                        "affected_action_refs": ["launch_mission_medical_17"],
                    },
                    "correction_scope": {
                        "state": "need_review",
                        "reason": (
                            "A later bounded correction may update the medical mission "
                            "and approval decisions, but must not rewrite the notice or "
                            "route geometry as part of this impact-mapping step."
                        ),
                        "mutable_paths": [
                            "/objects/mission-medical-17/attributes/dispatch_clearance/value",
                            "/objects/approval-medical-17/attributes/decision/value",
                        ],
                        "immutable_paths": [
                            "/objects/zone-riverside-temporary-gt24/attributes/polygon_local_xy/value",
                            "/objects/route-medical-a/attributes/polyline_local_xy/value",
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
        {observation_ref_id: observation_bytes},
    )
    report_bytes = _pretty_bytes(report.to_dict())
    return report, report_bytes


def _build_impact_graph(
    scenario: Mapping[str, object],
    world_state: WorldState,
    world_state_bytes: bytes,
    report: DiscrepancyReport,
    report_bytes: bytes,
) -> tuple[ImpactGraph, bytes]:
    config = _mapping(scenario.get("impact_graph"), "scenario.impact_graph")
    discrepancy_ref_id = "discrepancy-gt24"
    basis = [discrepancy_ref_id]
    payload = {
        "impact_graph": {
            "schema_id": "https://stpku.github.io/GeoTask/schemas/geotask-impact-graph-v0.1.schema.json",
            "schema_version": "0.1",
            "graph_id": _string(config.get("graph_id"), "scenario.impact_graph.graph_id"),
            "recorded_at": _string(
                config.get("recorded_at"), "scenario.impact_graph.recorded_at"
            ),
            "state": "blocked",
            "reason": (
                "The caller-declared dependency chain maps the active temporary "
                "no-fly zone to one medical route, its mission and approval outputs, "
                "and the launch action; unrelated inspection operations are excluded."
            ),
            "world_state": {
                "ref_id": "world-state-gt24",
                "artifact_id": "geotask.world-state",
                "schema_version": "0.1",
                "world_state_id": world_state.world_state_id,
                "revision": world_state.revision,
                "as_of": world_state.as_of,
                "semantic_fingerprint": world_state.semantic_fingerprint(),
                "content_sha256": _sha256(world_state_bytes),
            },
            "artifact_refs": [
                {
                    "ref_id": discrepancy_ref_id,
                    "artifact_id": "geotask.discrepancy-report",
                    "schema_version": "0.1",
                    "instance_id": report.report_id,
                    "content_sha256": _sha256(report_bytes),
                }
            ],
            "entity_refs": [
                {
                    "id": "entity-route-medical-clearance-stale",
                    "kind": "discrepancy",
                    "artifact_ref": discrepancy_ref_id,
                    "entity_id": "route-medical-a-clearance-stale",
                }
            ],
            "root_node_refs": ["node-medical-clearance-stale"],
            "nodes": [
                {
                    "id": "node-medical-clearance-stale",
                    "kind": "discrepancy",
                    "identity": "entity-route-medical-clearance-stale",
                    "impact_state": "root",
                    "reason": "The stale medical clearance is the declared root impact.",
                    "basis_refs": basis,
                    "entity_ref": "entity-route-medical-clearance-stale",
                },
                {
                    "id": "node-route-medical-intersection",
                    "kind": "world_state_path",
                    "identity": "/relations/route-medical-a-zone-riverside/value",
                    "impact_state": "affected",
                    "reason": "The medical route intersects the active temporary zone.",
                    "basis_refs": basis,
                },
                {
                    "id": "node-route-medical-assertion",
                    "kind": "assertion",
                    "identity": "route_medical_a_avoids_active_no_fly_zone",
                    "impact_state": "requires_recheck",
                    "reason": "The route-clearance assertion must be evaluated again.",
                    "basis_refs": basis,
                },
                {
                    "id": "node-mission-medical-assertion",
                    "kind": "assertion",
                    "identity": "mission_medical_17_dispatch_allowed",
                    "impact_state": "requires_recheck",
                    "reason": "Mission dispatch eligibility depends on the affected route.",
                    "basis_refs": basis,
                },
                {
                    "id": "node-mission-medical-output",
                    "kind": "output",
                    "identity": "mission_medical_17_dispatch_clearance",
                    "impact_state": "blocked",
                    "reason": "The mission dispatch output remains blocked pending recheck.",
                    "basis_refs": basis,
                },
                {
                    "id": "node-approval-medical-output",
                    "kind": "output",
                    "identity": "approval_medical_17_release_decision",
                    "impact_state": "blocked",
                    "reason": "The approval conclusion cannot be reused while dispatch is blocked.",
                    "basis_refs": basis,
                },
                {
                    "id": "node-launch-medical-action",
                    "kind": "action",
                    "identity": "launch_mission_medical_17",
                    "impact_state": "blocked",
                    "reason": "Launch remains blocked until the dependent outputs are released.",
                    "basis_refs": basis,
                },
            ],
            "edges": [
                {
                    "id": "edge-discrepancy-invalidates-route",
                    "kind": "invalidates",
                    "from_node": "node-medical-clearance-stale",
                    "to_node": "node-route-medical-intersection",
                    "state": "confirmed",
                    "reason": "The notice invalidates reuse of the prior route clearance.",
                    "basis_refs": basis,
                },
                {
                    "id": "edge-route-rechecks-route-assertion",
                    "kind": "requires_recheck",
                    "from_node": "node-route-medical-intersection",
                    "to_node": "node-route-medical-assertion",
                    "state": "confirmed",
                    "reason": "The changed route-zone relation requires route recheck.",
                    "basis_refs": basis,
                },
                {
                    "id": "edge-route-rechecks-mission-assertion",
                    "kind": "requires_recheck",
                    "from_node": "node-route-medical-intersection",
                    "to_node": "node-mission-medical-assertion",
                    "state": "confirmed",
                    "reason": "The affected route requires mission dispatch recheck.",
                    "basis_refs": basis,
                },
                {
                    "id": "edge-route-assertion-blocks-mission-output",
                    "kind": "blocks",
                    "from_node": "node-route-medical-assertion",
                    "to_node": "node-mission-medical-output",
                    "state": "confirmed",
                    "reason": "Unresolved route clearance blocks mission dispatch clearance.",
                    "basis_refs": basis,
                },
                {
                    "id": "edge-mission-assertion-blocks-mission-output",
                    "kind": "blocks",
                    "from_node": "node-mission-medical-assertion",
                    "to_node": "node-mission-medical-output",
                    "state": "confirmed",
                    "reason": "Unresolved mission eligibility blocks the dispatch output.",
                    "basis_refs": basis,
                },
                {
                    "id": "edge-mission-output-blocks-approval-output",
                    "kind": "blocks",
                    "from_node": "node-mission-medical-output",
                    "to_node": "node-approval-medical-output",
                    "state": "confirmed",
                    "reason": "A blocked dispatch output invalidates reuse of the approval conclusion.",
                    "basis_refs": basis,
                },
                {
                    "id": "edge-approval-output-blocks-launch",
                    "kind": "blocks",
                    "from_node": "node-approval-medical-output",
                    "to_node": "node-launch-medical-action",
                    "state": "confirmed",
                    "reason": "A blocked approval conclusion cannot authorize launch.",
                    "basis_refs": basis,
                },
            ],
            "reevaluation_targets": [
                {
                    "id": "target-route-medical-assertion",
                    "node_ref": "node-route-medical-assertion",
                    "state": "required",
                    "reason": "Recheck route clearance against the active zone.",
                    "input_node_refs": ["node-route-medical-intersection"],
                    "prerequisite_node_refs": [],
                    "basis_refs": basis,
                },
                {
                    "id": "target-mission-medical-assertion",
                    "node_ref": "node-mission-medical-assertion",
                    "state": "required",
                    "reason": "Recheck mission dispatch eligibility using the affected route.",
                    "input_node_refs": ["node-route-medical-intersection"],
                    "prerequisite_node_refs": [],
                    "basis_refs": basis,
                },
                {
                    "id": "target-mission-medical-output",
                    "node_ref": "node-mission-medical-output",
                    "state": "blocked",
                    "reason": "Dispatch clearance remains blocked until both assertions complete.",
                    "input_node_refs": ["node-route-medical-intersection"],
                    "prerequisite_node_refs": [
                        "node-route-medical-assertion",
                        "node-mission-medical-assertion",
                    ],
                    "basis_refs": basis,
                },
                {
                    "id": "target-approval-medical-output",
                    "node_ref": "node-approval-medical-output",
                    "state": "blocked",
                    "reason": "The approval conclusion remains blocked until dispatch is reevaluated.",
                    "input_node_refs": ["node-route-medical-intersection"],
                    "prerequisite_node_refs": ["node-mission-medical-output"],
                    "basis_refs": basis,
                },
            ],
            "blocked_outputs": [
                "mission_medical_17_dispatch_clearance",
                "approval_medical_17_release_decision",
            ],
            "blocked_actions": ["launch_mission_medical_17"],
        }
    }
    graph = load_impact_graph(payload)
    validate_impact_graph_bindings(
        graph,
        world_state,
        {discrepancy_ref_id: report},
        {},
        {
            "world-state-gt24": world_state_bytes,
            discrepancy_ref_id: report_bytes,
        },
    )
    graph_bytes = _pretty_bytes(graph.to_dict())
    return graph, graph_bytes


def _validate_declared_scope(
    scenario: Mapping[str, object],
    world_state: WorldState,
    graph: ImpactGraph,
) -> None:
    scope = _mapping(scenario.get("declared_scope"), "scenario.declared_scope")
    impacted = {
        _string(item, f"scenario.declared_scope.impacted[{index}]")
        for index, item in enumerate(
            _sequence(scope.get("impacted"), "scenario.declared_scope.impacted")
        )
    }
    unaffected = {
        _string(item, f"scenario.declared_scope.unaffected[{index}]")
        for index, item in enumerate(
            _sequence(scope.get("unaffected"), "scenario.declared_scope.unaffected")
        )
    }
    if impacted & unaffected:
        raise GT24BuildError("declared_scope: impacted and unaffected sets must be disjoint")

    actual = {
        f"{node.kind}:{node.identity}"
        for node in graph.nodes
        if node.kind != "discrepancy"
    }
    if actual != impacted:
        raise GT24BuildError(
            f"declared impacted scope mismatch: missing={sorted(impacted - actual)}, "
            f"extra={sorted(actual - impacted)}"
        )
    leaked = sorted(actual & unaffected)
    if leaked:
        raise GT24BuildError(f"unaffected identities leaked into impact graph: {leaked}")

    if _relation_value(world_state, "route-medical-a-zone-riverside") is not True:
        raise GT24BuildError("route-medical-a must be declared as intersecting the active zone")
    if _relation_value(world_state, "route-inspection-b-zone-riverside") is not False:
        raise GT24BuildError("route-inspection-b must remain outside the active zone")


def build_gt24_impact_scope(
    scenario_path: str | Path,
) -> tuple[WorldState, DiscrepancyReport, ImpactGraph, bytes, bytes]:
    """Build and validate the fixed GT24 discrepancy and declared impact graph."""

    path = Path(scenario_path).resolve()
    root = _mapping(json.loads(path.read_text(encoding="utf-8")), "root")
    scenario = _mapping(root.get("scenario"), "scenario")
    observation, observation_bytes, world_state, world_state_bytes = _load_inputs(
        path, scenario
    )
    report, report_bytes = _build_discrepancy(
        scenario,
        observation,
        observation_bytes,
        world_state,
    )
    graph, graph_bytes = _build_impact_graph(
        scenario,
        world_state,
        world_state_bytes,
        report,
        report_bytes,
    )
    _validate_declared_scope(scenario, world_state, graph)
    return world_state, report, graph, report_bytes, graph_bytes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "scenario",
        nargs="?",
        default=str(Path(__file__).with_name("gt24_temporary_no_fly_zone_impact.json")),
    )
    parser.add_argument("--discrepancy-output")
    parser.add_argument("--impact-output")
    args = parser.parse_args()

    _, report, graph, report_bytes, graph_bytes = build_gt24_impact_scope(args.scenario)
    wrote = False
    if args.discrepancy_output:
        Path(args.discrepancy_output).write_bytes(report_bytes)
        wrote = True
    if args.impact_output:
        Path(args.impact_output).write_bytes(graph_bytes)
        wrote = True
    if not wrote:
        print(json.dumps(graph.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
