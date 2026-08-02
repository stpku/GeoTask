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
from geotask_core.v1.verification_session import (
    VERIFICATION_SESSION_SCHEMA_ID,
    VerificationSessionFormatError,
    load_verification_session,
    validate_verification_session_bindings,
)
from geotask_core.v1.world_state import load_world_state


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "examples" / "core"
EXAMPLE = CORE / "verification_session_uav_recheck.json"
STATE = CORE / "world_state_uav_separation_recheck.json"
TASK = CORE / "uav_route_crossing_temporal_separation.yaml"
RESULT = CORE / "verification_session_uav_execution_result.json"
TRANSITION = CORE / "state_transition_uav_separation_recheck.json"
SCHEMA = ROOT / "schemas" / "geotask-verification-session-v0.1.schema.json"


def _payload() -> dict[str, object]:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def _contents() -> dict[str, bytes]:
    return {
        "task-gt16": TASK.read_bytes(),
        "result-gt16-initial": RESULT.read_bytes(),
        "transition-uav-recheck": TRANSITION.read_bytes(),
    }


def test_verification_session_example_matches_schema_loader_and_bindings() -> None:
    payload = _payload()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert list(Draft202012Validator(schema).iter_errors(payload)) == []

    session = load_verification_session(payload)
    state = load_world_state(json.loads(STATE.read_text(encoding="utf-8")))
    validate_verification_session_bindings(session, state, _contents())

    assert session.session_id == "fictional-uav-separation-verification-session"
    assert session.state == "blocked"
    assert session.world_state.revision == 2
    assert len(session.all_artifact_refs()) == 3
    assert len(session.action_eligibility) == 2
    assert len(session.recheck_triggers) == 1
    assert session.semantic_fingerprint() == (
        "3f74249c9a8263a46fd4c726a888a3a727bbbf500a4e80b9cc1f275f684ea604"
    )
    assert load_verification_session(session.to_dict()) == session


def test_verification_session_fingerprint_is_order_independent() -> None:
    payload = _payload()
    reordered = copy.deepcopy(payload)
    body = reordered["verification_session"]
    body["observation_refs"].reverse()
    body["action_eligibility"].reverse()
    for item in body["action_eligibility"]:
        item["basis_refs"].reverse()
        item["observation_refs"].reverse()
    body["recheck_triggers"].reverse()
    for item in body["recheck_triggers"]:
        item["affected_output_refs"].reverse()
        item["basis_refs"].reverse()
        item["observation_refs"].reverse()

    assert load_verification_session(reordered).semantic_fingerprint() == (
        load_verification_session(payload).semantic_fingerprint()
    )


def test_verification_session_rejects_time_and_artifact_type_mismatches() -> None:
    payload = _payload()
    payload["verification_session"]["recorded_at"] = "2026-07-16T10:00:59+08:00"
    with pytest.raises(VerificationSessionFormatError, match="world_state.as_of"):
        load_verification_session(payload)

    payload = _payload()
    payload["verification_session"]["task_refs"][0]["artifact_id"] = (
        "geotask.execution-result"
    )
    with pytest.raises(VerificationSessionFormatError, match="geotask.document"):
        load_verification_session(payload)

    payload = _payload()
    payload["verification_session"]["task_refs"][0]["schema_version"] = "0.1"
    with pytest.raises(VerificationSessionFormatError, match="must equal '1.0'"):
        load_verification_session(payload)

    discrepancy_ref = {
        "ref_id": "discrepancy-uav-recheck",
        "artifact_id": "geotask.execution-result",
        "schema_version": "0.1",
        "instance_id": "fictional-uav-separation-discrepancy-report",
        "content_sha256": "0" * 64,
    }
    payload = _payload()
    payload["verification_session"]["discrepancy_refs"] = [discrepancy_ref]
    with pytest.raises(VerificationSessionFormatError, match="geotask.discrepancy-report"):
        load_verification_session(payload)

    payload = _payload()
    discrepancy_ref["artifact_id"] = "geotask.discrepancy-report"
    discrepancy_ref["schema_version"] = "1.0"
    payload["verification_session"]["discrepancy_refs"] = [discrepancy_ref]
    with pytest.raises(VerificationSessionFormatError, match="must equal '0.1'"):
        load_verification_session(payload)


def test_verification_session_rejects_open_and_duplicate_references() -> None:
    payload = _payload()
    payload["verification_session"]["action_eligibility"][0]["basis_refs"] = [
        "missing"
    ]
    with pytest.raises(VerificationSessionFormatError, match="artifact reference lists"):
        load_verification_session(payload)

    payload = _payload()
    payload["verification_session"]["execution_result_refs"][0]["ref_id"] = (
        "task-gt16"
    )
    with pytest.raises(VerificationSessionFormatError, match="duplicates ref_id"):
        load_verification_session(payload)

    payload = _payload()
    duplicate = copy.deepcopy(payload["verification_session"]["action_eligibility"][0])
    payload["verification_session"]["action_eligibility"].append(duplicate)
    with pytest.raises(VerificationSessionFormatError, match="duplicates output_ref"):
        load_verification_session(payload)


