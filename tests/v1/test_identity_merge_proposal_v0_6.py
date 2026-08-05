"""GT39 identity-merge proposal contract tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from geotask_core import (
    IDENTITY_MERGE_BLOCKING_CONDITIONS,
    IDENTITY_MERGE_PROPOSAL_ARTIFACT_ID,
    IDENTITY_MERGE_PROPOSAL_SCHEMA_ID,
    IDENTITY_MERGE_PROPOSAL_SCHEMA_VERSION,
    IdentityMergeProposalError,
    build_identity_merge_proposal,
    load_identity_merge_proposal,
    validate_artifact_payload,
    validate_identity_merge_proposal_bindings,
)


ROOT = Path(__file__).resolve().parents[2]
ADJUDICATION = ROOT / "examples/core/trajectory_identity_adjudication_gt38.json"
PROPOSAL = ROOT / "examples/core/identity_merge_proposal_gt39.json"
SCHEMA = ROOT / "schemas/geotask-identity-merge-proposal-v0.1.schema.json"


def _build(*, canonical: str = "provisional_alpha"):
    return build_identity_merge_proposal(
        proposal_id="test-merge-proposal",
        created_at="2026-08-05T10:00:00+08:00",
        adjudication_bytes=ADJUDICATION.read_bytes(),
        canonical_subject_ref=canonical,
        proposal_rationale="Preserve provenance and require explicit review.",
        required_approvals=("identity_reviewer", "state_maintainer"),
    )


def test_public_constants_are_stable() -> None:
    assert IDENTITY_MERGE_PROPOSAL_ARTIFACT_ID == "geotask.identity-merge-proposal"
    assert IDENTITY_MERGE_PROPOSAL_SCHEMA_ID.endswith(
        "geotask-identity-merge-proposal-v0.1.schema.json"
    )
    assert IDENTITY_MERGE_PROPOSAL_SCHEMA_VERSION == "0.1"


def test_builder_selects_existing_canonical_and_preserves_alias() -> None:
    proposal = _build()
    assert proposal.proposal_state == "ready_for_review"
    assert proposal.canonical_subject_ref == "provisional_alpha"
    assert proposal.merge_subject_ref == "provisional_beta"
    assert proposal.affected_trajectory_refs == ("track_alpha", "track_beta")
    rewrite = proposal.proposed_subject_ref_rewrites[0]
    assert rewrite.trajectory_ref == "track_beta"
    assert rewrite.current_subject_ref == "provisional_beta"
    assert rewrite.proposed_subject_ref == "provisional_alpha"
    assert proposal.retained_aliases[0].alias_subject_ref == "provisional_beta"
    assert proposal.blocking_conditions == IDENTITY_MERGE_BLOCKING_CONDITIONS


def test_builder_can_select_the_other_existing_subject() -> None:
    proposal = _build(canonical="provisional_beta")
    assert proposal.merge_subject_ref == "provisional_alpha"
    rewrite = proposal.proposed_subject_ref_rewrites[0]
    assert rewrite.trajectory_ref == "track_alpha"
    assert rewrite.proposed_subject_ref == "provisional_beta"
    assert proposal.reversal_plan.restore_subject_refs[0].restore_subject_ref == (
        "provisional_alpha"
    )


def test_builder_rejects_new_canonical_identity() -> None:
    with pytest.raises(IdentityMergeProposalError, match="must select one existing"):
        _build(canonical="invented_primary_identity")


def test_builder_rejects_duplicate_approval_roles() -> None:
    with pytest.raises(IdentityMergeProposalError, match="duplicates"):
        build_identity_merge_proposal(
            proposal_id="duplicate-approval",
            created_at="2026-08-05T10:00:00+08:00",
            adjudication_bytes=ADJUDICATION.read_bytes(),
            canonical_subject_ref="provisional_alpha",
            proposal_rationale="Review required.",
            required_approvals=("reviewer", "reviewer"),
        )


def test_proposal_never_executes_or_mutates() -> None:
    proposal = _build()
    for field in (
        "new_identity_created",
        "alias_deleted",
        "proposal_approved",
        "object_graph_mutated",
        "identity_merge_performed",
        "subject_refs_mutated",
        "world_state_updated",
        "production_output_released",
        "action_authorized",
        "action_executed",
    ):
        assert getattr(proposal, field) is False


def test_strict_loader_rejects_claimed_approval_or_mutation() -> None:
    payload = _build().to_dict()
    for field in (
        "proposal_approved",
        "object_graph_mutated",
        "identity_merge_performed",
        "subject_refs_mutated",
        "world_state_updated",
        "production_output_released",
        "action_authorized",
        "action_executed",
    ):
        tampered = copy.deepcopy(payload)
        tampered["identity_merge_proposal"][field] = True
        with pytest.raises(IdentityMergeProposalError, match="must be false"):
            load_identity_merge_proposal(tampered)


def test_strict_loader_rejects_scope_expansion_and_alias_deletion() -> None:
    payload = _build().to_dict()
    expanded = copy.deepcopy(payload)
    expanded["identity_merge_proposal"]["affected_trajectory_refs"].append(
        "unrelated_track"
    )
    with pytest.raises(IdentityMergeProposalError, match="exactly two"):
        load_identity_merge_proposal(expanded)

    deleted = copy.deepcopy(payload)
    deleted["identity_merge_proposal"]["alias_deleted"] = True
    with pytest.raises(IdentityMergeProposalError, match="must be false"):
        load_identity_merge_proposal(deleted)


def test_strict_loader_rejects_incomplete_blocking_or_reversal_plan() -> None:
    payload = _build().to_dict()
    missing_block = copy.deepcopy(payload)
    missing_block["identity_merge_proposal"]["blocking_conditions"].pop()
    with pytest.raises(IdentityMergeProposalError, match="required closed set"):
        load_identity_merge_proposal(missing_block)

    wrong_reversal = copy.deepcopy(payload)
    wrong_reversal["identity_merge_proposal"]["reversal_plan"][
        "restore_subject_refs"
    ][0]["restore_subject_ref"] = "provisional_alpha"
    with pytest.raises(IdentityMergeProposalError, match="original subject"):
        load_identity_merge_proposal(wrong_reversal)


def test_exact_binding_replay_detects_insignificant_source_byte_change() -> None:
    proposal = _build()
    changed_bytes = ADJUDICATION.read_bytes().replace(b"{\n", b"{  \n", 1)
    with pytest.raises(IdentityMergeProposalError, match="rebuilt from exact"):
        validate_identity_merge_proposal_bindings(
            proposal,
            adjudication_bytes=changed_bytes,
        )


def test_fixed_artifact_matches_schema_and_exact_binding() -> None:
    payload = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    proposal = load_identity_merge_proposal(payload)
    validate_identity_merge_proposal_bindings(
        proposal,
        adjudication_bytes=ADJUDICATION.read_bytes(),
    )


def test_generic_artifact_validation_is_structural_not_exact_replay() -> None:
    payload = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    report = validate_artifact_payload(
        IDENTITY_MERGE_PROPOSAL_ARTIFACT_ID,
        payload,
        file=PROPOSAL.as_posix(),
    )
    assert report.valid is True
    assert report.summary["proposal_state"] == "ready_for_review"
    assert report.summary["source_binding_verified"] is False
    assert report.summary["identity_merge_performed"] is False
    assert report.summary["object_graph_mutated"] is False
