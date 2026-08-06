"""Build the fixed fictional GT41 object-graph change request."""

from __future__ import annotations

import json
from pathlib import Path

from geotask_core.v1.object_graph_change_request import (
    build_object_graph_change_request,
    load_object_graph_change_request,
    validate_object_graph_change_request_bindings,
)


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples" / "core"
PROPOSAL_PATH = EXAMPLES / "identity_merge_proposal_gt39.json"
APPROVAL_PATH = EXAMPLES / "identity_merge_approval_record_gt40.json"
REQUEST_PATH = EXAMPLES / "object_graph_change_request_gt41.json"
SCENARIO_PATH = EXAMPLES / "gt41_object_graph_change_request.json"


def _json_bytes(payload: dict[str, object]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def build() -> dict[str, object]:
    proposal_bytes = PROPOSAL_PATH.read_bytes()
    approval_bytes = APPROVAL_PATH.read_bytes()
    request = build_object_graph_change_request(
        change_request_id="gt41-provisional-subject-object-graph-change",
        created_at="2026-08-06T09:30:00+08:00",
        proposal_bytes=proposal_bytes,
        approval_record_bytes=approval_bytes,
    )
    payload = request.to_dict()
    loaded = load_object_graph_change_request(payload)
    validate_object_graph_change_request_bindings(
        loaded,
        proposal_bytes=proposal_bytes,
        approval_record_bytes=approval_bytes,
    )
    operation = loaded.change_operations[0]
    scenario = {
        "case_id": "GT41",
        "title": "归并提案已获批，是否可以直接改写对象关系图？",
        "proposal_artifact": PROPOSAL_PATH.relative_to(ROOT).as_posix(),
        "approval_artifact": APPROVAL_PATH.relative_to(ROOT).as_posix(),
        "change_request_artifact": REQUEST_PATH.relative_to(ROOT).as_posix(),
        "request_state": loaded.request_state,
        "operation": operation.to_dict(),
        "preconditions": [item.to_dict() for item in loaded.preconditions],
        "acceptance_criteria": [
            item.to_dict() for item in loaded.acceptance_criteria
        ],
        "next_action": loaded.next_action,
        "boundaries": {
            "application_authorized": loaded.application_authorized,
            "change_applied": loaded.change_applied,
            "identity_merge_performed": loaded.identity_merge_performed,
            "subject_refs_mutated": loaded.subject_refs_mutated,
            "object_graph_mutated": loaded.object_graph_mutated,
            "world_state_updated": loaded.world_state_updated,
            "production_output_released": loaded.production_output_released,
            "action_authorized": loaded.action_authorized,
            "action_executed": loaded.action_executed,
        },
    }
    return {"request": payload, "scenario": scenario}


def main() -> None:
    built = build()
    REQUEST_PATH.write_bytes(_json_bytes(built["request"]))
    SCENARIO_PATH.write_bytes(_json_bytes(built["scenario"]))


if __name__ == "__main__":
    main()
