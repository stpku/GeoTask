from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from geotask_core.v1.artifact_validation import validate_artifact_file
from geotask_core.v1.correction_request import load_correction_request
from geotask_core.v1.discrepancy_report import load_discrepancy_report
from geotask_core.v1.world_state import load_world_state
from geotask_core.v1.world_state_materialization import (
    WORLD_STATE_MATERIALIZATION_RESULT_ARTIFACT_ID,
    WORLD_STATE_MATERIALIZATION_RESULT_SCHEMA_ID,
    WorldStateMaterializationError,
    load_world_state_materialization_result,
    materialize_successor_world_state,
    serialize_world_state,
    validate_world_state_materialization_result_bindings,
)


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "examples" / "core"
BASE_STATE = CORE / "world_state_uav_separation_recheck.json"
SUCCESSOR_STATE = CORE / "world_state_uav_separation_successor.json"
CORRECTION_REQUEST = CORE / "correction_request_uav_recheck.json"
DISCREPANCY_REPORT = CORE / "discrepancy_report_uav_recheck.json"
TASK = CORE / "uav_route_crossing_temporal_separation.yaml"
RESULT = CORE / "world_state_materialization_result_uav_recheck.json"
SCHEMA = ROOT / "schemas" / "geotask-world-state-materialization-result-v0.1.schema.json"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _base():
    return load_world_state(_json(BASE_STATE))


def _successor():
    return load_world_state(_json(SUCCESSOR_STATE))


def _request(payload: dict | None = None):
    return load_correction_request(payload or _json(CORRECTION_REQUEST))


def _report():
    return load_discrepancy_report(_json(DISCREPANCY_REPORT))


def _request_artifact_contents() -> dict[str, bytes]:
    return {
        "base-world-state": BASE_STATE.read_bytes(),
        "discrepancy-uav-recheck": DISCREPANCY_REPORT.read_bytes(),
        "task-gt16": TASK.read_bytes(),
    }


def _materialize(**overrides):
    kwargs = {
        "materialization_id": "fictional-uav-successor-materialization",
        "reason": (
            "Apply the two telemetry-bound recomputations and preserve all "
            "blocked outputs and actions for reevaluation."
        ),
        "created_at": "2026-07-16T10:01:17+08:00",
        "base_world_state": _base(),
        "correction_request": _request(),
        "correction_request_ref_id": "correction-uav-recheck",
        "correction_request_content": CORRECTION_REQUEST.read_bytes(),
        "discrepancy_reports": {"discrepancy-uav-recheck": _report()},
        "artifact_contents": _request_artifact_contents(),
        "recomputed_values": {
            "recompute-uav-b-delay": 60,
            "recompute-temporal-separation": 60,
        },
        "as_of": "2026-07-16T10:01:15+08:00",
        "materialized_at": "2026-07-16T10:01:16+08:00",
    }
    kwargs.update(overrides)
    return materialize_successor_world_state(**kwargs)


def _result(payload: dict | None = None):
    return load_world_state_materialization_result(payload or _json(RESULT))


def _binding_contents(**overrides) -> dict[str, bytes]:
    contents = {
        "base-world-state": BASE_STATE.read_bytes(),
        "correction-uav-recheck": CORRECTION_REQUEST.read_bytes(),
        "successor-world-state": SUCCESSOR_STATE.read_bytes(),
    }
    contents.update(overrides)
    return contents


def _bind(result=None, *, base=None, request=None, successor=None, contents=None):
    validate_world_state_materialization_result_bindings(
        result or _result(),
        base or _base(),
        request or _request(),
        successor or _successor(),
        contents or _binding_contents(),
    )


