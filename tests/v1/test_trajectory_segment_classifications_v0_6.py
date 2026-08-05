"""v0.6 trajectory stop/move and observation-gap classification tests."""

from __future__ import annotations

import copy

import pytest


PARAMETERS = {
    "stationary_radius_in_horizontal_unit": 5,
    "minimum_stationary_duration_seconds": 120,
    "maximum_observation_gap_seconds": 300,
    "allow_observation_gap": True,
}


def _document() -> dict:
    return {
        "geotask": {
            "id": "gt35-trajectory-stop-move-gap",
            "name": "GT35 Stop Move and Observation Gap",
            "description": "Classify explicit adjacent trajectory segments using caller-declared thresholds.",
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
            "uav_alpha": {
                "type": "moving_object",
                "object_class": "uav",
                "identity": "fictional-uav-alpha",
            },
            "uav_alpha_track": {
                "type": "trajectory",
                "subject_ref": "uav_alpha",
                "interpolation": "none",
                "samples": [
                    {
                        "observed_at": "2026-08-05T08:00:00+08:00",
                        "coordinates": [0, 0],
                    },
                    {
                        "observed_at": "2026-08-05T08:02:00+08:00",
                        "coordinates": [3, 4],
                    },
                    {
                        "observed_at": "2026-08-05T08:04:00+08:00",
                        "coordinates": [13, 4],
                    },
                    {
                        "observed_at": "2026-08-05T08:14:00+08:00",
                        "coordinates": [13, 4],
                    },
                ],
            },
        },
        "operator_set": ["trajectory_segment_classifications"],
        "tasks": [
            {
                "id": "classify_trajectory_segments",
                "family": "trajectory_classification",
                "goal": "Classify every adjacent explicit sample pair using only declared thresholds.",
                "assertions": [
                    {
                        "id": "trajectory_segment_states",
                        "operator": "trajectory_segment_classifications",
                        "object_refs": ["uav_alpha_track"],
                        "parameters": copy.deepcopy(PARAMETERS),
                        "expected_type": "array",
                    }
                ],
                "outputs": ["trajectory_segment_states"],
            }
        ],
        "execution": {
            "mode": "local_only",
            "steps": [
                {
                    "id": "classify_segments",
                    "executor": "local",
                    "assertion_refs": ["trajectory_segment_states"],
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
            "required_fields": ["trajectory_segment_states"],
            "allow_additional_fields": False,
            "allow_model_inference": False,
        },
    }


def test_classification_uses_explicit_thresholds_and_closed_vocabulary() -> None:
    from geotask_core.parser import validate_document
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical
    from geotask_core.v1.validator import validate_canonical

    payload = _document()
    assert validate_document(copy.deepcopy(payload)) == []
    canonical = canonicalize(payload)
    assert validate_canonical(canonical) == []

    result = execute_canonical(canonical)
    assert result.overall.status == "verified"
    records = result.outputs["trajectory_segment_states"]
    assert [record["classification"] for record in records] == [
        "stationary_candidate",
        "moving_observed",
        "observation_gap",
    ]
    assert [record["duration_seconds"] for record in records] == [120.0, 120.0, 600.0]
    assert [record["distance_in_horizontal_unit"] for record in records] == [5.0, 10.0, 0.0]
    assert all(record["stationary_radius_in_horizontal_unit"] == 5.0 for record in records)
    assert all(record["minimum_stationary_duration_seconds"] == 120.0 for record in records)
    assert all(record["maximum_observation_gap_seconds"] == 300.0 for record in records)
    assert all(record["allow_observation_gap"] is True for record in records)


def test_excessive_interval_becomes_unverifiable_when_gap_marking_disallowed() -> None:
    from geotask_core.ops import trajectory_segment_classifications

    samples = _document()["objects"]["uav_alpha_track"]["samples"]
    records = trajectory_segment_classifications(
        samples,
        **{**PARAMETERS, "allow_observation_gap": False},
    )
    assert records[-1]["classification"] == "unverifiable"
    assert records[-1]["classification_reason"] == (
        "duration_exceeds_maximum_gap_but_gap_marking_is_disallowed"
    )
    assert "observation_gap" not in [record["classification"] for record in records]


def test_boundary_values_are_explicit_and_deterministic() -> None:
    from geotask_core.ops import trajectory_segment_classifications

    samples = _document()["objects"]["uav_alpha_track"]["samples"][:2]
    records = trajectory_segment_classifications(samples, **PARAMETERS)
    assert records[0]["distance_in_horizontal_unit"] == PARAMETERS[
        "stationary_radius_in_horizontal_unit"
    ]
    assert records[0]["duration_seconds"] == PARAMETERS[
        "minimum_stationary_duration_seconds"
    ]
    assert records[0]["classification"] == "stationary_candidate"


def test_document_validation_requires_exact_finite_parameters() -> None:
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.validator import validate_canonical

    payload = _document()
    del payload["tasks"][0]["assertions"][0]["parameters"][
        "stationary_radius_in_horizontal_unit"
    ]
    diagnostics = validate_canonical(canonicalize(payload))
    assert any(item["code"] == "missing_field" for item in diagnostics)

    payload = _document()
    payload["tasks"][0]["assertions"][0]["parameters"]["invented_threshold"] = 1
    diagnostics = validate_canonical(canonicalize(payload))
    assert any(item["code"] == "unknown_field" for item in diagnostics)

    invalid_values = (
        ("stationary_radius_in_horizontal_unit", -1),
        ("minimum_stationary_duration_seconds", 0),
        ("maximum_observation_gap_seconds", float("nan")),
        ("allow_observation_gap", "true"),
    )
    for name, value in invalid_values:
        payload = _document()
        payload["tasks"][0]["assertions"][0]["parameters"][name] = value
        diagnostics = validate_canonical(canonicalize(payload))
        assert any(
            item["code"] == "invalid_type" and name in item["path"]
            for item in diagnostics
        )


def test_direct_operator_rejects_invalid_thresholds() -> None:
    from geotask_core.ops import trajectory_segment_classifications

    samples = _document()["objects"]["uav_alpha_track"]["samples"]
    with pytest.raises(ValueError, match="non-negative"):
        trajectory_segment_classifications(
            samples,
            **{**PARAMETERS, "stationary_radius_in_horizontal_unit": -1},
        )
    with pytest.raises(ValueError, match="positive"):
        trajectory_segment_classifications(
            samples,
            **{**PARAMETERS, "maximum_observation_gap_seconds": 0},
        )
    with pytest.raises(ValueError, match="boolean"):
        trajectory_segment_classifications(
            samples,
            **{**PARAMETERS, "allow_observation_gap": 1},
        )


def test_classification_requires_planar_space_contract() -> None:
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.validator import validate_canonical

    payload = _document()
    payload["space"]["crs"] = {"type": "geographic", "identifier": "EPSG:4326"}
    diagnostics = validate_canonical(canonicalize(payload))
    assert any(item["code"] == "invalid_crs" for item in diagnostics)


def test_classification_does_not_infer_loss_of_link_anomaly_or_action() -> None:
    from geotask_core.ops import trajectory_segment_classifications

    records = trajectory_segment_classifications(
        _document()["objects"]["uav_alpha_track"]["samples"],
        **PARAMETERS,
    )
    serialized_keys = {key for record in records for key in record}
    for forbidden in (
        "lost_link",
        "anomaly",
        "interpolated_coordinates",
        "predicted_position",
        "map_matched_path",
        "action_authorized",
        "action_executed",
    ):
        assert forbidden not in serialized_keys


def test_public_api_and_registry_expose_classification_contract() -> None:
    import geotask_core
    from geotask_core.operator_registry import get_operator_metadata, operator_names

    assert geotask_core.TrajectorySegmentClassification.__name__ == (
        "TrajectorySegmentClassification"
    )
    assert callable(geotask_core.trajectory_segment_classifications)
    assert "trajectory_segment_classifications" in operator_names()
    metadata = get_operator_metadata("trajectory_segment_classifications")
    assert metadata["supported_geometry"] == ["trajectory"]
    assert metadata["output_type"] == "list"
    assert metadata["semantics"]["classification_vocabulary"] == [
        "stationary_candidate",
        "moving_observed",
        "observation_gap",
        "unverifiable",
    ]
