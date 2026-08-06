"""GT40 identity-merge approval record contract tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from geotask_core import (
    IDENTITY_MERGE_APPROVAL_RECORD_ARTIFACT_ID,
    IDENTITY_MERGE_APPROVAL_RECORD_SCHEMA_ID,
    IDENTITY_MERGE_APPROVAL_RECORD_SCHEMA_VERSION,
    IdentityMergeApprovalRecordError,
    build_identity_merge_approval_record,
    load_identity_merge_approval_record,
    validate_artifact_payload,
    validate_identity_merge_approval_record_bindings,
)


ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / "examples/core/identity_merge_proposal_gt39.json"
APPROVAL = ROOT / "examples/core/identity_merge_approval_record_gt40.json"
SCHEMA = ROOT / "schemas/geotask-identity-merge-approval-record-v0.1.schema.json"


def _decisions(
    *,
    identity: str = "approved",
    state: str = "approved",
) -> tuple[dict[str, object], ...]:
    return (
        {
            "approval_role": "identity_governance_reviewer",
            "reviewer_ref": "reviewer-identity",
            "decision": identity,
            "rationale": "Identity governance decision.",
            "decided_at": "2026-08-06T07:55:00+08:00",
            "evidence_refs": ["identity-evidence"] if identity == "evidence_required" else [],
        },
        {
            "approval_role": "world_state_maintainer",
            "reviewer_ref": "reviewer-state",
            "decision": state,
            "rationale": "World-state maintenance decision.",
            "decided_at": "2026-08-06T07:58:00+08:00",
            "evidence_refs": ["state-evidence"] if state == "evidence_required" else [],
        },
    )


def _build(*, decisions=None):
    return build_identity_merge_approval_record(
        approval_record_id="test-approval-record",
        created_at="2026-08-06T08:00:00+08:00",
        proposal_bytes=PROPOSAL.read_bytes(),
        approval_decisions=decisions or _decisions(),
    )


def test_public_constants_are_stable() -> None:
    assert (
        IDENTITY_MERGE_APPROVAL_RECORD_ARTIFACT_ID
        == "geotask.identity-merge-approval-record"
    )
    assert IDENTITY_MERGE_APPROVAL_RECORD_SCHEMA_ID.endswith(
        "geotask-identity-merge-approval-record-v0.1.schema.json"
    )
    assert IDENTITY_MERGE_APPROVAL_RECORD_SCHEMA_VERSION == "0.1"


def test_all_required_roles_can_approve_without_executing_merge() -> None:
    record = _build()
    assert record.aggregate_decision == "approved"
    assert record.approved_roles == (
        "identity_governance_reviewer",
        "world_state_maintainer",
    )
    assert record.proposal_approval_complete is True
    assert record.change_request_eligible is True
    assert record.next_action == "prepare_identity_merge_change_request"
    for field in (
        "identity_merge_performed",
        "subject_refs_mutated",
        "object_graph_mutated",
        "world_state_updated",
        "production_output_released",
        "action_authorized",
        "action_executed",
    ):
        assert getattr(record, field) is False


def test_rejection_takes_precedence_and_closes_proposal() -> None:
    record = _build(decisions=_decisions(identity="rejected"))
    assert record.aggregate_decision == "rejected"
    assert record.rejected_roles == ("identity_governance_reviewer",)
    assert record.proposal_approval_complete is False
    assert record.change_request_eligible is False
    assert record.next_action == "close_identity_merge_proposal"


def test_evidence_required_blocks_change_request() -> None:
    record = _build(decisions=_decisions(state="evidence_required"))
    assert record.aggregate_decision == "evidence_required"
    assert record.evidence_required_roles == ("world_state_maintainer",)
    assert record.proposal_approval_complete is False
    assert record.change_request_eligible is False
    assert record.next_action == "request_identity_merge_evidence"


def test_builder_requires_every_role_exactly_once() -> None:
    with pytest.raises(IdentityMergeApprovalRecordError, match="must cover every"):
        _build(decisions=_decisions()[:1])
    duplicate = list(_decisions())
    duplicate[1] = dict(duplicate[0])
    with pytest.raises(IdentityMergeApprovalRecordError, match="duplicates"):
        _build(decisions=tuple(duplicate))


def test_evidence_required_decision_requires_evidence_reference() -> None:
    decisions = list(_decisions(state="evidence_required"))
    decisions[1]["evidence_refs"] = []
    with pytest.raises(IdentityMergeApprovalRecordError, match="at least one"):
        _build(decisions=tuple(decisions))


def test_strict_loader_rejects_execution_claims_and_derived_tampering() -> None:
    payload = _build().to_dict()
    for field in (
        "identity_merge_performed",
        "subject_refs_mutated",
        "object_graph_mutated",
        "world_state_updated",
        "production_output_released",
        "action_authorized",
        "action_executed",
    ):
        tampered = copy.deepcopy(payload)
        tampered["identity_merge_approval_record"][field] = True
        with pytest.raises(IdentityMergeApprovalRecordError, match="must be false"):
            load_identity_merge_approval_record(tampered)

    wrong = copy.deepcopy(payload)
    wrong["identity_merge_approval_record"]["aggregate_decision"] = "rejected"
    with pytest.raises(IdentityMergeApprovalRecordError, match="decision_reason"):
        load_identity_merge_approval_record(wrong)


def test_exact_binding_detects_insignificant_source_byte_change() -> None:
    record = _build()
    changed = PROPOSAL.read_bytes().replace(b"{\n", b"{  \n", 1)
    with pytest.raises(IdentityMergeApprovalRecordError, match="exact bound"):
        validate_identity_merge_approval_record_bindings(
            record,
            proposal_bytes=changed,
        )


def test_fixed_artifact_matches_schema_and_exact_binding() -> None:
    payload = json.loads(APPROVAL.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    record = load_identity_merge_approval_record(payload)
    validate_identity_merge_approval_record_bindings(
        record,
        proposal_bytes=PROPOSAL.read_bytes(),
    )


def test_generic_artifact_validation_is_structural_not_exact_replay() -> None:
    payload = json.loads(APPROVAL.read_text(encoding="utf-8"))
    report = validate_artifact_payload(
        IDENTITY_MERGE_APPROVAL_RECORD_ARTIFACT_ID,
        payload,
        file=APPROVAL.as_posix(),
    )
    assert report.valid is True
    assert report.summary["aggregate_decision"] == "approved"
    assert report.summary["proposal_binding_verified"] is False
    assert report.summary["change_request_eligible"] is True
    assert report.summary["identity_merge_performed"] is False
