from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from geotask_core.v1.correction_request import load_correction_request
from geotask_core.v1.discrepancy_report import load_discrepancy_report
from geotask_core.v1.recompute_derivation import (
    RECOMPUTE_DERIVATION_RESULT_ARTIFACT_ID,
    RECOMPUTE_DERIVATION_RESULT_SCHEMA_ID,
    RecomputeDerivationError,
    evaluate_recompute_derivations,
    load_recompute_derivation_result,
    validate_recompute_derivation_bindings,
)
from geotask_core.v1.world_state import load_world_state
from geotask_core.v1.world_state_materialization import (
    materialize_successor_world_state,
)


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "examples" / "core"
RESULT = CORE / "recompute_derivation_result_uav_recheck.json"
OBSERVATION = CORE / "observation_uav_b_delay_recheck.json"
TASK = CORE / "uav_route_crossing_temporal_separation.yaml"
BASE_STATE = CORE / "world_state_uav_separation_recheck.json"
SUCCESSOR_STATE = CORE / "world_state_uav_separation_successor.json"
CORRECTION_REQUEST = CORE / "correction_request_uav_recheck.json"
DISCREPANCY_REPORT = CORE / "discrepancy_report_uav_recheck.json"
SCHEMA = ROOT / "schemas" / "geotask-recompute-derivation-result-v0.1.schema.json"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _payload() -> dict:
    return copy.deepcopy(_json(RESULT))


def _result(payload: dict | None = None):
    return load_recompute_derivation_result(payload or _payload())


def _base():
    return load_world_state(_json(BASE_STATE))


def _request(payload: dict | None = None):
    return load_correction_request(payload or _json(CORRECTION_REQUEST))


def _sources() -> dict[str, dict]:
    return {
        "observation-uav-b-delay": _json(OBSERVATION),
        "task-gt16": yaml.safe_load(TASK.read_text(encoding="utf-8")),
    }


def _contents(**overrides: bytes) -> dict[str, bytes]:
    contents = {
        "base-world-state": BASE_STATE.read_bytes(),
        "correction-uav-recheck": CORRECTION_REQUEST.read_bytes(),
        "observation-uav-b-delay": OBSERVATION.read_bytes(),
        "task-gt16": TASK.read_bytes(),
    }
    contents.update(overrides)
    return contents


def _bind(
    result=None,
    *,
    base=None,
    request=None,
    sources=None,
    contents=None,
) -> None:
    validate_recompute_derivation_bindings(
        result or _result(),
        base or _base(),
        request or _request(),
        sources or _sources(),
        contents or _contents(),
    )


def test_public_identity_schema_and_fingerprint_are_stable() -> None:
    result = _result()
    assert RECOMPUTE_DERIVATION_RESULT_ARTIFACT_ID == "geotask.recompute-derivation-result"
    assert RECOMPUTE_DERIVATION_RESULT_SCHEMA_ID.endswith(
        "geotask-recompute-derivation-result-v0.1.schema.json"
    )
    assert result.state == "completed"
    assert result.semantic_fingerprint() == (
        "517ad0ed92db9bac3b0586fe85eba7237d6cca0b02eccbcb8c11a33847838070"
    )
    assert load_recompute_derivation_result(result.to_dict()) == result


