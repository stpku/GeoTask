"""GT38 trajectory identity adjudication case tests."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "examples" / "core"
BUILDER = CORE / "gt38_build_trajectory_identity_adjudication.py"
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
SCENARIO = CORE / "gt38_trajectory_identity_adjudication.json"
GENERATED = [PROFILE, *DESCRIPTORS, REQUEST, *RESPONSES, ADJUDICATION, SCENARIO]


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_builder():
    spec = importlib.util.spec_from_file_location("gt38_builder", BUILDER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_gt38_exact_sources_rebuild_the_adjudication() -> None:
    from geotask_core.v1.trajectory_identity_adjudication import (
        load_trajectory_identity_adjudication,
        validate_trajectory_identity_adjudication_bindings,
    )

    adjudication = load_trajectory_identity_adjudication(_json(ADJUDICATION))
    validate_trajectory_identity_adjudication_bindings(
        adjudication,
        candidate_result_bytes=CANDIDATE.read_bytes(),
        verification_request_bytes=REQUEST.read_bytes(),
        assurance_profile_bytes=PROFILE.read_bytes(),
        provider_descriptor_bytes=[path.read_bytes() for path in DESCRIPTORS],
        verification_response_bytes=[path.read_bytes() for path in RESPONSES],
    )
    assert adjudication.adjudication_state == "same_object_confirmed"
    assert adjudication.candidate_alignment == "aligned"
    assert adjudication.identity_merge_recommendation == (
        "recommend_identity_merge_review"
    )
    assert adjudication.next_action == "review_identity_merge"


def test_gt38_preserves_original_subjects_and_never_merges() -> None:
    body = _json(ADJUDICATION)["trajectory_identity_adjudication"]
    assert body["identity_pair"]["first_subject_ref"] == "provisional_alpha"
    assert body["identity_pair"]["second_subject_ref"] == "provisional_beta"
    assert body["policy_result"]["provider_count"] == 2
    assert body["policy_result"]["independent_group_count"] == 2
    assert body["policy_result"]["same_object_response_refs"] == [
        "response-1",
        "response-2",
    ]
    for field in (
        "external_identity_verified_by_core",
        "identity_merge_performed",
        "subject_refs_mutated",
        "production_output_released",
        "action_authorized",
        "action_executed",
    ):
        assert body[field] is False


def test_gt38_registered_artifact_validates_structurally() -> None:
    from geotask_core.v1.artifact_validation import validate_artifact_payload

    report = validate_artifact_payload(
        "geotask.trajectory-identity-adjudication",
        _json(ADJUDICATION),
        file=str(ADJUDICATION.relative_to(ROOT)),
    ).to_dict()["artifact_validation"]
    assert report["valid"] is True
    assert report["schema_verified"] is True
    assert report["summary"]["adjudication_state"] == "same_object_confirmed"
    assert report["summary"]["identity_merge_recommendation"] == (
        "recommend_identity_merge_review"
    )
    assert report["summary"]["candidate_binding_verified"] is False
    assert report["summary"]["verification_bindings_verified"] is False
    assert report["summary"]["identity_merge_performed"] is False


def test_gt38_scenario_hashes_bind_every_retained_artifact() -> None:
    scenario = _json(SCENARIO)["scenario"]
    assert scenario["sha256"] == {
        "candidate_result": _sha(CANDIDATE),
        "assurance_profile": _sha(PROFILE),
        "verification_request": _sha(REQUEST),
        "asset_registry_descriptor": _sha(DESCRIPTORS[0]),
        "human_reviewer_descriptor": _sha(DESCRIPTORS[1]),
        "asset_registry_response": _sha(RESPONSES[0]),
        "human_reviewer_response": _sha(RESPONSES[1]),
        "identity_adjudication": _sha(ADJUDICATION),
    }


def test_gt38_scenario_exposes_review_not_execution_boundary() -> None:
    scenario = _json(SCENARIO)["scenario"]
    assert scenario["candidate"] == {
        "source_case": "GT37",
        "state": "same_object_candidate",
        "first_subject_ref": "provisional_alpha",
        "second_subject_ref": "provisional_beta",
    }
    assert scenario["adjudication"] == {
        "state": "same_object_confirmed",
        "candidate_alignment": "aligned",
        "identity_merge_recommendation": "recommend_identity_merge_review",
        "next_action": "review_identity_merge",
    }
    boundaries = scenario["boundaries"]
    assert boundaries["independent_evidence_satisfied"] is True
    assert boundaries["identity_merge_review_recommended"] is True
    assert boundaries["external_identity_verified_by_core"] is False
    assert boundaries["identity_merge_performed"] is False
    assert boundaries["subject_refs_mutated"] is False
    assert boundaries["production_output_released"] is False
    assert boundaries["action_authorized"] is False
    assert boundaries["action_executed"] is False


def test_gt38_builder_reproduces_all_fixed_outputs() -> None:
    before = {path.name: path.read_bytes() for path in GENERATED}
    _load_builder().build()
    after = {path.name: path.read_bytes() for path in GENERATED}
    assert after == before


def test_gt38_provider_inputs_remain_fictional_and_side_effect_free() -> None:
    for path in DESCRIPTORS:
        body = _json(path)["verification_provider_descriptor"]
        assert body["implementation_kind"] == "mock"
        assert body["production_ready"] is False
        assert body["external_side_effects_allowed"] is False
    for path in RESPONSES:
        body = _json(path)["verification_response"]
        assert body["independently_verified"] is False
        assert body["production_output_released"] is False
        assert body["action_authorized"] is False
        assert body["action_executed"] is False
