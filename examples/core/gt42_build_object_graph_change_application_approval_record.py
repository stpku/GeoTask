"""Build the fixed fictional GT42 object-graph change application approval."""

from __future__ import annotations

import json
from pathlib import Path

from geotask_core.v1.object_graph_change_application_approval_record import (
    build_object_graph_change_application_approval_record,
    load_object_graph_change_application_approval_record,
    validate_object_graph_change_application_approval_record_bindings,
)


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples" / "core"
REQUEST_PATH = EXAMPLES / "object_graph_change_request_gt41.json"
APPROVAL_PATH = (
    EXAMPLES / "object_graph_change_application_approval_record_gt42.json"
)
SCENARIO_PATH = (
    EXAMPLES / "gt42_object_graph_change_application_approval_record.json"
)
STORY_PATH = EXAMPLES / "uav_017_identity_governance_story_gt38_gt42.json"


def _json_bytes(payload: dict[str, object]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def build() -> dict[str, object]:
    request_bytes = REQUEST_PATH.read_bytes()
    required_roles = (
        "object_graph_change_owner",
        "world_state_governance_reviewer",
    )
    approval = build_object_graph_change_application_approval_record(
        approval_record_id="gt42-object-graph-change-application-approval",
        created_at="2026-08-06T11:30:00+08:00",
        change_request_bytes=request_bytes,
        required_approval_roles=required_roles,
        approval_decisions=(
            {
                "approval_role": "object_graph_change_owner",
                "reviewer_ref": "reviewer:object-graph-owner-alpha",
                "decision": "approved",
                "rationale": (
                    "The requested trajectory subject_ref rewrite remains within "
                    "the exact GT41 scope and retains alias history."
                ),
                "decided_at": "2026-08-06T11:20:00+08:00",
                "evidence_refs": [],
            },
            {
                "approval_role": "world_state_governance_reviewer",
                "reviewer_ref": "reviewer:world-state-governance-beta",
                "decision": "approved",
                "rationale": (
                    "The request preserves the World State boundary and requires "
                    "a later bounded application Artifact."
                ),
                "decided_at": "2026-08-06T11:25:00+08:00",
                "evidence_refs": [],
            },
        ),
    )
    payload = approval.to_dict()
    loaded = load_object_graph_change_application_approval_record(payload)
    validate_object_graph_change_application_approval_record_bindings(
        loaded,
        change_request_bytes=request_bytes,
    )
    story = json.loads(STORY_PATH.read_text(encoding="utf-8"))["composite_case"]
    scenario = {
        "case_id": "GT42",
        "title": "应用审批通过后，UAV-017的轨迹引用已经改变了吗？",
        "composite_case": {
            "id": story["id"],
            "stage": 5,
            "stage_count": len(story["stages"]),
            "stage_label_zh": story["stages"][4]["label_zh"],
            "story_file": STORY_PATH.relative_to(ROOT).as_posix(),
            "asset_label": story["asset_label"],
            "machine_to_display_mapping": story["machine_to_display_mapping"],
        },
        "change_request_artifact": REQUEST_PATH.relative_to(ROOT).as_posix(),
        "application_approval_artifact": APPROVAL_PATH.relative_to(ROOT).as_posix(),
        "aggregate_decision": loaded.aggregate_decision,
        "required_approval_roles": list(loaded.required_approval_roles),
        "approved_roles": list(loaded.approved_roles),
        "application_approval_complete": loaded.application_approval_complete,
        "change_application_eligible": loaded.change_application_eligible,
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
    return {"approval": payload, "scenario": scenario}


def main() -> None:
    built = build()
    APPROVAL_PATH.write_bytes(_json_bytes(built["approval"]))
    SCENARIO_PATH.write_bytes(_json_bytes(built["scenario"]))


if __name__ == "__main__":
    main()