def test_schema_and_binding_accept_reference_example() -> None:
    schema = _json(SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(_payload())
    _bind()


def test_deterministic_derivation_returns_complete_materializer_map() -> None:
    values = evaluate_recompute_derivations(_result())
    assert values == {
        "recompute-temporal-separation": 60,
        "recompute-uav-b-delay": 60,
    }


def test_derivation_values_feed_bounded_materializer_without_manual_values() -> None:
    result = _result()
    output = materialize_successor_world_state(
        materialization_id="fictional-uav-successor-materialization",
        reason=(
            "Apply recompute values produced by the exact source-bound derivation "
            "contract and keep outputs/actions blocked for reevaluation."
        ),
        created_at="2026-07-16T10:01:17+08:00",
        base_world_state=_base(),
        correction_request=_request(),
        correction_request_ref_id="correction-uav-recheck",
        correction_request_content=CORRECTION_REQUEST.read_bytes(),
        discrepancy_reports={
            "discrepancy-uav-recheck": load_discrepancy_report(
                _json(DISCREPANCY_REPORT)
            )
        },
        artifact_contents={
            "base-world-state": BASE_STATE.read_bytes(),
            "discrepancy-uav-recheck": DISCREPANCY_REPORT.read_bytes(),
            "task-gt16": TASK.read_bytes(),
        },
        recomputed_values=evaluate_recompute_derivations(result),
        as_of="2026-07-16T10:01:15+08:00",
        materialized_at="2026-07-16T10:01:16+08:00",
    )
    assert output.world_state == load_world_state(_json(SUCCESSOR_STATE))


def test_loader_rejects_arbitrary_method_and_wrong_aggregate_state() -> None:
    payload = _payload()
    payload["recompute_derivation_result"]["derivations"][0]["method"] = "eval_python"
    with pytest.raises(RecomputeDerivationError, match="must be one of"):
        _result(payload)

    payload = _payload()
    payload["recompute_derivation_result"]["state"] = "partial"
    with pytest.raises(RecomputeDerivationError, match="aggregate state 'completed'"):
        _result(payload)


def test_loader_rejects_result_map_drift_and_operational_claims() -> None:
    payload = _payload()
    payload["recompute_derivation_result"]["recompute_values"][0]["value"] = 59
    with pytest.raises(RecomputeDerivationError, match="exactly equal"):
        _result(payload)

    payload = _payload()
    payload["recompute_derivation_result"]["successor_materialized"] = True
    with pytest.raises(RecomputeDerivationError, match="must keep materialization"):
        _result(payload)


def test_evaluator_rejects_false_declared_result() -> None:
    payload = _payload()
    payload["recompute_derivation_result"]["derivations"][1]["result"] = 59
    payload["recompute_derivation_result"]["recompute_values"][0]["value"] = 59
    result = _result(payload)
    with pytest.raises(RecomputeDerivationError, match="deterministic result 60"):
        evaluate_recompute_derivations(result)


def test_binding_rejects_exact_byte_hash_drift() -> None:
    with pytest.raises(RecomputeDerivationError, match="SHA-256 mismatch"):
        _bind(contents=_contents(**{"observation-uav-b-delay": b"{}\n"}))


def test_binding_rejects_source_pointer_value_drift() -> None:
    payload = _payload()
    payload["recompute_derivation_result"]["derivations"][0]["inputs"][2]["value"] = 59
    result = _result(payload)
    with pytest.raises(RecomputeDerivationError, match="exact source value 60"):
        _bind(result)


def test_binding_rejects_missing_recompute_change_coverage() -> None:
    payload = _payload()
    body = payload["recompute_derivation_result"]
    body["derivations"] = body["derivations"][:1]
    body["recompute_values"] = [
        item
        for item in body["recompute_values"]
        if item["change_id"] == "recompute-uav-b-delay"
    ]
    result = _result(payload)
    with pytest.raises(RecomputeDerivationError, match="cover every recompute change"):
        _bind(result)


def test_binding_rejects_input_field_contract_drift() -> None:
    payload = _payload()
    payload["recompute_derivation_result"]["derivations"][0]["inputs"][0][
        "name"
    ] = "unexpected_field"
    result = _result(payload)
    with pytest.raises(RecomputeDerivationError, match="exactly match Correction Request"):
        _bind(result)


def test_binding_rejects_missing_source_basis_and_wrong_verified_time() -> None:
    payload = _payload()
    payload["recompute_derivation_result"]["derivations"][0]["basis_refs"] = [
        "correction-uav-recheck"
    ]
    result = _result(payload)
    with pytest.raises(RecomputeDerivationError, match="every used source"):
        _bind(result)

    payload = _payload()
    payload["recompute_derivation_result"]["derivations"][0]["inputs"][4][
        "value"
    ] = "2026-07-16T09:59:00+08:00"
    result = _result(payload)
    with pytest.raises(RecomputeDerivationError, match="between base as_of"):
        _bind(result)


def test_binding_rejects_observation_not_declared_by_request() -> None:
    observation_payload = _json(OBSERVATION)
    observation_payload["observation"]["observation_id"] = "other-observation"
    source_bytes = (json.dumps(observation_payload, indent=2) + "\n").encode("utf-8")
    payload = _payload()
    body = payload["recompute_derivation_result"]
    ref = body["source_artifact_refs"][0]
    ref["instance_id"] = "other-observation"
    import hashlib

    ref["content_sha256"] = hashlib.sha256(source_bytes).hexdigest()
    result = _result(payload)
    sources = _sources()
    sources["observation-uav-b-delay"] = observation_payload
    contents = _contents(**{"observation-uav-b-delay": source_bytes})
    with pytest.raises(RecomputeDerivationError, match="absent from request observation_refs"):
        _bind(result, sources=sources, contents=contents)


def test_binding_rejects_document_not_declared_by_request() -> None:
    import hashlib

    request_payload = _json(CORRECTION_REQUEST)
    body = request_payload["correction_request"]
    body["supporting_artifact_refs"] = []
    for change in body["changes"]:
        change["basis_refs"] = [
            ref for ref in change["basis_refs"] if ref != "task-gt16"
        ]
    request_bytes = (json.dumps(request_payload, indent=2) + "\n").encode("utf-8")
    request = _request(request_payload)

    result_payload = _payload()
    result_payload["recompute_derivation_result"]["correction_request_ref"][
        "content_sha256"
    ] = hashlib.sha256(request_bytes).hexdigest()
    result = _result(result_payload)
    contents = _contents(**{"correction-uav-recheck": request_bytes})

    with pytest.raises(
        RecomputeDerivationError,
        match="must be declared in Correction Request supporting_artifact_refs",
    ):
        _bind(result, request=request, contents=contents)
