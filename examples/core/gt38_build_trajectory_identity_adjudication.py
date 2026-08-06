"""Build the fixed GT38 trajectory identity adjudication bundle.

All identities and evidence are fictional. Two independent mock providers review
one exact GT37 ``same_object_candidate`` and return the same identity verdict.
The resulting artifact may recommend a human identity-merge review, but it never
merges identities, rewrites ``subject_ref``, releases a production update,
authorizes action, or executes action.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

from geotask_core.v1.trajectory_identity_adjudication import (
    build_trajectory_identity_adjudication,
    load_trajectory_identity_adjudication,
    validate_trajectory_identity_adjudication_bindings,
)
from geotask_core.v1.verification_provider import (
    load_assurance_profile,
    load_verification_provider_descriptor,
    load_verification_request,
    load_verification_response,
    sha256_bytes,
)


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "examples" / "core"
CANDIDATE_RESULT = CORE / "gt37_trajectory_identity_candidate_result.json"
PROFILE = CORE / "assurance_profile_trajectory_identity_gt38.json"
REGISTRY_DESCRIPTOR = (
    CORE / "verification_provider_descriptor_asset_registry_gt38.json"
)
HUMAN_DESCRIPTOR = (
    CORE / "verification_provider_descriptor_human_identity_reviewer_gt38.json"
)
REQUEST = CORE / "verification_request_trajectory_identity_gt38.json"
REGISTRY_RESPONSE = CORE / "verification_response_asset_registry_gt38.json"
HUMAN_RESPONSE = CORE / "verification_response_human_identity_reviewer_gt38.json"
ADJUDICATION = CORE / "trajectory_identity_adjudication_gt38.json"
SCENARIO = CORE / "gt38_trajectory_identity_adjudication.json"
STORY = CORE / "uav_017_identity_governance_story_gt38_gt42.json"


class GT38BuildError(ValueError):
    """Raised when the fixed GT38 bundle crosses its declared boundary."""


def _bytes(payload: Mapping[str, object]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _write(path: Path, payload: Mapping[str, object]) -> bytes:
    raw = _bytes(payload)
    path.write_bytes(raw)
    return raw


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict[str, object]:
    candidate_bytes = CANDIDATE_RESULT.read_bytes()

    profile_payload = {
        "assurance_profile": {
            "profile_version": "0.1",
            "profile_id": "gt38-trajectory-identity-adjudication",
            "title": "GT38 independent trajectory identity adjudication",
            "minimum_provider_count": 2,
            "minimum_independent_groups": 2,
            "allowed_provider_types": [
                "authoritative_data_provider",
                "human_review",
            ],
            "require_fresh_results": True,
            "max_result_age_seconds": 3600,
            "require_reproducible": True,
            "accepted_reproducibility": ["repeatable"],
            "require_calibration": True,
            "accepted_calibration_states": ["not_applicable"],
            "conflict_policy": "unknown",
            "eligible_output": "identity_merge_recommendation",
            "blocked_outputs": [
                "automatic_identity_merge",
                "subject_ref_update",
            ],
            "blocked_actions": ["merge_identity", "rewrite_subject_ref"],
            "next_action_on_insufficient_assurance": "request_identity_evidence",
            "action_authorized": False,
            "action_executed": False,
        }
    }
    profile = load_assurance_profile(profile_payload)
    profile_bytes = _write(PROFILE, profile.to_dict())

    descriptor_payloads = [
        {
            "verification_provider_descriptor": {
                "interface_version": "0.1",
                "provider_id": "geotask.provider.mock-asset-registry",
                "provider_version": "0.1.0",
                "title": "Mock Asset Registry Identity Reviewer",
                "provider_type": "authoritative_data_provider",
                "implementation_kind": "mock",
                "production_ready": False,
                "capabilities": ["trajectory_identity_review"],
                "supported_methods": ["identity_evidence_review"],
                "independence_group": "fictional-asset-registry",
                "reproducibility": "repeatable",
                "calibration_status": "not_applicable",
                "valid_until": "2026-08-06T00:00:00+08:00",
                "audit_supported": True,
                "credentials_managed_externally": True,
                "external_side_effects_allowed": False,
            }
        },
        {
            "verification_provider_descriptor": {
                "interface_version": "0.1",
                "provider_id": "geotask.provider.mock-human-identity-reviewer",
                "provider_version": "0.1.0",
                "title": "Mock Human Trajectory Identity Reviewer",
                "provider_type": "human_review",
                "implementation_kind": "mock",
                "production_ready": False,
                "capabilities": ["trajectory_identity_review"],
                "supported_methods": ["identity_evidence_review"],
                "independence_group": "fictional-human-identity-board",
                "reproducibility": "repeatable",
                "calibration_status": "not_applicable",
                "valid_until": "2026-08-06T00:00:00+08:00",
                "audit_supported": True,
                "credentials_managed_externally": True,
                "external_side_effects_allowed": False,
            }
        },
    ]
    descriptors = [
        load_verification_provider_descriptor(payload)
        for payload in descriptor_payloads
    ]
    descriptor_paths = [REGISTRY_DESCRIPTOR, HUMAN_DESCRIPTOR]
    descriptor_bytes = [
        _write(path, descriptor.to_dict())
        for path, descriptor in zip(descriptor_paths, descriptors)
    ]

    request_payload = {
        "verification_request": {
            "request_version": "0.1",
            "request_id": "verify-trajectory-identity-gt38",
            "created_at": "2026-08-05T08:10:00+08:00",
            "subject": {
                "claim_id": "identity:provisional_alpha:provisional_beta",
                "claim_type": "trajectory_identity",
                "value": "same_object",
                "unit": None,
                "observed_at": "2026-08-05T08:03:00+08:00",
                "valid_until": "2026-08-05T09:00:00+08:00",
            },
            "input_artifacts": [
                {
                    "ref_id": "gt37-identity-candidate-result",
                    "artifact_id": "geotask.execution-result",
                    "sha256": sha256_bytes(candidate_bytes),
                }
            ],
            "verification_method": "identity_evidence_review",
            "required_capabilities": ["trajectory_identity_review"],
            "allowed_provider_types": [
                "authoritative_data_provider",
                "human_review",
            ],
            "assurance_profile_ref": {
                "profile_id": profile.profile_id,
                "sha256": sha256_bytes(profile_bytes),
            },
            "deadline": "2026-08-05T08:30:00+08:00",
            "external_side_effects_allowed": False,
            "action_authorized": False,
        }
    }
    request = load_verification_request(request_payload)
    request_bytes = _write(REQUEST, request.to_dict())

    response_payloads = []
    response_metadata = [
        (
            "trajectory-identity-response-asset-registry-gt38",
            "2026-08-05T08:14:00+08:00",
            0.99,
            [
                "fictional-registry:airframe-serial-match",
                "fictional-registry:operator-record-continuity",
            ],
        ),
        (
            "trajectory-identity-response-human-review-gt38",
            "2026-08-05T08:17:00+08:00",
            0.95,
            [
                "fictional-review:visual-marking-continuity",
                "fictional-review:telemetry-sequence-consistency",
            ],
        ),
    ]
    for descriptor, metadata in zip(descriptors, response_metadata):
        response_id, completed_at, confidence, evidence_refs = metadata
        response_payloads.append(
            {
                "verification_response": {
                    "response_version": "0.1",
                    "response_id": response_id,
                    "request_ref": {
                        "request_id": request.request_id,
                        "sha256": sha256_bytes(request_bytes),
                    },
                    "provider_ref": {
                        "provider_id": descriptor.provider_id,
                        "provider_version": descriptor.provider_version,
                        "sha256": sha256_bytes(
                            descriptor_bytes[descriptors.index(descriptor)]
                        ),
                    },
                    "state": "verified",
                    "result": {
                        "claim_id": request.subject.claim_id,
                        "claim_type": request.subject.claim_type,
                        "value": "same_object",
                        "unit": None,
                        "observed_at": "2026-08-05T08:03:00+08:00",
                        "valid_until": "2026-08-05T09:00:00+08:00",
                    },
                    "verification_method": request.verification_method,
                    "evidence_refs": evidence_refs,
                    "assurance_declarations": {
                        "independence_group": descriptor.independence_group,
                        "reproducibility": descriptor.reproducibility,
                        "calibration_status": descriptor.calibration_status,
                        "confidence": confidence,
                    },
                    "diagnostics": [],
                    "completed_at": completed_at,
                    "independently_verified": False,
                    "production_output_released": False,
                    "action_authorized": False,
                    "action_executed": False,
                }
            }
        )

    responses = [load_verification_response(payload) for payload in response_payloads]
    response_paths = [REGISTRY_RESPONSE, HUMAN_RESPONSE]
    response_bytes = [
        _write(path, response.to_dict())
        for path, response in zip(response_paths, responses)
    ]

    adjudication = build_trajectory_identity_adjudication(
        adjudication_id="gt38-trajectory-identity-adjudication",
        created_at="2026-08-05T08:20:00+08:00",
        candidate_result_bytes=candidate_bytes,
        verification_request_bytes=request_bytes,
        assurance_profile_bytes=profile_bytes,
        provider_descriptor_bytes=descriptor_bytes,
        verification_response_bytes=response_bytes,
    )
    adjudication_payload = adjudication.to_dict()
    adjudication_bytes = _write(ADJUDICATION, adjudication_payload)
    loaded = load_trajectory_identity_adjudication(adjudication_payload)
    validate_trajectory_identity_adjudication_bindings(
        loaded,
        candidate_result_bytes=candidate_bytes,
        verification_request_bytes=request_bytes,
        assurance_profile_bytes=profile_bytes,
        provider_descriptor_bytes=descriptor_bytes,
        verification_response_bytes=response_bytes,
    )

    if loaded.adjudication_state != "same_object_confirmed":
        raise GT38BuildError("GT38 fixed adjudication state changed")
    if loaded.identity_merge_recommendation != "recommend_identity_merge_review":
        raise GT38BuildError("GT38 fixed review recommendation changed")
    if loaded.next_action != "review_identity_merge":
        raise GT38BuildError("GT38 fixed next action changed")
    if loaded.policy_result.independent_group_count != 2:
        raise GT38BuildError("GT38 must retain two independent groups")
    if loaded.identity_pair.first_subject_ref == loaded.identity_pair.second_subject_ref:
        raise GT38BuildError("GT38 must preserve distinct provisional subjects")
    if any(
        (
            loaded.external_identity_verified_by_core,
            loaded.identity_merge_performed,
            loaded.subject_refs_mutated,
            loaded.production_output_released,
            loaded.action_authorized,
            loaded.action_executed,
        )
    ):
        raise GT38BuildError("GT38 crossed its non-execution boundary")

    story = json.loads(STORY.read_text(encoding="utf-8"))["composite_case"]
    scenario = {
        "scenario": {
            "id": "gt38-trajectory-identity-adjudication",
            "title_zh": "巡检无人机失联后出现新轨迹编号，两个证据源足以确认是同一架吗？",
            "title_en": "After an inspection drone is briefly lost and assigned a new track identity, are two independent evidence sources enough to confirm it is the same drone?",
            "composite_case": {
                "id": story["id"],
                "stage": 1,
                "stage_count": len(story["stages"]),
                "stage_label_zh": story["stages"][0]["label_zh"],
                "story_file": STORY.relative_to(ROOT).as_posix(),
                "asset_label": story["asset_label"],
                "operational_context": story["operational_context"],
                "timeline": story["timeline"],
                "independent_evidence": story["independent_evidence"],
                "business_risks": story["business_risks"],
                "machine_to_display_mapping": story["machine_to_display_mapping"],
            },
            "candidate": {
                "source_case": "GT37",
                "state": loaded.candidate_state,
                "first_subject_ref": loaded.identity_pair.first_subject_ref,
                "second_subject_ref": loaded.identity_pair.second_subject_ref,
            },
            "assurance_policy": {
                "minimum_provider_count": profile.minimum_provider_count,
                "minimum_independent_groups": profile.minimum_independent_groups,
                "conflict_policy": profile.conflict_policy,
                "blocked_outputs": list(profile.blocked_outputs),
                "blocked_actions": list(profile.blocked_actions),
            },
            "independent_evidence": [
                {
                    "provider_id": item.provider_id,
                    "provider_type": item.provider_type,
                    "independence_group": item.independence_group,
                    "verdict": response.verdict,
                }
                for item, response in zip(
                    loaded.provider_refs, loaded.response_refs
                )
            ],
            "adjudication": {
                "state": loaded.adjudication_state,
                "candidate_alignment": loaded.candidate_alignment,
                "identity_merge_recommendation": (
                    loaded.identity_merge_recommendation
                ),
                "next_action": loaded.next_action,
            },
            "incorrect_actions": [
                "merge_identifiers_inside_core",
                "rewrite_track_beta_subject_ref",
                "treat_a_review_recommendation_as_a_completed_merge",
                "discard_original_candidate_or_provider_responses",
                "publish_a_production_identity_update",
                "authorize_or_execute_identity_merge",
            ],
            "sha256": {
                "candidate_result": sha256_bytes(candidate_bytes),
                "assurance_profile": sha256_bytes(profile_bytes),
                "verification_request": sha256_bytes(request_bytes),
                "asset_registry_descriptor": sha256_bytes(descriptor_bytes[0]),
                "human_reviewer_descriptor": sha256_bytes(descriptor_bytes[1]),
                "asset_registry_response": sha256_bytes(response_bytes[0]),
                "human_reviewer_response": sha256_bytes(response_bytes[1]),
                "identity_adjudication": sha256_bytes(adjudication_bytes),
            },
            "boundaries": {
                "fictional_data": True,
                "candidate_binding_verified": True,
                "verification_bindings_verified": True,
                "independent_evidence_satisfied": True,
                "identity_merge_review_recommended": True,
                "external_identity_verified_by_core": False,
                "identity_merge_performed": False,
                "subject_refs_mutated": False,
                "production_output_released": False,
                "action_authorized": False,
                "action_executed": False,
            },
        }
    }
    _write(SCENARIO, scenario)
    return {
        "adjudication": adjudication_payload,
        "scenario": scenario,
    }


if __name__ == "__main__":
    build()
    print("GT38 trajectory identity adjudication bundle generated")
