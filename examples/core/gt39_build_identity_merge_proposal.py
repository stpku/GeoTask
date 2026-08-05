"""Build the fixed fictional GT39 identity-merge proposal."""

from __future__ import annotations

import json
from pathlib import Path

from geotask_core import (
    build_identity_merge_proposal,
    load_identity_merge_proposal,
    validate_identity_merge_proposal_bindings,
)


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples" / "core"
ADJUDICATION_PATH = EXAMPLES / "trajectory_identity_adjudication_gt38.json"
PROPOSAL_PATH = EXAMPLES / "identity_merge_proposal_gt39.json"
SCENARIO_PATH = EXAMPLES / "gt39_identity_merge_proposal.json"


def _json_bytes(payload: dict[str, object]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def build() -> dict[str, object]:
    adjudication_bytes = ADJUDICATION_PATH.read_bytes()
    proposal = build_identity_merge_proposal(
        proposal_id="gt39-provisional-subject-merge-proposal",
        created_at="2026-08-05T09:45:00+08:00",
        adjudication_bytes=adjudication_bytes,
        canonical_subject_ref="provisional_alpha",
        proposal_rationale=(
            "GT38 provides aligned same-object evidence; retain provisional_beta as "
            "an auditable alias and require explicit review before any graph change."
        ),
        required_approvals=(
            "identity_governance_reviewer",
            "world_state_maintainer",
        ),
    )
    payload = proposal.to_dict()
    loaded = load_identity_merge_proposal(payload)
    validate_identity_merge_proposal_bindings(
        loaded,
        adjudication_bytes=adjudication_bytes,
    )
    scenario = {
        "case_id": "GT39",
        "title": "证据支持同一对象后，系统可以直接归并身份吗？",
        "source_artifact": ADJUDICATION_PATH.relative_to(ROOT).as_posix(),
        "proposal_artifact": PROPOSAL_PATH.relative_to(ROOT).as_posix(),
        "canonical_subject_ref": loaded.canonical_subject_ref,
        "merge_subject_ref": loaded.merge_subject_ref,
        "affected_trajectory_refs": list(loaded.affected_trajectory_refs),
        "proposal_state": loaded.proposal_state,
        "review_action": loaded.review_action,
        "next_action": loaded.next_action,
        "boundaries": {
            "new_identity_created": loaded.new_identity_created,
            "alias_deleted": loaded.alias_deleted,
            "proposal_approved": loaded.proposal_approved,
            "object_graph_mutated": loaded.object_graph_mutated,
            "identity_merge_performed": loaded.identity_merge_performed,
            "subject_refs_mutated": loaded.subject_refs_mutated,
            "world_state_updated": loaded.world_state_updated,
            "production_output_released": loaded.production_output_released,
            "action_authorized": loaded.action_authorized,
            "action_executed": loaded.action_executed,
        },
    }
    return {"proposal": payload, "scenario": scenario}


def main() -> None:
    built = build()
    PROPOSAL_PATH.write_bytes(_json_bytes(built["proposal"]))
    SCENARIO_PATH.write_bytes(_json_bytes(built["scenario"]))


if __name__ == "__main__":
    main()
