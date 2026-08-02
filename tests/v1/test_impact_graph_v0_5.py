"""Contract tests for GeoTask Impact Graph v0.1."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import geotask_core
import geotask_core.v1 as v1
from geotask_core.v1.artifact_validation import validate_artifact_payload
from geotask_core.v1.correction_request import load_correction_request
from geotask_core.v1.discrepancy_report import load_discrepancy_report
from geotask_core.v1.impact_graph import (
    IMPACT_GRAPH_SCHEMA_ID,
    IMPACT_GRAPH_SCHEMA_VERSION,
    ImpactGraphFormatError,
    load_impact_graph,
    validate_impact_graph_bindings,
)
from geotask_core.v1.world_state import load_world_state


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "examples" / "core"
EXAMPLE = CORE / "impact_graph_uav_recheck.json"
WORLD_STATE = CORE / "world_state_uav_separation_recheck.json"
DISCREPANCY_REPORT = CORE / "discrepancy_report_uav_recheck.json"
CORRECTION_REQUEST = CORE / "correction_request_uav_recheck.json"
SCHEMA = ROOT / "schemas" / "geotask-impact-graph-v0.1.schema.json"
EXPECTED_FINGERPRINT = "ad8fcc1a18f334b36608110f279615f5dfaee8e7e294e0460a2093b649a32713"


def _payload() -> dict[str, object]:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def _world_state():
    return load_world_state(json.loads(WORLD_STATE.read_text(encoding="utf-8")))


def _report():
    return load_discrepancy_report(
        json.loads(DISCREPANCY_REPORT.read_text(encoding="utf-8"))
    )


def _request():
    return load_correction_request(
        json.loads(CORRECTION_REQUEST.read_text(encoding="utf-8"))
    )


def _contents() -> dict[str, bytes]:
    return {
        "base-world-state": WORLD_STATE.read_bytes(),
        "discrepancy-uav-recheck": DISCREPANCY_REPORT.read_bytes(),
        "correction-uav-recheck": CORRECTION_REQUEST.read_bytes(),
    }


def _bind(graph) -> None:
    validate_impact_graph_bindings(
        graph,
        _world_state(),
        {"discrepancy-uav-recheck": _report()},
        {"correction-uav-recheck": _request()},
        _contents(),
    )


def test_impact_graph_example_loads_round_trips_and_binds() -> None:
    graph = load_impact_graph(_payload())

    assert graph.graph_id == "fictional-uav-separation-impact-graph"
    assert graph.state == "blocked"
    assert graph.world_state.revision == 2
    assert len(graph.nodes) == 8
    assert len(graph.edges) == 9
    assert len(graph.reevaluation_targets) == 2
    assert graph.semantic_fingerprint() == EXPECTED_FINGERPRINT
    assert load_impact_graph(graph.to_dict()) == graph
    _bind(graph)


def test_impact_graph_schema_is_valid_and_accepts_example() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert schema["$id"] == IMPACT_GRAPH_SCHEMA_ID
    assert schema["properties"]["impact_graph"]["$ref"] == "#/$defs/impactGraph"
    assert list(Draft202012Validator(schema).iter_errors(_payload())) == []
    assert _payload()["impact_graph"]["schema_version"] == IMPACT_GRAPH_SCHEMA_VERSION


def test_impact_graph_unified_validation_preserves_execution_boundaries() -> None:
    validation = validate_artifact_payload(
        "geotask.impact-graph",
        _payload(),
        file=EXAMPLE.as_posix(),
    )

    assert validation.valid is True
    assert validation.schema_verified is True
    summary = validation.summary
    assert summary["graph_id"] == "fictional-uav-separation-impact-graph"
    assert summary["state"] == "blocked"
    assert summary["node_count"] == 8
    assert summary["edge_count"] == 9
    assert summary["reevaluation_target_count"] == 2
    assert summary["semantic_fingerprint"] == EXPECTED_FINGERPRINT
    for key in (
        "world_state_binding_verified",
        "artifact_bindings_verified",
        "source_entities_verified",
        "edge_semantics_verified",
        "impact_computed",
        "propagation_executed",
        "corrections_applied",
        "successor_world_state_materialized",
        "reevaluation_executed",
        "outputs_released",
        "external_truth_verified",
        "action_authorized",
    ):
        assert summary[key] is False


def test_impact_graph_fingerprint_is_collection_order_invariant() -> None:
    original = _payload()
    reordered = copy.deepcopy(original)
    body = reordered["impact_graph"]
    for key in (
        "artifact_refs",
        "entity_refs",
        "root_node_refs",
        "nodes",
        "edges",
        "reevaluation_targets",
        "blocked_outputs",
        "blocked_actions",
    ):
        body[key].reverse()
    for node in body["nodes"]:
        node["basis_refs"].reverse()
    for edge in body["edges"]:
        edge["basis_refs"].reverse()
    for target in body["reevaluation_targets"]:
        target["input_node_refs"].reverse()
        target["prerequisite_node_refs"].reverse()
        target["basis_refs"].reverse()

    assert load_impact_graph(original).semantic_fingerprint() == (
        load_impact_graph(reordered).semantic_fingerprint()
    )


def test_impact_graph_rejects_cycles_and_unreachable_nodes() -> None:
    payload = _payload()
    edge = payload["impact_graph"]["edges"][0]
    edge["from_node"] = "node-route-action"
    edge["to_node"] = "node-discrepancy"
    with pytest.raises(ImpactGraphFormatError, match="cycle"):
        load_impact_graph(payload)

    payload = _payload()
    payload["impact_graph"]["edges"] = [
        edge
        for edge in payload["impact_graph"]["edges"]
        if edge["to_node"] != "node-route-action"
    ]
    with pytest.raises(ImpactGraphFormatError, match="reachable"):
        load_impact_graph(payload)


def test_impact_graph_rejects_root_and_blocked_state_mismatch() -> None:
    payload = _payload()
    payload["impact_graph"]["nodes"][0]["impact_state"] = "affected"
    with pytest.raises(ImpactGraphFormatError, match="root nodes"):
        load_impact_graph(payload)

    payload = _payload()
    payload["impact_graph"]["blocked_outputs"] = []
    payload["impact_graph"]["blocked_actions"] = []
    for node in payload["impact_graph"]["nodes"]:
        if node["impact_state"] == "blocked":
            node["impact_state"] = "affected"
    for target in payload["impact_graph"]["reevaluation_targets"]:
        if target["state"] == "blocked":
            target["state"] = "required"
    with pytest.raises(ImpactGraphFormatError, match="state 'blocked'"):
        load_impact_graph(payload)


def test_impact_graph_rejects_duplicate_identity_and_invalid_target_ancestry() -> None:
    payload = _payload()
    duplicate = copy.deepcopy(payload["impact_graph"]["nodes"][3])
    duplicate["id"] = "duplicate-delay-path"
    payload["impact_graph"]["nodes"].append(duplicate)
    with pytest.raises(ImpactGraphFormatError, match="duplicates node identity"):
        load_impact_graph(payload)

    payload = _payload()
    payload["impact_graph"]["reevaluation_targets"][0]["input_node_refs"] = [
        "node-route-action"
    ]
    with pytest.raises(ImpactGraphFormatError, match="strict graph ancestor"):
        load_impact_graph(payload)


def test_impact_graph_binding_rejects_world_state_and_exact_bytes_mismatch() -> None:
    payload = _payload()
    payload["impact_graph"]["world_state"]["semantic_fingerprint"] = "0" * 64
    graph = load_impact_graph(payload)
    with pytest.raises(ImpactGraphFormatError, match="does not match bound World State"):
        _bind(graph)

    graph = load_impact_graph(_payload())
    contents = _contents()
    contents["correction-uav-recheck"] += b"\n"
    with pytest.raises(ImpactGraphFormatError, match="SHA-256 mismatch"):
        validate_impact_graph_bindings(
            graph,
            _world_state(),
            {"discrepancy-uav-recheck": _report()},
            {"correction-uav-recheck": _request()},
            contents,
        )


def test_impact_graph_binding_rejects_missing_entity_and_ungrounded_identity() -> None:
    payload = _payload()
    payload["impact_graph"]["entity_refs"][0]["entity_id"] = "missing-discrepancy"
    graph = load_impact_graph(payload)
    with pytest.raises(ImpactGraphFormatError, match="absent from bound"):
        _bind(graph)

    payload = _payload()
    node = next(
        item
        for item in payload["impact_graph"]["nodes"]
        if item["id"] == "node-temporal-conflict"
    )
    node["identity"] = "invented_assertion"
    graph = load_impact_graph(payload)
    with pytest.raises(ImpactGraphFormatError, match="not grounded"):
        _bind(graph)


def test_impact_graph_binding_rejects_invalid_change_and_discrepancy_edges() -> None:
    payload = _payload()
    edge = next(
        item
        for item in payload["impact_graph"]["edges"]
        if item["id"] == "edge-delay-change-updates-path"
    )
    edge["to_node"] = "node-separation-path"
    payload["impact_graph"]["edges"].append(
        {
            "id": "edge-keep-delay-path-reachable",
            "kind": "affects",
            "from_node": "node-discrepancy",
            "to_node": "node-delay-path",
            "state": "confirmed",
            "reason": "Keep the graph structurally reachable while testing change binding.",
            "basis_refs": ["discrepancy-uav-recheck"],
        }
    )
    graph = load_impact_graph(payload)
    with pytest.raises(ImpactGraphFormatError, match="does not match correction change"):
        _bind(graph)

    payload = _payload()
    payload["impact_graph"]["nodes"].append(
        {
            "id": "node-correction-artifact",
            "kind": "artifact",
            "identity": "correction-uav-recheck",
            "impact_state": "affected",
            "reason": "A globally bound artifact that is not a basis artifact of this discrepancy.",
            "basis_refs": ["correction-uav-recheck"],
        }
    )
    edge = next(
        item
        for item in payload["impact_graph"]["edges"]
        if item["id"] == "edge-discrepancy-invalidates-separation"
    )
    edge["to_node"] = "node-correction-artifact"
    edge["basis_refs"] = [
        "correction-uav-recheck",
        "discrepancy-uav-recheck",
    ]
    graph = load_impact_graph(payload)
    with pytest.raises(ImpactGraphFormatError, match="absent from discrepancy"):
        _bind(graph)


def test_impact_graph_binding_rejects_change_not_linked_to_discrepancy() -> None:
    payload = _payload()
    payload["impact_graph"]["entity_refs"][0]["entity_id"] = (
        "initial-temporal-result-stale"
    )
    invalidates = next(
        item
        for item in payload["impact_graph"]["edges"]
        if item["id"] == "edge-discrepancy-invalidates-separation"
    )
    invalidates["to_node"] = "node-continuation-output"
    graph = load_impact_graph(payload)
    with pytest.raises(ImpactGraphFormatError, match="not bound to source discrepancy"):
        _bind(graph)


def test_impact_graph_rejects_state_kind_and_root_indegree_errors() -> None:
    payload = _payload()
    node = next(
        item
        for item in payload["impact_graph"]["nodes"]
        if item["id"] == "node-delay-path"
    )
    node["impact_state"] = "blocked"
    with pytest.raises(ImpactGraphFormatError, match="limited to output or action"):
        load_impact_graph(payload)

    payload = _payload()
    node = next(
        item
        for item in payload["impact_graph"]["nodes"]
        if item["id"] == "node-change-delay"
    )
    node["impact_state"] = "root"
    payload["impact_graph"]["root_node_refs"].append("node-change-delay")
    with pytest.raises(ImpactGraphFormatError, match="must not have incoming edges"):
        load_impact_graph(payload)


def test_impact_graph_blocked_lists_exactly_match_blocked_nodes() -> None:
    payload = _payload()
    payload["impact_graph"]["nodes"].append(
        {
            "id": "node-undisclosed-blocked-output",
            "kind": "output",
            "identity": "another_blocked_output",
            "impact_state": "blocked",
            "reason": "A blocked node must not be omitted from the blocked output inventory.",
            "basis_refs": [
                "correction-uav-recheck",
                "discrepancy-uav-recheck",
            ],
        }
    )
    payload["impact_graph"]["edges"].append(
        {
            "id": "edge-assertion-blocks-undisclosed-output",
            "kind": "blocks",
            "from_node": "node-temporal-conflict",
            "to_node": "node-undisclosed-blocked-output",
            "state": "confirmed",
            "reason": "Keep the omitted blocked node reachable for structural validation.",
            "basis_refs": [
                "correction-uav-recheck",
                "discrepancy-uav-recheck",
            ],
        }
    )
    with pytest.raises(ImpactGraphFormatError, match="exactly enumerate"):
        load_impact_graph(payload)


def test_impact_graph_binding_rejects_unsupported_edge_shape_and_missing_source_basis() -> None:
    payload = _payload()
    edge = next(
        item
        for item in payload["impact_graph"]["edges"]
        if item["id"] == "edge-delay-affects-separation"
    )
    edge["from_node"] = "node-change-delay"
    payload["impact_graph"]["edges"].append(
        {
            "id": "edge-keep-delay-input-ancestry",
            "kind": "affects",
            "from_node": "node-delay-path",
            "to_node": "node-separation-path",
            "state": "confirmed",
            "reason": "Keep the declared input path as an ancestor while testing edge shape.",
            "basis_refs": [
                "correction-uav-recheck",
                "discrepancy-uav-recheck",
            ],
        }
    )
    graph = load_impact_graph(payload)
    with pytest.raises(ImpactGraphFormatError, match="unsupported affects edge shape"):
        _bind(graph)

    payload = _payload()
    edge = next(
        item
        for item in payload["impact_graph"]["edges"]
        if item["id"] == "edge-delay-change-updates-path"
    )
    edge["basis_refs"] = ["discrepancy-uav-recheck"]
    graph = load_impact_graph(payload)
    with pytest.raises(ImpactGraphFormatError, match="bound Correction Request ref"):
        _bind(graph)


def test_impact_graph_rejects_inconsistent_target_state_and_overlapping_dependencies() -> None:
    payload = _payload()
    payload["impact_graph"]["reevaluation_targets"][1]["state"] = "required"
    with pytest.raises(ImpactGraphFormatError, match="required targets"):
        load_impact_graph(payload)

    payload = _payload()
    target = payload["impact_graph"]["reevaluation_targets"][0]
    target["prerequisite_node_refs"].append(target["input_node_refs"][0])
    with pytest.raises(ImpactGraphFormatError, match="must be disjoint"):
        load_impact_graph(payload)


def test_impact_graph_public_python_namespaces_export_contract() -> None:
    for namespace in (geotask_core, v1):
        assert namespace.IMPACT_GRAPH_ARTIFACT_ID == "geotask.impact-graph"
        assert namespace.IMPACT_GRAPH_SCHEMA_ID == IMPACT_GRAPH_SCHEMA_ID
        assert namespace.IMPACT_GRAPH_SCHEMA_VERSION == "0.1"
        assert namespace.IMPACT_GRAPH_FORMAT_VERSION == "0.1"
        assert namespace.load_impact_graph is load_impact_graph
        assert namespace.validate_impact_graph_bindings is validate_impact_graph_bindings
        assert namespace.ImpactGraph.__name__ == "ImpactGraph"
