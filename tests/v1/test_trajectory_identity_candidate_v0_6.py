"""v0.6 trajectory identity-candidate contract tests."""

from __future__ import annotations

import copy

import pytest


PARAMETERS = {
    "maximum_identity_gap_seconds": 120,
    "maximum_identity_distance_in_horizontal_unit": 10,
    "require_same_object_class": True,
}


def _document() -> dict:
    return {
        "geotask": {
            "id": "gt37-trajectory-identity-candidate",
            "name": "GT37 Trajectory Identity Candidate",
            "description": "Classify two trajectory fragments without merging identities.",
            "schema_version": "1.0",
            "language": "en",
            "domain": "general_spatial",
        },
        "space": {
            "crs": {"type": "local_cartesian", "identifier": "fictional_local_xy_m"},
            "axes": {"x": "east", "y": "north"},
            "horizontal_unit": "meter",
            "coordinate_order": ["x", "y"],
        },
        "objects": {
            "provisional_alpha": {
                "type": "moving_object",
                "object_class": "uav",
                "identity": "fictional-provisional-alpha",
            },
            "provisional_beta": {
                "type": "moving_object",
                "object_class": "uav",
                "identity": "fictional-provisional-beta",
            },
            "track_alpha": {
                "type": "trajectory",
                "subject_ref": "provisional_alpha",
                "interpolation": "none",
                "samples": [
                    {
                        "observed_at": "2026-08-05T08:00:00+08:00",
                        "coordinates": [0, 0],
                    },
                    {
                        "observed_at": "2026-08-05T08:02:00+08:00",
                        "coordinates": [36, 48],
                    },
                ],
            },
            "track_beta": {
                "type": "trajectory",
                "subject_ref": "provisional_beta",
                "interpolation": "none",
                "samples": [
                    {
                        "observed_at": "2026-08-05T08:03:00+08:00",
                        "coordinates": [39, 52],
                    },
                    {
                        "observed_at": "2026-08-05T08:05:00+08:00",
                        "coordinates": [75, 100],
                    },
                ],
            },
        },
        "operator_set": ["trajectory_identity_candidate"],
        "tasks": [
            {
                "id": "classify_identity_candidate",
                "family": "trajectory_identity",
                "goal": "Classify a boundary-sample identity candidate without merging objects.",
                "assertions": [
                    {
                        "id": "identity_candidate",
                        "operator": "trajectory_identity_candidate",
                        "object_refs": ["track_alpha", "track_beta"],
                        "parameters": copy.deepcopy(PARAMETERS),
                        "expected_type": "object",
                    }
                ],
                "outputs": ["identity_candidate"],
            }
        ],
        "execution": {
            "mode": "local_only",
            "steps": [
                {
                    "id": "classify_identity",
                    "executor": "local",
                    "assertion_refs": ["identity_candidate"],
                    "depends_on": [],
                }
            ],
        },
        "verification": {
            "mode": "local_deterministic",
            "required_assurance": "local_deterministic",
        },
        "output_contract": {
            "format": "structured",
            "required_fields": ["identity_candidate"],
            "allow_additional_fields": False,
            "allow_model_inference": False,
        },
    }


def _execute(payload: dict) -> dict:
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    result = execute_canonical(canonicalize(payload))
    assert result.overall.status == "verified"
    return result.outputs["identity_candidate"]


def test_same_object_candidate_binds_boundary_evidence_without_merge() -> None:
    from geotask_core.parser import validate_document
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.validator import validate_canonical

    payload = _document()
    assert validate_document(copy.deepcopy(payload)) == []
    canonical = canonicalize(payload)
    assert validate_canonical(canonical) == []

    record = _execute(payload)
    assert record["candidate_state"] == "same_object_candidate"
    assert record["candidate_reason"] == (
        "boundary_samples_within_declared_time_and_distance_limits"
    )
    assert record["first_trajectory_ref"] == "track_alpha"
    assert record["second_trajectory_ref"] == "track_beta"
    assert record["first_subject_ref"] == "provisional_alpha"
    assert record["second_subject_ref"] == "provisional_beta"
    assert record["first_object_class"] == "uav"
    assert record["second_object_class"] == "uav"
    assert record["first_boundary_sample_index"] == 1
    assert record["second_boundary_sample_index"] == 0
    assert record["temporal_gap_seconds"] == 60.0
    assert record["spatial_distance_in_horizontal_unit"] == 5.0
    assert record["identity_merge_performed"] is False
    assert record["subject_refs_mutated"] is False


