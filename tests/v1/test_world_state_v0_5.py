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
from geotask_core.v1.world_state import (
    WORLD_STATE_SCHEMA_ID,
    WorldStateFormatError,
    load_world_state,
)


ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "core" / "world_state_uav_separation.json"
SCHEMA = ROOT / "schemas" / "geotask-world-state-v0.1.schema.json"


def _payload() -> dict[str, object]:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_world_state_example_matches_schema_and_strict_loader() -> None:
    payload = _payload()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert list(Draft202012Validator(schema).iter_errors(payload)) == []

    state = load_world_state(payload)
    assert state.world_state_id == "fictional-uav-separation-state"
    assert state.revision == 1
    assert state.as_of == "2026-07-16T10:00:40+08:00"
    assert len(state.objects) == 2
    assert sum(len(item.attributes) for item in state.objects) == 3
    assert len(state.relations) == 2
    assert state.semantic_fingerprint() == (
        "256b05cd81de380029f7815f0313bbf6497e2c9394ce2b5c11c54af332ac98ea"
    )
    assert load_world_state(state.to_dict()) == state


def test_world_state_fingerprint_is_order_independent_for_set_like_collections() -> None:
    payload = _payload()
    reordered = copy.deepcopy(payload)
    body = reordered["world_state"]
    body["observation_refs"].reverse()
    body["evidence_refs"].reverse()
    body["objects"].reverse()
    for item in body["objects"]:
        item["attributes"].reverse()
        item["observation_refs"].reverse()
        item["evidence_refs"].reverse()
        for attribute in item["attributes"]:
            attribute["observation_refs"].reverse()
            attribute["evidence_refs"].reverse()
    body["relations"].reverse()
    for relation in body["relations"]:
        relation["observation_refs"].reverse()
        relation["evidence_refs"].reverse()

    assert load_world_state(reordered).semantic_fingerprint() == load_world_state(
        payload
    ).semantic_fingerprint()


def test_world_state_rejects_materialization_before_snapshot_time() -> None:
    payload = _payload()
    payload["world_state"]["materialized_at"] = "2026-07-16T10:00:39+08:00"

    with pytest.raises(WorldStateFormatError, match="must not be earlier"):
        load_world_state(payload)


def test_world_state_rejects_inactive_snapshot_item() -> None:
    payload = _payload()
    payload["world_state"]["objects"][0]["valid_until"] = (
        "2026-07-16T10:00:39+08:00"
    )

    with pytest.raises(WorldStateFormatError, match="world_state.as_of"):
        load_world_state(payload)


def test_world_state_rejects_unknown_relation_object() -> None:
    payload = _payload()
    payload["world_state"]["relations"][0]["object_ref"] = "missing-uav"

    with pytest.raises(WorldStateFormatError, match="unknown world object"):
        load_world_state(payload)


def test_world_state_rejects_undeclared_nested_trace_reference() -> None:
    payload = _payload()
    payload["world_state"]["objects"][0]["evidence_refs"] = ["missing:evidence"]

    with pytest.raises(WorldStateFormatError, match="world_state.evidence_refs"):
        load_world_state(payload)


def test_world_state_requires_traceability_for_supported_statuses() -> None:
    payload = _payload()
    attribute = payload["world_state"]["objects"][0]["attributes"][0]
    attribute["observation_refs"] = []
    attribute["evidence_refs"] = []

    with pytest.raises(WorldStateFormatError, match="requires at least one"):
        load_world_state(payload)


def test_world_state_rejects_duplicate_attributes_and_nonfinite_values() -> None:
    payload = _payload()
    duplicate = copy.deepcopy(payload["world_state"]["objects"][0]["attributes"][0])
    payload["world_state"]["objects"][0]["attributes"].append(duplicate)
    with pytest.raises(WorldStateFormatError, match="duplicates attribute name"):
        load_world_state(payload)

    payload = _payload()
    payload["world_state"]["relations"][0]["value"] = float("nan")
    with pytest.raises(WorldStateFormatError, match="non-finite"):
        load_world_state(payload)


def test_world_state_registry_and_unified_validation_are_fail_closed() -> None:
    descriptor = get_artifact_descriptor("geotask.world-state")
    assert descriptor.schema_id == WORLD_STATE_SCHEMA_ID
    assert descriptor.wrapper_key == "world_state"
    assert descriptor.schema_path == "schemas/geotask-world-state-v0.1.schema.json"
    assert descriptor.specification_path == "docs/spec/geotask-world-state-v0.1.md"
    assert "examples/core/world_state*.json" in descriptor.to_dict()["ide_file_patterns"]
    assert "does not fetch evidence" in descriptor.execution_boundary

    report = validate_artifact_payload(
        "geotask.world-state", _payload(), file=EXAMPLE.as_posix()
    )
    assert report.valid is True
    assert report.schema_verified is True
    assert report.summary == {
        "world_state_id": "fictional-uav-separation-state",
        "revision": 1,
        "as_of": "2026-07-16T10:00:40+08:00",
        "object_count": 2,
        "attribute_count": 3,
        "relation_count": 2,
        "observation_ref_count": 1,
        "evidence_ref_count": 2,
        "semantic_fingerprint": (
            "256b05cd81de380029f7815f0313bbf6497e2c9394ce2b5c11c54af332ac98ea"
        ),
        "external_truth_verified": False,
        "state_transition_computed": False,
        "action_eligibility_changed": False,
    }

    invalid = _payload()
    invalid["world_state"]["relations"][0]["subject_ref"] = "missing-uav"
    invalid_report = validate_artifact_payload("geotask.world-state", invalid)
    assert invalid_report.valid is False
    assert invalid_report.schema_verified is True
    assert invalid_report.diagnostics[0]["code"] == "invalid_world_state"


def test_world_state_public_python_namespaces_export_contract() -> None:
    for namespace in (geotask_core, v1):
        assert namespace.WORLD_STATE_ARTIFACT_ID == "geotask.world-state"
        assert namespace.WORLD_STATE_SCHEMA_ID == WORLD_STATE_SCHEMA_ID
        assert namespace.WORLD_STATE_SCHEMA_VERSION == "0.1"
        assert namespace.WORLD_STATE_FORMAT_VERSION == "0.1"
        assert namespace.load_world_state is load_world_state
        assert namespace.WorldState.__name__ == "WorldState"