def test_verification_session_rejects_inconsistent_outcome_and_trigger() -> None:
    payload = _payload()
    payload["verification_session"]["state"] = "blocked"
    payload["verification_session"]["action_eligibility"][0]["state"] = "eligible"
    with pytest.raises(VerificationSessionFormatError, match="blocked requires"):
        load_verification_session(payload)

    payload = _payload()
    payload["verification_session"]["state"] = "need_review"
    payload["verification_session"]["action_eligibility"][0]["state"] = "eligible"
    with pytest.raises(VerificationSessionFormatError, match="satisfied must affect"):
        load_verification_session(payload)

    payload = _payload()
    payload["verification_session"]["recheck_triggers"][0][
        "affected_output_refs"
    ] = ["missing-output"]
    with pytest.raises(VerificationSessionFormatError, match="action_eligibility"):
        load_verification_session(payload)


def test_verification_session_binding_validation_fails_closed() -> None:
    session = load_verification_session(_payload())
    state = load_world_state(json.loads(STATE.read_text(encoding="utf-8")))

    contents = _contents()
    contents["task-gt16"] += b"\n"
    with pytest.raises(VerificationSessionFormatError, match="SHA-256 mismatch"):
        validate_verification_session_bindings(session, state, contents)

    contents = _contents()
    del contents["transition-uav-recheck"]
    with pytest.raises(VerificationSessionFormatError, match="missing ref_id"):
        validate_verification_session_bindings(session, state, contents)

    contents = _contents()
    contents["extra"] = b"extra"
    with pytest.raises(VerificationSessionFormatError, match="unknown ref_id"):
        validate_verification_session_bindings(session, state, contents)


def test_verification_session_rejects_world_state_observation_mismatch() -> None:
    state_payload = json.loads(STATE.read_text(encoding="utf-8"))
    state_payload["world_state"]["observation_refs"] = ["different-observation"]
    state_payload["world_state"]["objects"][1]["observation_refs"] = [
        "different-observation"
    ]
    state_payload["world_state"]["objects"][1]["attributes"][1][
        "observation_refs"
    ] = ["different-observation"]
    state_payload["world_state"]["relations"][1]["observation_refs"] = [
        "different-observation"
    ]
    state = load_world_state(state_payload)
    session_payload = _payload()
    session_payload["verification_session"]["world_state"][
        "semantic_fingerprint"
    ] = state.semantic_fingerprint()
    session = load_verification_session(session_payload)

    with pytest.raises(VerificationSessionFormatError, match="not declared"):
        validate_verification_session_bindings(session, state, _contents())


def test_verification_session_registry_and_unified_validation_are_fail_closed() -> None:
    descriptor = get_artifact_descriptor("geotask.verification-session")
    assert descriptor.schema_id == VERIFICATION_SESSION_SCHEMA_ID
    assert descriptor.wrapper_key == "verification_session"
    assert descriptor.schema_path == (
        "schemas/geotask-verification-session-v0.1.schema.json"
    )
    assert descriptor.specification_path == (
        "docs/spec/geotask-verification-session-v0.1.md"
    )
    assert "examples/core/verification_session*.json" in descriptor.to_dict()[
        "ide_file_patterns"
    ]
    assert "does not validate linked artifact semantics" in descriptor.execution_boundary

    report = validate_artifact_payload(
        "geotask.verification-session", _payload(), file=EXAMPLE.as_posix()
    )
    assert report.valid is True
    assert report.schema_verified is True
    assert report.summary == {
        "session_id": "fictional-uav-separation-verification-session",
        "state": "blocked",
        "world_state_id": "fictional-uav-separation-state",
        "world_state_revision": 2,
        "observation_ref_count": 1,
        "artifact_ref_count": 3,
        "task_ref_count": 1,
        "execution_result_ref_count": 1,
        "control_evaluation_ref_count": 0,
        "state_transition_ref_count": 1,
        "discrepancy_ref_count": 0,
        "action_eligibility_count": 2,
        "blocked_action_count": 1,
        "unknown_action_count": 0,
        "recheck_trigger_count": 1,
        "satisfied_recheck_count": 1,
        "semantic_fingerprint": (
            "3f74249c9a8263a46fd4c726a888a3a727bbbf500a4e80b9cc1f275f684ea604"
        ),
        "world_state_binding_verified": False,
        "artifact_bindings_verified": False,
        "linked_artifact_semantics_verified": False,
        "tasks_executed": False,
        "controls_evaluated": False,
        "rechecks_executed": False,
        "external_truth_verified": False,
        "world_state_materialized": False,
        "action_authorized": False,
    }

    invalid = _payload()
    invalid["verification_session"]["task_refs"] = []
    invalid_report = validate_artifact_payload("geotask.verification-session", invalid)
    assert invalid_report.valid is False
    assert invalid_report.schema_verified is True
    assert invalid_report.diagnostics[0]["code"] == "invalid_verification_session"


def test_verification_session_public_python_namespaces_export_contract() -> None:
    for namespace in (geotask_core, v1):
        assert namespace.VERIFICATION_SESSION_ARTIFACT_ID == (
            "geotask.verification-session"
        )
        assert namespace.VERIFICATION_SESSION_SCHEMA_ID == VERIFICATION_SESSION_SCHEMA_ID
        assert namespace.VERIFICATION_SESSION_SCHEMA_VERSION == "0.1"
        assert namespace.VERIFICATION_SESSION_FORMAT_VERSION == "0.1"
        assert namespace.load_verification_session is load_verification_session
        assert (
            namespace.validate_verification_session_bindings
            is validate_verification_session_bindings
        )
        assert namespace.VerificationSession.__name__ == "VerificationSession"