def test_far_boundary_is_different_object_candidate() -> None:
    payload = _document()
    payload["objects"]["track_beta"]["samples"][0]["coordinates"] = [136, 48]
    record = _execute(payload)
    assert record["candidate_state"] == "different_object_candidate"
    assert record["candidate_reason"] == "boundary_distance_exceeds_declared_maximum"
    assert record["spatial_distance_in_horizontal_unit"] == 100.0


def test_class_mismatch_is_different_when_required() -> None:
    payload = _document()
    payload["objects"]["provisional_beta"]["object_class"] = "ground_vehicle"
    record = _execute(payload)
    assert record["candidate_state"] == "different_object_candidate"
    assert record["candidate_reason"] == (
        "object_classes_differ_under_declared_requirement"
    )


def test_excessive_positive_gap_is_unverifiable_before_distance_or_class() -> None:
    payload = _document()
    payload["objects"]["provisional_beta"]["object_class"] = "ground_vehicle"
    payload["objects"]["track_beta"]["samples"][0]["observed_at"] = (
        "2026-08-05T08:12:00+08:00"
    )
    payload["objects"]["track_beta"]["samples"][1]["observed_at"] = (
        "2026-08-05T08:14:00+08:00"
    )
    record = _execute(payload)
    assert record["candidate_state"] == "unverifiable"
    assert record["candidate_reason"] == "temporal_gap_exceeds_declared_maximum"
    assert record["temporal_gap_seconds"] == 600.0
    assert record["spatial_distance_in_horizontal_unit"] == 5.0


def test_overlap_or_reverse_order_is_rejected() -> None:
    from geotask_core.ops import trajectory_identity_candidate

    first = {
        "trajectory_ref": "a",
        "subject_ref": "a_subject",
        "object_class": "uav",
        "samples": _document()["objects"]["track_alpha"]["samples"],
    }
    second = {
        "trajectory_ref": "b",
        "subject_ref": "b_subject",
        "object_class": "uav",
        "samples": copy.deepcopy(_document()["objects"]["track_beta"]["samples"]),
    }
    second["samples"][0]["observed_at"] = "2026-08-05T08:01:00+08:00"
    with pytest.raises(ValueError, match="start after the first trajectory ends"):
        trajectory_identity_candidate(first, second, **PARAMETERS)


def test_exact_identity_parameters_are_required() -> None:
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.validator import validate_canonical

    payload = _document()
    del payload["tasks"][0]["assertions"][0]["parameters"][
        "maximum_identity_gap_seconds"
    ]
    assert any(
        item["code"] == "missing_field"
        for item in validate_canonical(canonicalize(payload))
    )

    payload = _document()
    payload["tasks"][0]["assertions"][0]["parameters"]["invented"] = 1
    assert any(
        item["code"] == "unknown_field"
        for item in validate_canonical(canonicalize(payload))
    )

    invalid_values = (
        ("maximum_identity_gap_seconds", 0),
        ("maximum_identity_gap_seconds", True),
        ("maximum_identity_distance_in_horizontal_unit", -1),
        ("maximum_identity_distance_in_horizontal_unit", float("nan")),
        ("require_same_object_class", "true"),
    )
    for name, value in invalid_values:
        payload = _document()
        payload["tasks"][0]["assertions"][0]["parameters"][name] = value
        diagnostics = validate_canonical(canonicalize(payload))
        assert any(
            item["code"] == "invalid_type" and name in item["path"]
            for item in diagnostics
        )


def test_public_api_registry_and_no_overclaim_contract() -> None:
    import geotask_core
    from geotask_core.operator_registry import get_operator_metadata, operator_names

    assert geotask_core.TrajectoryIdentityCandidate.__name__ == (
        "TrajectoryIdentityCandidate"
    )
    assert callable(geotask_core.trajectory_identity_candidate)
    assert "trajectory_identity_candidate" in operator_names()
    metadata = get_operator_metadata("trajectory_identity_candidate")
    assert metadata["supported_geometry"] == ["trajectory", "trajectory"]
    assert metadata["output_type"] == "dict"
    assert metadata["semantics"]["candidate_vocabulary"] == [
        "same_object_candidate",
        "different_object_candidate",
        "unverifiable",
    ]
    assert metadata["semantics"]["identity_merge_performed"] is False
    assert metadata["semantics"]["subject_refs_mutated"] is False
