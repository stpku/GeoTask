"""Fixed GT39 identity-merge proposal case tests."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from geotask_core import (
    IDENTITY_MERGE_PROPOSAL_ARTIFACT_ID,
    load_identity_merge_proposal,
    validate_artifact_file,
    validate_identity_merge_proposal_bindings,
)


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "core"
BUILDER = EXAMPLES / "gt39_build_identity_merge_proposal.py"
ADJUDICATION = EXAMPLES / "trajectory_identity_adjudication_gt38.json"
PROPOSAL = EXAMPLES / "identity_merge_proposal_gt39.json"
SCENARIO = EXAMPLES / "gt39_identity_merge_proposal.json"


def _load_builder():
    spec = importlib.util.spec_from_file_location("gt39_builder", BUILDER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gt39_fixed_builder_reproduces_committed_artifacts() -> None:
    built = _load_builder().build()
    assert built["proposal"] == json.loads(PROPOSAL.read_text(encoding="utf-8"))
    assert built["scenario"] == json.loads(SCENARIO.read_text(encoding="utf-8"))


def test_gt39_fixed_proposal_is_strict_and_exact_bound() -> None:
    proposal = load_identity_merge_proposal(
        json.loads(PROPOSAL.read_text(encoding="utf-8"))
    )
    validate_identity_merge_proposal_bindings(
        proposal,
        adjudication_bytes=ADJUDICATION.read_bytes(),
    )
    assert proposal.canonical_subject_ref == "provisional_alpha"
    assert proposal.merge_subject_ref == "provisional_beta"
    assert proposal.affected_trajectory_refs == ("track_alpha", "track_beta")
    assert proposal.proposed_subject_ref_rewrites[0].trajectory_ref == "track_beta"
    assert proposal.retained_aliases[0].state == "retain_as_alias"
    assert proposal.reversal_plan.reversal_executed is False


def test_gt39_fixed_proposal_passes_unified_validation() -> None:
    report = validate_artifact_file(IDENTITY_MERGE_PROPOSAL_ARTIFACT_ID, PROPOSAL)
    assert report.valid is True
    assert report.summary["proposal_state"] == "ready_for_review"
    assert report.summary["source_binding_verified"] is False
    assert report.summary["scope_closed"] is True
    assert report.summary["aliases_preserved"] is True
    assert report.summary["proposal_approved"] is False
    assert report.summary["identity_merge_performed"] is False


def test_gt39_scenario_preserves_non_execution_boundary() -> None:
    scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
    assert scenario["case_id"] == "GT39"
    assert scenario["proposal_state"] == "ready_for_review"
    assert scenario["review_action"] == "review_identity_merge_proposal"
    assert scenario["next_action"] == "request_identity_merge_approval"
    assert set(scenario["boundaries"].values()) == {False}
