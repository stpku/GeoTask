from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import geotask_core
import geotask_core.v1 as v1
from geotask_core.v1.artifact_registry import get_artifact_descriptor
from geotask_core.v1.artifact_validation import validate_artifact_payload
from geotask_core.v1.state_transition import (
    STATE_TRANSITION_SCHEMA_ID,
    StateTransitionFormatError,
    load_state_transition,
    validate_state_transition_bindings,
)
from geotask_core.v1.world_state import load_world_state


ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "core" / "state_transition_uav_separation_recheck.json"
FROM_STATE = ROOT / "examples" / "core" / "world_state_uav_separation.json"
TO_STATE = ROOT / "examples" / "core" / "world_state_uav_separation_recheck.json"
SCHEMA = ROOT / "schemas" / "geotask-state-transition-v0.1.schema.json"


def _payload() -> dict[str, object]:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_state_transition_example_matches_schema_loader_and_bound_states() -> None:
    payload = _payload()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert list(Draft202012Validator(schema).iter_errors(payload)) == []

    transition = load_state_transition(payload)
    before = load_world_state(json.loads(FROM_STATE.read_text(encoding="utf-8")))
    after = load_world_state(json.loads(TO_STATE.read_text(encoding="utf-8")))
    validate_state_transition_bindings(transition, before, after)

    assert transition.transition_id == "fictional-uav-separation-recheck-transition"
    assert transition.from_state.revision == 1
    assert transition.to_state.revision == 2
    assert len(transition.changes) == 2
    assert len(transition.action_eligibility_changes) == 1
    assert transition.semantic_fingerprint() == (
        "2f876d9f50fc38d9028161c3f536615197fb5781c041edea28efe74e95701496"
    )
    assert load_state_transition(transition.to_dict()) == transition


def test_state_transition_fingerprint_is_order_independent() -> None:
    payload = _payload()
    reordered = copy.deepcopy(payload)
    body = reordered["state_transition"]
    body["observation_refs"].reverse()
    body["evidence_refs"].reverse()
    body["changes"].reverse()
    for change in body["changes"]:
        change["observation_refs"].reverse()
        change["evidence_refs"].reverse()
    body["action_eligibility_changes"].reverse()
    for change in body["action_eligibility_changes"]:
        change["observation_refs"].reverse()
        change["evidence_refs"].reverse()

    assert load_state_transition(reordered).semantic_fingerprint() == (
        load_state_transition(payload).semantic_fingerprint()
    )


def test_state_transition_rejects_wrong_revision_and_time_order() -> None:
    payload = _payload()
    payload["state_transition"]["to_state"]["revision"] = 1
    with pytest.raises(StateTransitionFormatError, match="greater than"):
        load_state_transition(payload)

    payload = _payload()
    payload["state_transition"]["occurred_at"] = "2026-07-16T10:01:01+08:00"
    with pytest.raises(StateTransitionFormatError, match="must fall between"):
        load_state_transition(payload)

    payload = _payload()
    payload["state_transition"]["recorded_at"] = "2026-07-16T10:00:59+08:00"
    with pytest.raises(StateTransitionFormatError, match="to_state.as_of"):
        load_state_transition(payload)


def test_state_transition_rejects_invalid_operation_shapes() -> None:
    payload = _payload()
    del payload["state_transition"]["changes"][0]["before"]
    with pytest.raises(StateTransitionFormatError, match="requires both before and after"):
        load_state_transition(payload)

    payload = _payload()
    payload["state_transition"]["changes"][0]["operation"] = "add"
    with pytest.raises(StateTransitionFormatError, match="add requires after and forbids before"):
        load_state_transition(payload)

    payload = _payload()
    payload["state_transition"]["changes"][0]["after"] = 40
    with pytest.raises(StateTransitionFormatError, match="must differ"):
        load_state_transition(payload)


def test_state_transition_rejects_wrong_kind_path_and_duplicate_path() -> None:
    payload = _payload()
    payload["state_transition"]["changes"][0]["path"] = (
        "/relations/uav-temporal-separation/value"
    )
    with pytest.raises(StateTransitionFormatError, match="attribute changes must target"):
        load_state_transition(payload)

    payload = _payload()
    payload["state_transition"]["changes"][0]["kind"] = "object"
    payload["state_transition"]["changes"][0]["path"] = "/objects"
    with pytest.raises(StateTransitionFormatError, match="object changes must target"):
        load_state_transition(payload)

    payload = _payload()
    payload["state_transition"]["changes"][1]["path"] = "/relations"
    with pytest.raises(StateTransitionFormatError, match="relation changes must target"):
        load_state_transition(payload)

    payload = _payload()
    payload["state_transition"]["changes"][1]["path"] = (
        "/objects/uav-b/attributes/delay_seconds/value"
    )
    payload["state_transition"]["changes"][1]["kind"] = "attribute"
    with pytest.raises(StateTransitionFormatError, match="duplicates changed path"):
        load_state_transition(payload)


