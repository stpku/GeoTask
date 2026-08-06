"""Executable GT42 fixed-case regression."""

from __future__ import annotations

import json
from pathlib import Path

from geotask_core import (
    load_object_graph_change_application_approval_record,
    validate_object_graph_change_application_approval_record_bindings,
)


ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "examples/core/object_graph_change_request_gt41.json"
APPROVAL = (
    ROOT / "examples/core/object_graph_change_application_approval_record_gt42.json"
)
SCENARIO = (
    ROOT / "examples/core/gt42_object_graph_change_application_approval_record.json"
)


def test_gt42_fixed_case_is_exact_bound_closed_and_non_applying() -> None:
    payload = json.loads(APPROVAL.read_text(encoding="utf-8"))
    scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
    approval = load_object_graph_change_application_approval_record(payload)
    validate_object_graph_change_application_approval_record_bindings(
        approval,
        change_request_bytes=REQUEST.read_bytes(),
    )

    assert scenario["case_id"] == "GT42"
    assert approval.aggregate_decision == "approved"
    assert approval.required_approval_roles == (
        "object_graph_change_owner",
        "world_state_governance_reviewer",
    )
    assert approval.approved_roles == approval.required_approval_roles
    assert approval.application_approval_complete is True
    assert approval.change_application_eligible is True
    assert approval.next_action == "prepare_bounded_object_graph_change_application"
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