def test_public_identity_and_schema_are_stable() -> None:
    assert (
        WORLD_STATE_MATERIALIZATION_RESULT_ARTIFACT_ID
        == "geotask.world-state-materialization-result"
    )
    assert WORLD_STATE_MATERIALIZATION_RESULT_SCHEMA_ID.endswith(
        "geotask-world-state-materialization-result-v0.1.schema.json"
    )
    schema = _json(SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(_json(RESULT))


def test_unified_artifact_validation_keeps_execution_boundaries_false() -> None:
    report = validate_artifact_file(
        "geotask.world-state-materialization-result",
        RESULT,
    )
    body = report.to_dict()["artifact_validation"]

    assert report.valid is True
    assert body["artifact_id"] == "geotask.world-state-materialization-result"
    assert body["summary"]["materialization_id"] == (
        "fictional-uav-successor-materialization"
    )
    assert body["summary"]["applied_change_count"] == 2
    for field in (
        "base_world_state_binding_verified",
        "correction_request_binding_verified",
        "successor_world_state_binding_verified",
        "changes_applied",
        "successor_world_state_materialized",
        "reevaluation_executed",
        "outputs_released",
        "external_truth_verified",
        "action_authorized",
        "action_executed",
    ):
        assert body["summary"][field] is False


def test_materializer_generates_exact_public_examples() -> None:
    output = _materialize()

    assert output.world_state == _successor()
    assert output.world_state_bytes == SUCCESSOR_STATE.read_bytes()
    assert output.result == _result()
    assert output.result_bytes == RESULT.read_bytes()
    assert output.world_state.revision == 3
    assert output.result.state == "completed"
    assert output.result.next_action == "reevaluate_successor_state"
    assert output.result.reevaluation_executed is False
    assert output.result.outputs_released is False
    assert output.result.action_authorized is False
    assert output.result.action_executed is False


def test_result_round_trip_fingerprint_and_bindings() -> None:
    result = _result()

    assert result.semantic_fingerprint() == (
        "d1c3ff5b0734754b3768b061df488778d06fa5c7fdb9d329c18c40e098bacadf"
    )
    assert load_world_state_materialization_result(result.to_dict()) == result
    assert serialize_world_state(_successor()) == SUCCESSOR_STATE.read_bytes()
    _bind(result)


def test_materializer_requires_exact_recompute_keys() -> None:
    with pytest.raises(WorldStateMaterializationError, match="missing"):
        _materialize(
            recomputed_values={"recompute-uav-b-delay": 60},
        )
    with pytest.raises(WorldStateMaterializationError, match="unexpected"):
        _materialize(
            recomputed_values={
                "recompute-uav-b-delay": 60,
                "recompute-temporal-separation": 60,
                "not-a-change": 1,
            },
        )


def test_materializer_rejects_non_json_safe_recomputed_value() -> None:
    with pytest.raises(WorldStateMaterializationError, match="non-finite"):
        _materialize(
            recomputed_values={
                "recompute-uav-b-delay": float("nan"),
                "recompute-temporal-separation": 60,
            }
        )


def test_materializer_rejects_non_required_request() -> None:
    request = replace(_request(), state="blocked", next_action="none")
    with pytest.raises(WorldStateMaterializationError, match="must equal 'required'"):
        _materialize(correction_request=request)


def test_materializer_enforces_time_causality() -> None:
    with pytest.raises(WorldStateMaterializationError, match="must not precede"):
        _materialize(as_of="2026-07-16T10:01:07+08:00")
    with pytest.raises(WorldStateMaterializationError, match="must not precede as_of"):
        _materialize(materialized_at="2026-07-16T10:01:14+08:00")
    with pytest.raises(WorldStateMaterializationError, match="created_at"):
        _materialize(created_at="2026-07-16T10:01:15+08:00")


def test_materializer_rejects_request_object_bytes_mismatch() -> None:
    payload = _json(CORRECTION_REQUEST)
    payload["correction_request"]["reason"] += " altered"
    altered = _request(payload)
    with pytest.raises(WorldStateMaterializationError, match="does not strictly load"):
        _materialize(correction_request=altered)


def test_materializer_rejects_base_object_that_disagrees_with_bound_bytes() -> None:
    altered_base = replace(
        _base(), materialized_at="2026-07-16T10:01:03+08:00"
    )
    with pytest.raises(
        WorldStateMaterializationError, match="binding validation failed"
    ):
        _materialize(base_world_state=altered_base)


def test_materializer_rejects_new_observation_or_evidence_refs() -> None:
    payload = _json(CORRECTION_REQUEST)
    payload["correction_request"]["observation_refs"].append("obs-new")
    payload["correction_request"]["evidence_refs"].append("evidence:new")
    request = _request(payload)
    raw = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode()
    with pytest.raises(
        WorldStateMaterializationError, match="binding validation failed"
    ):
        _materialize(correction_request=request, correction_request_content=raw)


def test_materializer_rejects_successor_outside_validity_window() -> None:
    with pytest.raises(WorldStateMaterializationError, match="generated snapshot is invalid"):
        _materialize(
            as_of="2026-07-16T10:03:00+08:00",
            materialized_at="2026-07-16T10:03:01+08:00",
            created_at="2026-07-16T10:03:02+08:00",
        )


def test_loader_rejects_unknown_fields_duplicate_changes_and_true_boundaries() -> None:
    payload = _json(RESULT)
    payload["world_state_materialization_result"]["unknown"] = True
    with pytest.raises(WorldStateMaterializationError, match="unknown fields"):
        _result(payload)

    payload = _json(RESULT)
    payload["world_state_materialization_result"]["applied_changes"].append(
        copy.deepcopy(
            payload["world_state_materialization_result"]["applied_changes"][0]
        )
    )
    with pytest.raises(WorldStateMaterializationError, match="duplicates"):
        _result(payload)

    payload = _json(RESULT)
    payload["world_state_materialization_result"]["action_authorized"] = True
    with pytest.raises(WorldStateMaterializationError, match="must remain false"):
        _result(payload)


def test_binding_rejects_missing_or_substituted_exact_bytes() -> None:
    contents = _binding_contents()
    del contents["successor-world-state"]
    with pytest.raises(WorldStateMaterializationError, match="keys must exactly match"):
        _bind(contents=contents)

    contents = _binding_contents(
        **{"successor-world-state": SUCCESSOR_STATE.read_bytes() + b"\n"}
    )
    with pytest.raises(WorldStateMaterializationError, match="content_sha256"):
        _bind(contents=contents)


def test_binding_rejects_supplied_object_not_loaded_from_exact_bytes() -> None:
    payload = _json(SUCCESSOR_STATE)
    payload["world_state"]["materialized_at"] = "2026-07-16T10:01:17+08:00"
    successor = load_world_state(payload)
    with pytest.raises(WorldStateMaterializationError, match="expected"):
        _bind(successor=successor)


def test_binding_rejects_missing_change_or_changed_request_fields() -> None:
    payload = _json(RESULT)
    payload["world_state_materialization_result"]["applied_changes"].pop()
    result = _result(payload)
    with pytest.raises(WorldStateMaterializationError, match="cover every"):
        _bind(result=result)

    payload = _json(RESULT)
    payload["world_state_materialization_result"]["applied_changes"][0][
        "request_basis_refs"
    ] = ["task-gt16"]
    result = _result(payload)
    with pytest.raises(WorldStateMaterializationError, match="does not match"):
        _bind(result=result)


def test_binding_rejects_before_or_after_that_disagrees_with_snapshots() -> None:
    payload = _json(RESULT)
    payload["world_state_materialization_result"]["applied_changes"][0][
        "before"
    ] = 999
    result = _result(payload)
    with pytest.raises(WorldStateMaterializationError, match="base snapshot"):
        _bind(result=result)

    payload = _json(RESULT)
    payload["world_state_materialization_result"]["applied_changes"][0][
        "after"
    ] = 999
    result = _result(payload)
    with pytest.raises(WorldStateMaterializationError, match="successor snapshot"):
        _bind(result=result)


def _successor_variant(mutator):
    payload = _json(SUCCESSOR_STATE)
    mutator(payload["world_state"])
    raw = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode()
    successor = load_world_state(payload)
    result_payload = _json(RESULT)
    ref = result_payload["world_state_materialization_result"][
        "successor_world_state"
    ]
    ref["semantic_fingerprint"] = successor.semantic_fingerprint()
    ref["content_sha256"] = hashlib.sha256(raw).hexdigest()
    ref["materialized_at"] = successor.materialized_at
    result = _result(result_payload)
    contents = _binding_contents(**{"successor-world-state": raw})
    return result, successor, contents


def test_binding_rejects_successor_changes_outside_requested_paths() -> None:
    def mutate(body):
        body["objects"][0]["verification_status"] = "asserted"

    result, successor, contents = _successor_variant(mutate)
    with pytest.raises(WorldStateMaterializationError, match="outside requested paths"):
        _bind(result=result, successor=successor, contents=contents)


def test_binding_rejects_changed_provenance_refs() -> None:
    def mutate(body):
        body["evidence_refs"].append("evidence:extra")
        body["objects"][0]["evidence_refs"].append("evidence:extra")

    result, successor, contents = _successor_variant(mutate)
    with pytest.raises(WorldStateMaterializationError, match="preserve base refs"):
        _bind(result=result, successor=successor, contents=contents)


def test_binding_rejects_dropped_blocked_outputs_or_actions() -> None:
    payload = _json(RESULT)
    payload["world_state_materialization_result"]["blocked_outputs"] = []
    result = _result(payload)
    with pytest.raises(WorldStateMaterializationError, match="blocked outputs"):
        _bind(result=result)

    payload = _json(RESULT)
    payload["world_state_materialization_result"]["blocked_actions"] = []
    result = _result(payload)
    with pytest.raises(WorldStateMaterializationError, match="blocked actions"):
        _bind(result=result)
