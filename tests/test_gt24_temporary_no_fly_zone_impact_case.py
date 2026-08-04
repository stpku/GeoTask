from __future__ import annotations

import copy
import importlib.util
import json
import shutil
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from geotask_core.v1.discrepancy_report import (
    load_discrepancy_report,
    validate_discrepancy_report_bindings,
)
from geotask_core.v1.impact_graph import (
    ImpactGraphFormatError,
    load_impact_graph,
    validate_impact_graph_bindings,
)
from geotask_core.v1.observation import load_observation
from geotask_core.v1.world_state import load_world_state


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "examples" / "core"
SCENARIO = CORE / "gt24_temporary_no_fly_zone_impact.json"
OBSERVATION = CORE / "observation_temporary_no_fly_zone_gt24.json"
WORLD_STATE = CORE / "world_state_temporary_no_fly_zone_gt24.json"
DISCREPANCY = CORE / "discrepancy_report_temporary_no_fly_zone_gt24.json"
IMPACT_GRAPH = CORE / "impact_graph_temporary_no_fly_zone_gt24.json"
BUILDER_PATH = CORE / "gt24_build_impact_scope.py"
OBSERVATION_SCHEMA = ROOT / "schemas" / "geotask-observation-v0.1.schema.json"
WORLD_STATE_SCHEMA = ROOT / "schemas" / "geotask-world-state-v0.1.schema.json"
DISCREPANCY_SCHEMA = ROOT / "schemas" / "geotask-discrepancy-report-v0.1.schema.json"
IMPACT_SCHEMA = ROOT / "schemas" / "geotask-impact-graph-v0.1.schema.json"


