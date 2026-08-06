"""Executable GT41 fixed-case regression."""

from __future__ import annotations

import json
from pathlib import Path

from geotask_core import (
    load_object_graph_change_request,
    validate_object_graph_change_request_bindings,
)


ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / "examples/core/identity_merge_proposal_gt39.json"
APPROVAL = ROOT / "examples/core/identity_merge_approval_record_gt40.json"
REQUEST = ROOT / "examples/core/object_graph_change_request_gt41.json"
SCENARIO = ROOT / "examples/core/gt41_object_graph_change_request.json"


def test_gt41_fixed_case_is_exact_bound_closed_and_non_applying() -> None:
    payload = json.loads(REQUEST.read_text(encoding="utf-8"))
    scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
    request = load_object_graph_change_request(payload)
    validate_object_graph_change_request_bindings(
        request,
        proposal_bytes=PROPOSAL.read_bytes(),
        approval_record_bytes=APPROVAL.read_bytes(),
    )

    assert scenario["case_id"] == "GT41"
    assert request.request_state == "ready_for_application_review"
    assert request.next_action == "request_object_graph_change_application_approval"
    assert request.application_review_required is True
    assert len(request.change_operations) == 1
    operation = request.change_operations[0]
    assert operation.target_ref == "track_beta"
    assert operation.target_path == "/subject_ref"
    assert operation.before_subject_ref == "provisional_beta"
    assert operation.after_subject_ref == "provisional_alpha"
    assert len(request.preconditions) == 7
    assert len(request.acceptance_criteria) == 5
    assert scenario["boundaries"] == {
        "application_authorized": False,
        "change_applied": False,
        "identity_merge_performed": False,
        "subject_refs_mutated": False,
        "object_graph_mutated": False,
        "world_state_updated": False,
        "production_output_released": False,
        "action_authorized": False,
        "action_executed": False,
    }
