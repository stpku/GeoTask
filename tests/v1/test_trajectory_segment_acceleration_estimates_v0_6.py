"""v0.6 trajectory acceleration and motion continuity contract tests."""

from __future__ import annotations

import copy

import pytest


PARAMETERS = {
    "representative_time_method": "segment_midpoint",
    "maximum_observation_gap_seconds": 300,
}


def _document() -> dict:
    return {
        "geotask": {
            "id": "gt36-trajectory-acceleration",
            "name": "GT36 Trajectory Acceleration",
            "description": "Estimate scalar acceleration between adjacent segment-average speeds.",
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
                        "coordinates": [36, 48],
                    },
                    {
                        "observed_at": "2026-08-05T08:05:00+08:00",
                        "coordinates": [36, 138],
                    },
                    {
                        "observed_at": "2026-08-05T08:07:00+08:00",
                        "coordinates": [156, 138],
                    },
                    {
                        "observed_at": "2026-08-05T08:17:00+08:00",
                        "coordinates": [156, 138],
                    },
                ],
            },
        },
        "operator_set": ["trajectory_segment_acceleration_estimates"],
        "tasks": [
            {
                "id": "estimate_trajectory_acceleration",
                "family": "trajectory_acceleration",
                "goal": "Estimate scalar acceleration only across continuity-eligible adjacent segments.",
                "assertions": [
                    {
                        "id": "trajectory_acceleration_estimates",
                        "operator": "trajectory_segment_acceleration_estimates",
                        "object_refs": ["uav_alpha_track"],
                        "parameters": copy.deepcopy(PARAMETERS),
                        "expected_type": "array",
                    }
                ],
                "outputs": ["trajectory_acceleration_estimates"],
            }
        ],
        "execution": {
            "mode": "local_only",
            "steps": [
                {
                    "id": "estimate_acceleration",
                    "executor": "local",
                    "assertion_refs": ["trajectory_acceleration_estimates"],
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
            "required_fields": ["trajectory_acceleration_estimates"],
            "allow_additional_fields": False,
            "allow_model_inference": False,
        },
    }


def test_acceleration_estimates_bind_midpoints_and_fail_closed_on_gap() -> None:
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
    records = result.outputs["trajectory_acceleration_estimates"]
    assert len(records) == 3
    assert [record["continuity_state"] for record in records] == [
        "continuous_observation",
        "continuous_observation",
        "unverifiable",
    ]
    assert [record["shared_sample_index"] for record in records] == [1, 2, 3]
    assert [record["prior_representative_at"] for record in records] == [
        "2026-08-05T08:01:00+08:00",
        "2026-08-05T08:03:30+08:00",
        "2026-08-05T08:06:00+08:00",
    ]
    assert [record["next_representative_at"] for record in records] == [
        "2026-08-05T08:03:30+08:00",
        "2026-08-05T08:06:00+08:00",
        "2026-08-05T08:12:00+08:00",
    ]
    assert [record["representative_interval_seconds"] for record in records] == [
        150.0,
        150.0,
        360.0,
    ]
    assert records[0]["speed_change_in_horizontal_units_per_second"] == 0.0
    assert records[0]["acceleration_in_horizontal_units_per_second_squared"] == 0.0
    assert records[1]["speed_change_in_horizontal_units_per_second"] == 0.5
    assert records[1]["acceleration_in_horizontal_units_per_second_squared"] == pytest.approx(
        1.0 / 300.0
    )
    assert records[2]["speed_change_in_horizontal_units_per_second"] is None
    assert records[2]["acceleration_in_horizontal_units_per_second_squared"] is None
    assert records[2]["continuity_reason"] == (
        "next_segment_exceeds_declared_maximum_gap"
    )


def test_gap_boundary_is_inclusive_for_continuity() -> None:
    from geotask_core.ops import trajectory_segment_acceleration_estimates

    samples = _document()["objects"]["uav_alpha_track"]["samples"]
    records = trajectory_segment_acceleration_estimates(
        samples,
        representative_time_method="segment_midpoint",
        maximum_observation_gap_seconds=600,
    )
    assert records[-1]["continuity_state"] == "continuous_observation"
    assert records[-1]["speed_change_in_horizontal_units_per_second"] == -1.0
    assert records[-1]["acceleration_in_horizontal_units_per_second_squared"] == pytest.approx(
        -1.0 / 360.0
    )


def test_document_validation_requires_exact_acceleration_parameters() -> None:
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.validator import validate_canonical

    payload = _document()
    del payload["tasks"][0]["assertions"][0]["parameters"][
        "representative_time_method"
    ]
    diagnostics = validate_canonical(canonicalize(payload))
    assert any(item["code"] == "missing_field" for item in diagnostics)

    payload = _document()
    payload["tasks"][0]["assertions"][0]["parameters"]["invented_method"] = "x"
    diagnostics = validate_canonical(canonicalize(payload))
    assert any(item["code"] == "unknown_field" for item in diagnostics)

    invalid_values = (
        ("representative_time_method", "sample_boundary"),
        ("maximum_observation_gap_seconds", 0),
        ("maximum_observation_gap_seconds", float("nan")),
        ("maximum_observation_gap_seconds", True),
    )
    for name, value in invalid_values:
        payload = _document()
        payload["tasks"][0]["assertions"][0]["parameters"][name] = value
        diagnostics = validate_canonical(canonicalize(payload))
        assert any(
            item["code"] == "invalid_type" and name in item["path"]
            for item in diagnostics
        )


def test_direct_operator_rejects_implicit_or_invalid_parameters() -> None:
    from geotask_core.ops import trajectory_segment_acceleration_estimates

    samples = _document()["objects"]["uav_alpha_track"]["samples"]
    with pytest.raises(ValueError, match="segment_midpoint"):
        trajectory_segment_acceleration_estimates(
            samples,
            representative_time_method="sample_boundary",
            maximum_observation_gap_seconds=300,
        )
    with pytest.raises(ValueError, match="positive"):
        trajectory_segment_acceleration_estimates(
            samples,
            representative_time_method="segment_midpoint",
            maximum_observation_gap_seconds=0,
        )
    with pytest.raises(ValueError, match="finite number"):
        trajectory_segment_acceleration_estimates(
            samples,
            representative_time_method="segment_midpoint",
            maximum_observation_gap_seconds=True,
        )


def test_acceleration_requires_planar_space_contract() -> None:
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.validator import validate_canonical

    payload = _document()
    payload["space"]["crs"] = {"type": "geographic", "identifier": "EPSG:4326"}
    diagnostics = validate_canonical(canonicalize(payload))
    assert any(item["code"] == "invalid_crs" for item in diagnostics)


def test_acceleration_does_not_overclaim_instantaneous_vector_or_action_state() -> None:
    from geotask_core.ops import trajectory_segment_acceleration_estimates

    records = trajectory_segment_acceleration_estimates(
        _document()["objects"]["uav_alpha_track"]["samples"],
        **PARAMETERS,
    )
    serialized_keys = {key for record in records for key in record}
    for forbidden in (
        "instantaneous_acceleration",
        "acceleration_vector",
        "heading_change",
        "lost_link",
        "anomaly",
        "interpolated_coordinates",
        "predicted_position",
        "map_matched_path",
        "action_authorized",
        "action_executed",
    ):
        assert forbidden not in serialized_keys


def test_public_api_and_registry_expose_acceleration_contract() -> None:
    import geotask_core
    from geotask_core.operator_registry import get_operator_metadata, operator_names

    assert geotask_core.TrajectorySegmentAccelerationEstimate.__name__ == (
        "TrajectorySegmentAccelerationEstimate"
    )
    assert callable(geotask_core.trajectory_segment_acceleration_estimates)
    assert "trajectory_segment_acceleration_estimates" in operator_names()
    metadata = get_operator_metadata("trajectory_segment_acceleration_estimates")
    assert metadata["supported_geometry"] == ["trajectory"]
    assert metadata["output_type"] == "list"
    assert metadata["semantics"]["representative_time_method"] == "segment_midpoint"
    assert metadata["semantics"]["continuity_vocabulary"] == [
        "continuous_observation",
        "unverifiable",
    ]