def test_state_transition_rejects_open_references_and_empty_transition() -> None:
    payload = _payload()
    payload["state_transition"]["changes"][0]["observation_refs"] = ["missing"]
    with pytest.raises(StateTransitionFormatError, match="state_transition.observation_refs"):
        load_state_transition(payload)

    payload = _payload()
    payload["state_transition"]["changes"] = []
    payload["state_transition"]["action_eligibility_changes"] = []
    with pytest.raises(StateTransitionFormatError, match="at least one"):
        load_state_transition(payload)


def test_state_transition_rejects_duplicate_change_and_output_identities() -> None:
    payload = _payload()
    duplicate = copy.deepcopy(payload["state_transition"]["changes"][0])
    duplicate["path"] = "/objects/uav-b/attributes/delay_seconds/uncertainty"
    payload["state_transition"]["changes"].append(duplicate)
    with pytest.raises(StateTransitionFormatError, match="duplicates id"):
        load_state_transition(payload)

    payload = _payload()
    duplicate_eligibility = copy.deepcopy(
        payload["state_transition"]["action_eligibility_changes"][0]
    )
    duplicate_eligibility["id"] = "eligibility-duplicate"
    payload["state_transition"]["action_eligibility_changes"].append(
        duplicate_eligibility
    )
    with pytest.raises(StateTransitionFormatError, match="duplicates output_ref"):
        load_state_transition(payload)


def test_state_transition_binding_validation_fails_on_snapshot_mismatch() -> None:
    transition = load_state_transition(_payload())
    before_payload = json.loads(FROM_STATE.read_text(encoding="utf-8"))
    before_payload["world_state"]["objects"][1]["attributes"][1]["value"] = 41
    before = load_world_state(before_payload)
    after = load_world_state(json.loads(TO_STATE.read_text(encoding="utf-8")))

    with pytest.raises(StateTransitionFormatError, match="semantic_fingerprint"):
        validate_state_transition_bindings(transition, before, after)


def test_state_transition_registry_and_unified_validation_are_fail_closed() -> None:
    descriptor = get_artifact_descriptor("geotask.state-transition")
    assert descriptor.schema_id == STATE_TRANSITION_SCHEMA_ID
    assert descriptor.wrapper_key == "state_transition"
    assert descriptor.schema_path == "schemas/geotask-state-transition-v0.1.schema.json"
    assert descriptor.specification_path == "docs/spec/geotask-state-transition-v0.1.md"
    assert "examples/core/state_transition*.json" in descriptor.to_dict()[
        "ide_file_patterns"
    ]
    assert "does not compare snapshots" in descriptor.execution_boundary

    report = validate_artifact_payload(
        "geotask.state-transition", _payload(), file=EXAMPLE.as_posix()
    )
    assert report.valid is True
    assert report.schema_verified is True
    assert report.summary == {
        "transition_id": "fictional-uav-separation-recheck-transition",
        "world_state_id": "fictional-uav-separation-state",
        "from_revision": 1,
        "to_revision": 2,
        "change_count": 2,
        "relation_change_count": 1,
        "action_eligibility_change_count": 1,
        "observation_ref_count": 1,
        "evidence_ref_count": 2,
        "semantic_fingerprint": (
            "2f876d9f50fc38d9028161c3f536615197fb5781c041edea28efe74e95701496"
        ),
        "snapshot_bindings_verified": False,
        "changes_applied": False,
        "world_state_materialized": False,
        "external_truth_verified": False,
        "action_authorized": False,
    }

    invalid = _payload()
    invalid["state_transition"]["to_state"]["revision"] = 1
    invalid_report = validate_artifact_payload("geotask.state-transition", invalid)
    assert invalid_report.valid is False
    assert invalid_report.schema_verified is True
    assert invalid_report.diagnostics[0]["code"] == "invalid_state_transition"


def test_state_transition_public_python_namespaces_export_contract() -> None:
    for namespace in (geotask_core, v1):
        assert namespace.STATE_TRANSITION_ARTIFACT_ID == "geotask.state-transition"
        assert namespace.STATE_TRANSITION_SCHEMA_ID == STATE_TRANSITION_SCHEMA_ID
        assert namespace.STATE_TRANSITION_SCHEMA_VERSION == "0.1"
        assert namespace.STATE_TRANSITION_FORMAT_VERSION == "0.1"
        assert namespace.load_state_transition is load_state_transition
        assert (
            namespace.validate_state_transition_bindings
            is validate_state_transition_bindings
        )
        assert namespace.StateTransition.__name__ == "StateTransition"
