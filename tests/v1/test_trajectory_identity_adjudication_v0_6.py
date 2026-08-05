"""v0.6 trajectory identity adjudication artifact tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "examples" / "core"
CANDIDATE = CORE / "gt37_trajectory_identity_candidate_result.json"
PROFILE = CORE / "assurance_profile_trajectory_identity_gt38.json"
DESCRIPTORS = [
    CORE / "verification_provider_descriptor_asset_registry_gt38.json",
    CORE / "verification_provider_descriptor_human_identity_reviewer_gt38.json",
]
REQUEST = CORE / "verification_request_trajectory_identity_gt38.json"
RESPONSES = [
    CORE / "verification_response_asset_registry_gt38.json",
    CORE / "verification_response_human_identity_reviewer_gt38.json",
]
ADJUDICATION = CORE / "trajectory_identity_adjudication_gt38.json"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _bytes(path: Path) -> bytes:
    return path.read_bytes()


def _serialized(payload: dict) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _build(*, response_bytes: list[bytes] | None = None, descriptor_bytes: list[bytes] | None = None):
    from geotask_core.v1.trajectory_identity_adjudication import (
        build_trajectory_identity_adjudication,
    )

    return build_trajectory_identity_adjudication(
        adjudication_id="gt38-test-adjudication",
        created_at="2026-08-05T08:20:00+08:00",
        candidate_result_bytes=_bytes(CANDIDATE),
        verification_request_bytes=_bytes(REQUEST),
        assurance_profile_bytes=_bytes(PROFILE),
        provider_descriptor_bytes=(
            descriptor_bytes or [_bytes(path) for path in DESCRIPTORS]
        ),
        verification_response_bytes=(
            response_bytes or [_bytes(path) for path in RESPONSES]
        ),
    )


def test_fixed_adjudication_loads_and_preserves_non_execution_boundary() -> None:
    from geotask_core.v1.trajectory_identity_adjudication import (
        load_trajectory_identity_adjudication,
    )

    result = load_trajectory_identity_adjudication(_json(ADJUDICATION))
    assert result.adjudication_state == "same_object_confirmed"
    assert result.candidate_state == "same_object_candidate"
    assert result.candidate_alignment == "aligned"
    assert result.identity_merge_recommendation == (
        "recommend_identity_merge_review"
    )
    assert result.next_action == "review_identity_merge"
    assert result.policy_result.provider_count == 2
    assert result.policy_result.usable_provider_count == 2
    assert result.policy_result.independent_group_count == 2
    assert result.policy_result.same_object_response_refs == (
        "response-1",
        "response-2",
    )
    assert result.identity_pair.first_subject_ref == "provisional_alpha"
    assert result.identity_pair.second_subject_ref == "provisional_beta"
    assert result.external_identity_verified_by_core is False
    assert result.identity_merge_performed is False
    assert result.subject_refs_mutated is False
    assert result.production_output_released is False
    assert result.action_authorized is False
    assert result.action_executed is False


def test_exact_binding_validation_rebuilds_the_fixed_artifact() -> None:
    from geotask_core.v1.trajectory_identity_adjudication import (
        load_trajectory_identity_adjudication,
        validate_trajectory_identity_adjudication_bindings,
    )

    result = load_trajectory_identity_adjudication(_json(ADJUDICATION))
    validate_trajectory_identity_adjudication_bindings(
        result,
        candidate_result_bytes=_bytes(CANDIDATE),
        verification_request_bytes=_bytes(REQUEST),
        assurance_profile_bytes=_bytes(PROFILE),
        provider_descriptor_bytes=[_bytes(path) for path in DESCRIPTORS],
        verification_response_bytes=[_bytes(path) for path in RESPONSES],
    )


def test_tampered_candidate_or_descriptor_bytes_fail_closed() -> None:
    from geotask_core.v1.trajectory_identity_adjudication import (
        TrajectoryIdentityAdjudicationError,
        build_trajectory_identity_adjudication,
    )

    with pytest.raises(TrajectoryIdentityAdjudicationError, match="input_artifacts"):
        build_trajectory_identity_adjudication(
            adjudication_id="tampered-candidate",
            created_at="2026-08-05T08:20:00+08:00",
            candidate_result_bytes=_bytes(CANDIDATE) + b"\n",
            verification_request_bytes=_bytes(REQUEST),
            assurance_profile_bytes=_bytes(PROFILE),
            provider_descriptor_bytes=[_bytes(path) for path in DESCRIPTORS],
            verification_response_bytes=[_bytes(path) for path in RESPONSES],
        )

    descriptors = [_bytes(path) for path in DESCRIPTORS]
    descriptors[0] += b"\n"
    with pytest.raises(TrajectoryIdentityAdjudicationError, match="SHA-256"):
        _build(descriptor_bytes=descriptors)


def test_conflicting_independent_verdicts_remain_unresolved() -> None:
    response_payloads = [_json(path) for path in RESPONSES]
    response_payloads[1]["verification_response"]["result"]["value"] = (
        "different_objects"
    )
    result = _build(response_bytes=[_serialized(item) for item in response_payloads])
    assert result.policy_result.state == "unknown"
    assert result.policy_result.reason == "independent_provider_conflict"
    assert result.adjudication_state == "unresolved"
    assert result.candidate_alignment == "unresolved"
    assert result.identity_merge_recommendation == "request_more_evidence"
    assert result.next_action == "request_identity_evidence"
    assert result.independent_evidence_satisfied is False
    assert result.identity_merge_performed is False


def test_insufficient_provider_count_remains_unresolved() -> None:
    result = _build(
        descriptor_bytes=[_bytes(DESCRIPTORS[0])],
        response_bytes=[_bytes(RESPONSES[0])],
    )
    assert result.policy_result.state == "unknown"
    assert any(
        item["code"] == "insufficient_provider_count"
        for item in result.policy_result.diagnostics
    )
    assert result.adjudication_state == "unresolved"
    assert result.identity_merge_recommendation == "request_more_evidence"


def test_loader_rejects_merge_mutation_and_partition_overclaims() -> None:
    from geotask_core.v1.trajectory_identity_adjudication import (
        TrajectoryIdentityAdjudicationError,
        load_trajectory_identity_adjudication,
    )

    for field in (
        "external_identity_verified_by_core",
        "identity_merge_performed",
        "subject_refs_mutated",
        "production_output_released",
        "action_authorized",
        "action_executed",
    ):
        payload = _json(ADJUDICATION)
        payload["trajectory_identity_adjudication"][field] = True
        with pytest.raises(TrajectoryIdentityAdjudicationError, match=field):
            load_trajectory_identity_adjudication(payload)

    payload = _json(ADJUDICATION)
    policy = payload["trajectory_identity_adjudication"]["policy_result"]
    policy["same_object_response_refs"] = ["response-1"]
    with pytest.raises(TrajectoryIdentityAdjudicationError, match="partition"):
        load_trajectory_identity_adjudication(payload)


def test_generic_artifact_validation_is_structural_not_binding_replay() -> None:
    from geotask_core.v1.artifact_validation import validate_artifact_payload

    report = validate_artifact_payload(
        "geotask.trajectory-identity-adjudication",
        _json(ADJUDICATION),
        file=str(ADJUDICATION.relative_to(ROOT)),
    ).to_dict()["artifact_validation"]
    assert report["valid"] is True
    assert report["schema_verified"] is True
    assert report["summary"]["adjudication_state"] == "same_object_confirmed"
    assert report["summary"]["provider_count"] == 2
    assert report["summary"]["candidate_binding_verified"] is False
    assert report["summary"]["verification_bindings_verified"] is False
    assert report["summary"]["identity_merge_performed"] is False


def test_public_api_and_registry_expose_gt38_contract() -> None:
    import geotask_core
    import geotask_core.v1 as v1
    from geotask_core.v1.artifact_registry import get_artifact_descriptor

    assert geotask_core.TrajectoryIdentityAdjudication is (
        v1.TrajectoryIdentityAdjudication
    )
    assert callable(geotask_core.build_trajectory_identity_adjudication)
    descriptor = get_artifact_descriptor(
        "geotask.trajectory-identity-adjudication"
    )
    assert descriptor.kind == "trajectory_identity_adjudication"
    assert descriptor.schema_version == "0.1"
    assert descriptor.wrapper_key == "trajectory_identity_adjudication"
    assert descriptor.schema_path.endswith(
        "geotask-trajectory-identity-adjudication-v0.1.schema.json"
    )
