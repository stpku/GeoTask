"""Executable GT40 fixed-case regression."""

from __future__ import annotations

import json
from pathlib import Path

from geotask_core import (
    load_identity_merge_approval_record,
    validate_identity_merge_approval_record_bindings,
)


ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / "examples/core/identity_merge_proposal_gt39.json"
APPROVAL = ROOT / "examples/core/identity_merge_approval_record_gt40.json"
SCENARIO = ROOT / "examples/core/gt40_identity_merge_approval_record.json"


def test_gt40_fixed_case_is_exact_bound_and_non_executing() -> None:
    payload = json.loads(APPROVAL.read_text(encoding="utf-8"))
    scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
    record = load_identity_merge_approval_record(payload)
    validate_identity_merge_approval_record_bindings(
        record,
        proposal_bytes=PROPOSAL.read_bytes(),
    )

    assert scenario["case_id"] == "GT40"
    assert record.aggregate_decision == "approved"
    assert record.required_approval_roles == (
        "identity_governance_reviewer",
        "world_state_maintainer",
    )
    assert record.approved_roles == record.required_approval_roles
    assert record.proposal_approval_complete is True
    assert record.change_request_eligible is True
    assert record.next_action == "prepare_identity_merge_change_request"
    assert scenario["boundaries"] == {
        "identity_merge_performed": False,
        "subject_refs_mutated": False,
        "object_graph_mutated": False,
        "world_state_updated": False,
        "production_output_released": False,
        "action_authorized": False,
        "action_executed": False,
    }
