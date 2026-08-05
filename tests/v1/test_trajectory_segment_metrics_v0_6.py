"""v0.6 discrete trajectory segment metric contract tests."""

from __future__ import annotations

import copy

import pytest


def _document() -> dict:
    return {
        "geotask": {
            "id": "gt34-trajectory-segments",
            "name": "GT34 Trajectory Segment Metrics",
            "description": "Compute explicit adjacent-sample metrics for one fictional trajectory.",
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
                ],
            },
        },
        "operator_set": ["trajectory_segment_metrics"],
        "tasks": [
            {
                "id": "measure_trajectory_segments",
                "family": "trajectory_measurement",
                "goal": "Compute metrics for every adjacent explicit sample pair.",
                "assertions": [
                    {
                        "id": "trajectory_segments",
                        "operator": "trajectory_segment_metrics",
                        "object_refs": ["uav_alpha_track"],
                        "expected_type": "array",
                    }
                ],
                "outputs": ["trajectory_segments"],
            }
        ],
        "execution": {
            "mode": "local_only",
            "steps": [
                {
                    "id": "measure_segments",
                    "executor": "local",
                    "assertion_refs": ["trajectory_segments"],
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
            "required_fields": ["trajectory_segments"],
            "allow_additional_fields": False,
            "allow_model_inference": False,
        },
    }


def test_segment_metrics_bind_adjacent_samples_and_units() -> None:
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
    assert result.checks[0].operator == "trajectory_segment_metrics"
    assert result.checks[0].unit == ""
    assert result.outputs["trajectory_segments"] == [
        {
            "segment_index": 0,
            "start_sample_index": 0,
            "end_sample_index": 1,
            "start_observed_at": "2026-08-05T08:00:00+08:00",
            "end_observed_at": "2026-08-05T08:02:00+08:00",
            "start_coordinates": [0, 0],
            "end_coordinates": [36, 48],
            "duration_seconds": 120.0,
            "distance_in_horizontal_unit": 60.0,
            "average_speed_in_horizontal_units_per_second": 0.5,
        },
        {
            "segment_index": 1,
            "start_sample_index": 1,
            "end_sample_index": 2,
            "start_observed_at": "2026-08-05T08:02:00+08:00",
            "end_observed_at": "2026-08-05T08:05:00+08:00",
            "start_coordinates": [36, 48],
            "end_coordinates": [36, 138],
            "duration_seconds": 180.0,
            "distance_in_horizontal_unit": 90.0,
            "average_speed_in_horizontal_units_per_second": 0.5,
        },
    ]


def test_segment_metrics_reject_static_polyline_substitution() -> None:
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.validator import validate_canonical

    canonical = canonicalize(_document())
    canonical.objects["uav_alpha_track"].type = "polyline"
    canonical.objects["uav_alpha_track"].data = {
        "coordinates": [[0, 0], [36, 48], [36, 138]]
    }
    diagnostics = validate_canonical(canonical)
    assert any(
        item["code"] == "object_type_mismatch"
        and "expects type 'trajectory'" in item["message"]
        for item in diagnostics
    )


def test_segment_metrics_fail_closed_on_non_increasing_time() -> None:
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.validator import validate_canonical

    payload = _document()
    payload["objects"]["uav_alpha_track"]["samples"][1]["observed_at"] = (
        "2026-08-05T08:00:00+08:00"
    )
    diagnostics = validate_canonical(canonicalize(payload))
    assert any(
        item["code"] == "invalid_interval"
        and "strictly increasing" in item["message"]
        for item in diagnostics
    )

    from geotask_core.ops import trajectory_segment_metrics

    with pytest.raises(ValueError, match="strictly increasing"):
        trajectory_segment_metrics(
            [
                {
                    "observed_at": "2026-08-05T08:00:00+08:00",
                    "coordinates": [0, 0],
                },
                {
                    "observed_at": "2026-08-05T08:00:00+08:00",
                    "coordinates": [1, 1],
                },
            ]
        )


def test_segment_metrics_do_not_overclaim_units_or_inferred_state() -> None:
    from geotask_core.ops import trajectory_segment_metrics

    segments = trajectory_segment_metrics(
        _document()["objects"]["uav_alpha_track"]["samples"]
    )
    serialized_keys = {key for segment in segments for key in segment}
    assert "distance_meters" not in serialized_keys
    assert "speed_meters_per_second" not in serialized_keys
    assert "interpolated_coordinates" not in serialized_keys
    assert "predicted_position" not in serialized_keys
    assert "map_matched_path" not in serialized_keys
    assert "action_authorized" not in serialized_keys


def test_public_api_exposes_segment_contract() -> None:
    import geotask_core
    from geotask_core.operator_registry import get_operator_metadata, operator_names

    assert geotask_core.TrajectorySegment.__name__ == "TrajectorySegment"
    assert callable(geotask_core.trajectory_segment_metrics)
    assert "trajectory_segment_metrics" in operator_names()
    metadata = get_operator_metadata("trajectory_segment_metrics")
    assert metadata["supported_geometry"] == ["trajectory"]
    assert metadata["output_type"] == "list"
    assert metadata["semantics"]["speed_unit"] == "horizontal_unit_per_second"
    assert metadata["semantics"]["interpolation"] == "none"