def _load_builder():
    spec = importlib.util.spec_from_file_location("gt24_builder", BUILDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILDER = _load_builder()


def _payload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_case(tmp_path: Path) -> Path:
    for filename in (
        "gt24_temporary_no_fly_zone_impact.json",
        "observation_temporary_no_fly_zone_gt24.json",
        "world_state_temporary_no_fly_zone_gt24.json",
    ):
        shutil.copy2(CORE / filename, tmp_path / filename)
    return tmp_path / "gt24_temporary_no_fly_zone_impact.json"


def _relation_value(world_state, relation_id: str):
    return next(item.value for item in world_state.relations if item.id == relation_id)


def test_gt24_source_state_discrepancy_and_impact_graph_are_strictly_valid() -> None:
    observation = load_observation(_payload(OBSERVATION))
    world_state = load_world_state(_payload(WORLD_STATE))
    report = load_discrepancy_report(_payload(DISCREPANCY))
    graph = load_impact_graph(_payload(IMPACT_GRAPH))

    for schema_path, payload_path in (
        (OBSERVATION_SCHEMA, OBSERVATION),
        (WORLD_STATE_SCHEMA, WORLD_STATE),
        (DISCREPANCY_SCHEMA, DISCREPANCY),
        (IMPACT_SCHEMA, IMPACT_GRAPH),
    ):
        schema = _payload(schema_path)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(_payload(payload_path))

    validate_discrepancy_report_bindings(
        report,
        world_state,
        {"notice-observation-gt24": OBSERVATION.read_bytes()},
    )
    validate_impact_graph_bindings(
        graph,
        world_state,
        {"discrepancy-gt24": report},
        {},
        {
            "world-state-gt24": WORLD_STATE.read_bytes(),
            "discrepancy-gt24": DISCREPANCY.read_bytes(),
        },
    )

    assert observation.observation_id == "obs-riverside-temporary-no-fly-zone-gt24"
    assert world_state.revision == 2
    assert graph.state == "blocked"


def test_gt24_builder_reproduces_fixed_artifacts_and_fingerprints() -> None:
    expected = _payload(SCENARIO)["scenario"]["expected"]
    world_state, report, graph, report_bytes, graph_bytes = BUILDER.build_gt24_impact_scope(
        SCENARIO
    )

    assert report_bytes == DISCREPANCY.read_bytes()
    assert graph_bytes == IMPACT_GRAPH.read_bytes()
    assert report.to_dict() == _payload(DISCREPANCY)
    assert graph.to_dict() == _payload(IMPACT_GRAPH)
    assert world_state.semantic_fingerprint() == expected[
        "world_state_semantic_fingerprint"
    ]
    assert report.semantic_fingerprint() == expected[
        "discrepancy_semantic_fingerprint"
    ]
    assert graph.semantic_fingerprint() == expected[
        "impact_graph_semantic_fingerprint"
    ]
    assert len(graph.nodes) == expected["impact_node_count"]
    assert len(graph.edges) == expected["impact_edge_count"]
    assert len(graph.reevaluation_targets) == expected["reevaluation_target_count"]
    assert len(graph.blocked_outputs) == expected["blocked_output_count"]
    assert len(graph.blocked_actions) == expected["blocked_action_count"]


def test_gt24_declared_scope_includes_only_medical_chain() -> None:
    scenario = _payload(SCENARIO)["scenario"]
    world_state, _, graph, _, _ = BUILDER.build_gt24_impact_scope(SCENARIO)
    actual = {
        f"{node.kind}:{node.identity}"
        for node in graph.nodes
        if node.kind != "discrepancy"
    }

    assert actual == set(scenario["declared_scope"]["impacted"])
    assert actual.isdisjoint(scenario["declared_scope"]["unaffected"])
    assert _relation_value(world_state, "route-medical-a-zone-riverside") is True
    assert _relation_value(world_state, "route-inspection-b-zone-riverside") is False
    assert "launch_mission_medical_17" in graph.blocked_actions
    assert "launch_mission_inspection_08" not in graph.blocked_actions


def test_gt24_fails_closed_when_declared_impacted_scope_is_incomplete(
    tmp_path: Path,
) -> None:
    scenario_path = _copy_case(tmp_path)
    payload = _payload(scenario_path)
    payload["scenario"]["declared_scope"]["impacted"].pop()
    scenario_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    with pytest.raises(BUILDER.GT24BuildError, match="declared impacted scope mismatch"):
        BUILDER.build_gt24_impact_scope(scenario_path)


def test_gt24_fails_closed_if_independent_route_is_marked_intersecting(
    tmp_path: Path,
) -> None:
    scenario_path = _copy_case(tmp_path)
    world_state_path = tmp_path / "world_state_temporary_no_fly_zone_gt24.json"
    payload = _payload(world_state_path)
    relation = next(
        item
        for item in payload["world_state"]["relations"]
        if item["id"] == "route-inspection-b-zone-riverside"
    )
    relation["value"] = True
    world_state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    with pytest.raises(BUILDER.GT24BuildError, match="must remain outside"):
        BUILDER.build_gt24_impact_scope(scenario_path)


def test_gt24_exact_binding_rejects_tampered_discrepancy_bytes() -> None:
    world_state = load_world_state(_payload(WORLD_STATE))
    report = load_discrepancy_report(_payload(DISCREPANCY))
    graph = load_impact_graph(_payload(IMPACT_GRAPH))

    with pytest.raises(ImpactGraphFormatError, match="SHA-256 mismatch"):
        validate_impact_graph_bindings(
            graph,
            world_state,
            {"discrepancy-gt24": report},
            {},
            {
                "world-state-gt24": WORLD_STATE.read_bytes(),
                "discrepancy-gt24": DISCREPANCY.read_bytes() + b"\n",
            },
        )


def test_gt24_graph_loader_rejects_a_cycle() -> None:
    payload = copy.deepcopy(_payload(IMPACT_GRAPH))
    payload["impact_graph"]["edges"].append(
        {
            "id": "edge-approval-output-back-to-mission-output",
            "kind": "affects",
            "from_node": "node-approval-medical-output",
            "to_node": "node-mission-medical-output",
            "state": "confirmed",
            "reason": "Synthetic back edge used only to prove cycle rejection.",
            "basis_refs": ["discrepancy-gt24"],
        }
    )

    with pytest.raises(ImpactGraphFormatError, match="cycle"):
        load_impact_graph(payload)
