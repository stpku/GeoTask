"""Build the fixed fictional GT40 identity-merge approval record."""

from __future__ import annotations

import json
from pathlib import Path

from geotask_core import (
    build_identity_merge_approval_record,
    load_identity_merge_approval_record,
    validate_identity_merge_approval_record_bindings,
)


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples" / "core"
PROPOSAL_PATH = EXAMPLES / "identity_merge_proposal_gt39.json"
APPROVAL_PATH = EXAMPLES / "identity_merge_approval_record_gt40.json"
SCENARIO_PATH = EXAMPLES / "gt40_identity_merge_approval_record.json"
STORY_PATH = EXAMPLES / "uav_017_identity_governance_story_gt38_gt42.json"


def _json_bytes(payload: dict[str, object]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def build() -> dict[str, object]:
    proposal_bytes = PROPOSAL_PATH.read_bytes()
    record = build_identity_merge_approval_record(
        approval_record_id="gt40-provisional-subject-merge-approval",
        created_at="2026-08-06T08:00:00+08:00",
        proposal_bytes=proposal_bytes,
        approval_decisions=(
            {
                "approval_role": "identity_governance_reviewer",
                "reviewer_ref": "fictional-reviewer-identity-01",
                "decision": "approved",
                "rationale": (
                    "The proposal preserves alias history, closes the affected scope, "
                    "and provides a reversible subject-reference rewrite."
                ),
                "decided_at": "2026-08-06T07:55:00+08:00",
                "evidence_refs": ["gt38-identity-adjudication", "gt39-merge-proposal"],
            },
            {
                "approval_role": "world_state_maintainer",
                "reviewer_ref": "fictional-reviewer-state-01",
                "decision": "approved",
                "rationale": (
                    "The proposal is eligible for a separate bounded change request; "
                    "no object graph or World State mutation is performed here."
                ),
                "decided_at": "2026-08-06T07:58:00+08:00",
                "evidence_refs": ["gt39-reversal-plan"],
            },
        ),
    )
    payload = record.to_dict()
    loaded = load_identity_merge_approval_record(payload)
    validate_identity_merge_approval_record_bindings(
        loaded,
        proposal_bytes=proposal_bytes,
    )
    story = json.loads(STORY_PATH.read_text(encoding="utf-8"))["composite_case"]
    scenario = {
        "case_id": "GT40",
        "title": "无人机身份归并提案由谁审批，批准后记录已经改变了吗？",
        "composite_case": {
            "id": story["id"],
            "stage": 3,
            "stage_count": len(story["stages"]),
            "stage_label_zh": story["stages"][2]["label_zh"],
            "story_file": STORY_PATH.relative_to(ROOT).as_posix(),
            "asset_label": story["asset_label"],
            "machine_to_display_mapping": story["machine_to_display_mapping"],
        },
        "source_artifact": PROPOSAL_PATH.relative_to(ROOT).as_posix(),
        "approval_artifact": APPROVAL_PATH.relative_to(ROOT).as_posix(),
        "aggregate_decision": loaded.aggregate_decision,
        "required_approval_roles": list(loaded.required_approval_roles),
        "approved_roles": list(loaded.approved_roles),
        "proposal_approval_complete": loaded.proposal_approval_complete,
        "change_request_eligible": loaded.change_request_eligible,
        "next_action": loaded.next_action,
        "boundaries": {
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
