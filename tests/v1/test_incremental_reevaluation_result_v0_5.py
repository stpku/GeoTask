"""Contract tests for GeoTask Incremental Reevaluation Result v0.1."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import geotask_core
import geotask_core.v1 as v1
from geotask_core.v1.artifact_validation import validate_artifact_payload
from geotask_core.v1.correction_request import load_correction_request
from geotask_core.v1.discrepancy_report import load_discrepancy_report
from geotask_core.v1.impact_graph import load_impact_graph
from geotask_core.v1.incremental_reevaluation_result import (
    INCREMENTAL_REEVALUATION_RESULT_ARTIFACT_ID,
    INCREMENTAL_REEVALUATION_RESULT_SCHEMA_ID,
    INCREMENTAL_REEVALUATION_RESULT_SCHEMA_VERSION,
    IncrementalReevaluationResultFormatError,
    load_incremental_reevaluation_result,
    validate_incremental_reevaluation_result_bindings,
)
from geotask_core.v1.result import GeotaskResult
from geotask_core.v1.world_state import load_world_state


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "examples" / "core"
EXAMPLE = CORE / "incremental_reevaluation_result_uav_recheck.json"
BASE_STATE = CORE / "world_state_uav_separation_recheck.json"
SUCCESSOR_STATE = CORE / "world_state_uav_separation_successor.json"
IMPACT_GRAPH = CORE / "impact_graph_uav_recheck.json"
CORRECTION_REQUEST = CORE / "correction_request_uav_recheck.json"
DISCREPANCY_REPORT = CORE / "discrepancy_report_uav_recheck.json"
EXECUTION_RESULT = CORE / "incremental_reevaluation_uav_execution_result.json"
SCHEMA = ROOT / "schemas" / "geotask-incremental-reevaluation-result-v0.1.schema.json"


def _json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _payload() -> dict[str, object]:
    return _json(EXAMPLE)


def _raw_json(payload: dict[str, object]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _dependencies():
    return (
        load_world_state(_json(BASE_STATE)),
        load_world_state(_json(SUCCESSOR_STATE)),
        load_impact_graph(_json(IMPACT_GRAPH)),
        load_correction_request(_json(CORRECTION_REQUEST)),
        load_discrepancy_report(_json(DISCREPANCY_REPORT)),
        GeotaskResult.from_dict(_json(EXECUTION_RESULT)),
    )


def _contents() -> dict[str, bytes]:
    return {
        "base-world-state": BASE_STATE.read_bytes(),
        "successor-world-state": SUCCESSOR_STATE.read_bytes(),
        "impact-graph-uav-recheck": IMPACT_GRAPH.read_bytes(),
        "correction-uav-recheck": CORRECTION_REQUEST.read_bytes(),
        "discrepancy-uav-recheck": DISCREPANCY_REPORT.read_bytes(),
        "result-gt16-reevaluation": EXECUTION_RESULT.read_bytes(),
    }


def _bind(
    result,
    *,
    base=None,
    successor=None,
    graph=None,
    request=None,
    report=None,
    execution=None,
    contents=None,
) -> None:
    default_base, default_successor, default_graph, default_request, default_report, default_execution = (
        _dependencies()
    )
    validate_incremental_reevaluation_result_bindings(
        result,
        base or default_base,
        successor or default_successor,
        graph or default_graph,
        {"correction-uav-recheck": request or default_request},
        {"discrepancy-uav-recheck": report or default_report},
        {"result-gt16-reevaluation": execution or default_execution},
        contents or _contents(),
    )


def _successor_variant(mutator):
    successor_payload = _json(SUCCESSOR_STATE)
    mutator(successor_payload["world_state"])
    successor_raw = _raw_json(successor_payload)
    successor = load_world_state(successor_payload)
    result_payload = _payload()
    ref = result_payload["incremental_reevaluation_result"]["successor_world_state"]
    ref["semantic_fingerprint"] = successor.semantic_fingerprint()
    ref["content_sha256"] = hashlib.sha256(successor_raw).hexdigest()
    result = load_incremental_reevaluation_result(result_payload)
    contents = _contents()
    contents["successor-world-state"] = successor_raw
    return result, successor, contents


def test_example_loads_round_trips_and_binds() -> None:
    result = load_incremental_reevaluation_result(_payload())

    assert result.result_id == "fictional-uav-separation-incremental-reevaluation"
    assert result.state == "completed"
    assert result.base_world_state.revision == 2
    assert result.successor_world_state.revision == 3
    assert len(result.node_results) == 8
    assert len(result.target_results) == 2
    assert len(result.acceptance_results) == 5
    assert result.output_gates[0].state == "released"
    assert result.action_gates[0].state == "eligible"
    assert result.action_gates[0].authorized is False
    assert result.action_gates[0].executed is False
    assert result.semantic_fingerprint() == (
        "a855a553cadb2ac368ca55dc7bfd173ee3d31a44817d202a0ddc60ff1cf734ce"
    )
    assert load_incremental_reevaluation_result(result.to_dict()) == result
    _bind(result)


def test_schema_is_valid_and_accepts_example() -> None:
    schema = _json(SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(_payload())
    assert schema["$id"] == INCREMENTAL_REEVALUATION_RESULT_SCHEMA_ID
    assert schema["properties"]["incremental_reevaluation_result"]["$ref"] == (
        "#/$defs/incrementalReevaluationResult"
    )


def test_unified_validation_preserves_execution_boundaries() -> None:
    report = validate_artifact_payload(
        INCREMENTAL_REEVALUATION_RESULT_ARTIFACT_ID,
        _payload(),
        file=str(EXAMPLE),
    )
    assert report.valid is True
    summary = report.summary
    assert summary["state"] == "completed"
    assert summary["node_result_count"] == 8
    assert summary["completed_target_count"] == 2
    assert summary["satisfied_acceptance_count"] == 5
    assert summary["resolved_discrepancy_count"] == 1
    assert summary["released_output_count"] == 1
    assert summary["eligible_action_count"] == 1
    for key in (
        "base_world_state_binding_verified",
        "successor_world_state_binding_verified",
        "artifact_bindings_verified",
        "impact_graph_coverage_verified",
        "correction_scope_verified",
        "acceptance_criteria_evaluated",
        "discrepancies_resolved",
        "reevaluation_executed",
        "successor_world_state_materialized",
        "outputs_released",
        "external_truth_verified",
        "action_authorized",
        "action_executed",
    ):
        assert summary[key] is False


def test_loader_rejects_unknown_fields_revision_order_and_aggregate_state() -> None:
    payload = _payload()
    payload["incremental_reevaluation_result"]["extra"] = True
    with pytest.raises(IncrementalReevaluationResultFormatError, match="unknown fields"):
        load_incremental_reevaluation_result(payload)

    payload = _payload()
    payload["incremental_reevaluation_result"]["successor_world_state"]["revision"] = 2
    with pytest.raises(IncrementalReevaluationResultFormatError, match="greater than base"):
        load_incremental_reevaluation_result(payload)

    payload = _payload()
    payload["incremental_reevaluation_result"]["state"] = "blocked"
    with pytest.raises(IncrementalReevaluationResultFormatError, match="aggregate state"):
        load_incremental_reevaluation_result(payload)


def test_loader_rejects_inconsistent_node_and_target_states() -> None:
    payload = _payload()
    node = next(
        item
        for item in payload["incremental_reevaluation_result"]["node_results"]
        if item["node_ref"] == "node-delay-path"
    )
    node.pop("current")
    with pytest.raises(IncrementalReevaluationResultFormatError, match="requires previous and current"):
        load_incremental_reevaluation_result(payload)

    payload = _payload()
    target = payload["incremental_reevaluation_result"]["target_results"][0]
    target["node_ref"] = "node-separation-path"
    with pytest.raises(IncrementalReevaluationResultFormatError, match="must match"):
        load_incremental_reevaluation_result(payload)


def test_loader_rejects_action_authorization_or_execution() -> None:
    payload = _payload()
    payload["incremental_reevaluation_result"]["action_gates"][0]["authorized"] = True
    with pytest.raises(IncrementalReevaluationResultFormatError, match="authorized and executed false"):
        load_incremental_reevaluation_result(payload)

    payload = _payload()
    payload["incremental_reevaluation_result"]["action_gates"][0]["executed"] = True
    with pytest.raises(IncrementalReevaluationResultFormatError, match="authorized and executed false"):
        load_incremental_reevaluation_result(payload)


def test_binding_rejects_world_state_and_exact_byte_mismatches() -> None:
    payload = _payload()
    payload["incremental_reevaluation_result"]["base_world_state"][
        "semantic_fingerprint"
    ] = "0" * 64
    result = load_incremental_reevaluation_result(payload)
    with pytest.raises(IncrementalReevaluationResultFormatError, match="does not match bound"):
        _bind(result)

    result = load_incremental_reevaluation_result(_payload())
    contents = _contents()
    contents["result-gt16-reevaluation"] += b"\n"
    with pytest.raises(IncrementalReevaluationResultFormatError, match="SHA-256 mismatch"):
        _bind(result, contents=contents)


def test_binding_rejects_impact_graph_reference_drift() -> None:
    payload = _payload()
    payload["incremental_reevaluation_result"]["correction_request_refs"][0][
        "content_sha256"
    ] = "0" * 64
    result = load_incremental_reevaluation_result(payload)
    with pytest.raises(IncrementalReevaluationResultFormatError, match="exact Impact Graph"):
        _bind(result)


def test_binding_requires_complete_graph_node_and_target_coverage() -> None:
    payload = _payload()
    payload["incremental_reevaluation_result"]["node_results"] = [
        item
        for item in payload["incremental_reevaluation_result"]["node_results"]
        if item["node_ref"] != "node-change-delay"
    ]
    for acceptance in payload["incremental_reevaluation_result"]["acceptance_results"]:
        acceptance["node_result_refs"] = [
            ref
            for ref in acceptance["node_result_refs"]
            if ref != "result-node-change-delay"
        ]
    for discrepancy in payload["incremental_reevaluation_result"]["discrepancy_results"]:
        discrepancy["node_result_refs"] = [
            ref
            for ref in discrepancy["node_result_refs"]
            if ref != "result-node-change-delay"
        ]
    result = load_incremental_reevaluation_result(payload)
    with pytest.raises(IncrementalReevaluationResultFormatError, match="every Impact Graph node"):
        _bind(result)

    payload = _payload()
    payload["incremental_reevaluation_result"]["target_results"] = [
        item
        for item in payload["incremental_reevaluation_result"]["target_results"]
        if item["target_ref"] != "target-temporal-conflict"
    ]
    for acceptance in payload["incremental_reevaluation_result"]["acceptance_results"]:
        acceptance["target_result_refs"] = [
            ref
            for ref in acceptance["target_result_refs"]
            if ref != "result-target-temporal-conflict"
        ]
    result = load_incremental_reevaluation_result(payload)
    with pytest.raises(IncrementalReevaluationResultFormatError, match="every Impact Graph reevaluation target"):
        _bind(result)


def test_binding_rejects_supplied_object_that_does_not_match_exact_bytes() -> None:
    execution_payload = _json(EXECUTION_RESULT)
    execution_payload["geotask_result"]["warnings"] = ["object-only mutation"]
    execution = GeotaskResult.from_dict(execution_payload)
    result = load_incremental_reevaluation_result(_payload())
    with pytest.raises(
        IncrementalReevaluationResultFormatError,
        match="strictly loaded from exact bytes",
    ):
        _bind(result, execution=execution)


def test_binding_rejects_execution_that_precedes_successor_materialization() -> None:
    execution_payload = _json(EXECUTION_RESULT)
    execution_payload["geotask_result"]["execution"]["started_at"] = (
        "2026-07-16T10:01:14+08:00"
    )
    execution_payload["geotask_result"]["execution"]["finished_at"] = (
        "2026-07-16T10:01:15+08:00"
    )
    execution_raw = _raw_json(execution_payload)
    execution = GeotaskResult.from_dict(execution_payload)
    result_payload = _payload()
    result_payload["incremental_reevaluation_result"]["execution_result_refs"][0][
        "content_sha256"
    ] = hashlib.sha256(execution_raw).hexdigest()
    result = load_incremental_reevaluation_result(result_payload)
    contents = _contents()
    contents["result-gt16-reevaluation"] = execution_raw
    with pytest.raises(IncrementalReevaluationResultFormatError, match="between successor"):
        _bind(result, execution=execution, contents=contents)


def test_binding_rejects_action_that_omits_request_output_gate() -> None:
    payload = _payload()
    payload["incremental_reevaluation_result"]["action_gates"][0]["output_refs"] = []
    result = load_incremental_reevaluation_result(payload)
    with pytest.raises(IncrementalReevaluationResultFormatError, match="every output gate"):
        _bind(result)


def test_binding_rejects_execution_result_and_assertion_mismatch() -> None:
    payload = _payload()
    node = next(
        item
        for item in payload["incremental_reevaluation_result"]["node_results"]
        if item["node_ref"] == "node-temporal-conflict"
    )
    node["current"] = True
    result = load_incremental_reevaluation_result(payload)
    with pytest.raises(IncrementalReevaluationResultFormatError, match="recomputed assertion"):
        _bind(result)


def test_binding_rejects_acceptance_without_declared_supporting_results() -> None:
    payload = _payload()
    criterion = next(
        item
        for item in payload["incremental_reevaluation_result"]["acceptance_results"]
        if item["criterion_id"] == "delay-path-recomputed"
    )
    criterion["node_result_refs"].remove("result-node-change-delay")
    result = load_incremental_reevaluation_result(payload)
    with pytest.raises(IncrementalReevaluationResultFormatError, match="supporting node results"):
        _bind(result)


def test_binding_rejects_released_output_with_unrelated_completed_target() -> None:
    payload = _payload()
    payload["incremental_reevaluation_result"]["output_gates"][0][
        "target_result_refs"
    ] = ["result-target-temporal-conflict"]
    result = load_incremental_reevaluation_result(payload)
    with pytest.raises(IncrementalReevaluationResultFormatError, match="targets for that output"):
        _bind(result)


def test_binding_rejects_failed_acceptance_declaration_and_omitted_gate_criteria() -> None:
    payload = _payload()
    criterion = next(
        item
        for item in payload["incremental_reevaluation_result"]["acceptance_results"]
        if item["criterion_id"] == "successor-world-state-valid"
    )
    criterion["state"] = "failed"
    payload["incremental_reevaluation_result"]["state"] = "failed"
    payload["incremental_reevaluation_result"]["next_action"] = "continue_reevaluation"
    result = load_incremental_reevaluation_result(payload)
    with pytest.raises(IncrementalReevaluationResultFormatError, match="evaluated state"):
        _bind(result)

    payload = _payload()
    payload["incremental_reevaluation_result"]["output_gates"][0][
        "criterion_result_refs"
    ].remove("accept-delay-path-recomputed")
    result = load_incremental_reevaluation_result(payload)
    with pytest.raises(IncrementalReevaluationResultFormatError, match="every acceptance result"):
        _bind(result)


def test_binding_rejects_successor_changes_outside_correction_scope() -> None:
    def mutate(body):
        uav_a = next(item for item in body["objects"] if item["id"] == "uav-a")
        route = next(item for item in uav_a["attributes"] if item["name"] == "route_id")
        route["value"] = "route-tampered"

    result, successor, contents = _successor_variant(mutate)
    with pytest.raises(
        IncrementalReevaluationResultFormatError,
        match="outside requested paths|immutable path changed",
    ):
        _bind(result, successor=successor, contents=contents)


def test_binding_rejects_successor_value_that_disagrees_with_node_results() -> None:
    def mutate(body):
        uav_b = next(item for item in body["objects"] if item["id"] == "uav-b")
        delay = next(item for item in uav_b["attributes"] if item["name"] == "delay_seconds")
        delay["value"] = 61

    result, successor, contents = _successor_variant(mutate)
    with pytest.raises(IncrementalReevaluationResultFormatError, match="does not match successor"):
        _bind(result, successor=successor, contents=contents)


def test_fingerprint_is_collection_order_invariant() -> None:
    original = _payload()
    reordered = copy.deepcopy(original)
    body = reordered["incremental_reevaluation_result"]
    for field in (
        "correction_request_refs",
        "discrepancy_report_refs",
        "execution_result_refs",
        "node_results",
        "target_results",
        "acceptance_results",
        "discrepancy_results",
        "output_gates",
        "action_gates",
    ):
        body[field].reverse()
    for node in body["node_results"]:
        node["basis_refs"].reverse()
    for acceptance in body["acceptance_results"]:
        acceptance["node_result_refs"].reverse()
        acceptance["target_result_refs"].reverse()
        acceptance["basis_refs"].reverse()
    assert load_incremental_reevaluation_result(original).semantic_fingerprint() == (
        load_incremental_reevaluation_result(reordered).semantic_fingerprint()
    )


def test_public_python_namespaces_export_contract() -> None:
    for namespace in (geotask_core, v1):
        assert namespace.INCREMENTAL_REEVALUATION_RESULT_ARTIFACT_ID == (
            "geotask.incremental-reevaluation-result"
        )
        assert namespace.INCREMENTAL_REEVALUATION_RESULT_SCHEMA_ID == (
            INCREMENTAL_REEVALUATION_RESULT_SCHEMA_ID
        )
        assert namespace.INCREMENTAL_REEVALUATION_RESULT_SCHEMA_VERSION == "0.1"
        assert namespace.load_incremental_reevaluation_result is (
            load_incremental_reevaluation_result
        )
        assert namespace.validate_incremental_reevaluation_result_bindings is (
            validate_incremental_reevaluation_result_bindings
        )
