"""Fixed fictional cases for the public GeoTask Core benchmark.

The cases exercise production Core APIs only. They contain no customer data,
external evidence, network access, model calls, or benchmark-local verifier.
"""

from __future__ import annotations

import json
from typing import Any


def _base_document(
    *,
    document_id: str,
    name: str,
    objects: dict[str, Any],
    operators: list[str],
    assertions: list[dict[str, Any]],
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "metadata": {
            "id": document_id,
            "name": name,
            "schema_version": "1.0",
            "language": "en",
            "domain": "general_spatial",
        },
        "space": {
            "crs": {
                "type": "local_cartesian",
                "identifier": "fictional_benchmark_grid_m",
            },
            "horizontal_unit": "meter",
            "vertical_unit": "meter",
            "coordinate_order": ["x", "y"],
            "boundary_semantics": "closed",
        },
        "objects": objects,
        "operator_set": operators,
        "tasks": [
            {
                "id": f"{document_id}.task",
                "family": "public_core_benchmark",
                "goal": "Exercise deterministic GeoTask Core contracts.",
                "assertions": assertions,
                "outputs": [item["id"] for item in assertions],
            }
        ],
        "execution": {"mode": "local_only", "steps": []},
        "verification": {
            "mode": "local_deterministic",
            "required_assurance": "local_deterministic",
        },
        "output_contract": {
            "format": "structured",
            "required_fields": [item["id"] for item in assertions],
            "allow_additional_fields": False,
            "allow_model_inference": False,
        },
    }
    if provenance is not None:
        payload["provenance"] = provenance
    return payload


def _case(
    case_id: str,
    payload: dict[str, Any],
    *,
    expected_outputs: dict[str, Any],
    expected_evidence_refs: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "payload_json": json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ),
        "operators": tuple(payload["operator_set"]),
        "expected_outputs": expected_outputs,
        "expected_evidence_refs": expected_evidence_refs or {},
    }


CORE_BENCHMARK_CASES: tuple[dict[str, Any], ...] = (
    _case(
        "distance_2d",
        _base_document(
            document_id="benchmark.distance",
            name="Distance benchmark",
            objects={
                "point_a": {"type": "point", "data": {"coordinates": [0, 0]}},
                "point_b": {"type": "point", "data": {"coordinates": [3, 4]}},
            },
            operators=["distance_2d"],
            assertions=[
                {
                    "id": "distance_value",
                    "operator": "distance_2d",
                    "object_refs": ["point_a", "point_b"],
                    "expected_type": "number",
                    "unit": "meter",
                }
            ],
        ),
        expected_outputs={"distance_value": 5.0},
    ),
    _case(
        "planar_topology",
        _base_document(
            document_id="benchmark.planar-topology",
            name="Planar topology benchmark",
            objects={
                "query_point": {
                    "type": "point",
                    "data": {"coordinates": [1, 2]},
                },
                "route": {
                    "type": "polyline",
                    "data": {"coordinates": [[0, 0], [4, 0]]},
                },
                "work_rect": {
                    "type": "rect",
                    "data": {"bbox": [0, 0, 4, 4]},
                },
            },
            operators=[
                "point_to_line_distance_2d",
                "line_intersects_rect",
                "rect_contains_point",
            ],
            assertions=[
                {
                    "id": "point_line_distance",
                    "operator": "point_to_line_distance_2d",
                    "object_refs": ["query_point", "route"],
                    "expected_type": "number",
                    "unit": "meter",
                },
                {
                    "id": "route_intersects",
                    "operator": "line_intersects_rect",
                    "object_refs": ["route", "work_rect"],
                    "expected_type": "boolean",
                },
                {
                    "id": "point_contained",
                    "operator": "rect_contains_point",
                    "object_refs": ["work_rect", "query_point"],
                    "expected_type": "boolean",
                },
            ],
        ),
        expected_outputs={
            "point_line_distance": 2.0,
            "route_intersects": True,
            "point_contained": True,
        },
    ),
    _case(
        "polygon_multi_polyline",
        _base_document(
            document_id="benchmark.polygon-multi",
            name="Polygon and grouped-route benchmark",
            objects={
                "query_point": {
                    "type": "point",
                    "data": {"coordinates": [2, 2]},
                },
                "service_polygon": {
                    "type": "polygon",
                    "data": {
                        "coordinates": [[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]]
                    },
                },
                "grouped_routes": {
                    "type": "multi_polyline",
                    "data": {
                        "coordinates": [
                            [[-4, -4], [-3, -3]],
                            [[-1, 2], [5, 2]],
                        ]
                    },
                },
                "service_rect": {
                    "type": "rect",
                    "data": {"bbox": [0, 0, 4, 4]},
                },
            },
            operators=[
                "point_in_polygon",
                "polygon_contains_point",
                "multi_polyline_intersects_rect",
            ],
            assertions=[
                {
                    "id": "point_in_service_polygon",
                    "operator": "point_in_polygon",
                    "object_refs": ["query_point", "service_polygon"],
                    "expected_type": "boolean",
                },
                {
                    "id": "service_polygon_contains_point",
                    "operator": "polygon_contains_point",
                    "object_refs": ["service_polygon", "query_point"],
                    "expected_type": "boolean",
                },
                {
                    "id": "grouped_route_intersects",
                    "operator": "multi_polyline_intersects_rect",
                    "object_refs": ["grouped_routes", "service_rect"],
                    "expected_type": "boolean",
                },
            ],
        ),
        expected_outputs={
            "point_in_service_polygon": True,
            "service_polygon_contains_point": True,
            "grouped_route_intersects": True,
        },
    ),
    _case(
        "time_altitude",
        _base_document(
            document_id="benchmark.time-altitude",
            name="Time and altitude benchmark",
            objects={
                "window_a": {
                    "type": "time_interval",
                    "data": {"start": "08:00", "end": "10:00"},
                },
                "window_b": {
                    "type": "time_interval",
                    "data": {"start": "09:30", "end": "11:00"},
                },
                "altitude_a": {
                    "type": "altitude_interval",
                    "data": {
                        "min": 100,
                        "max": 200,
                        "unit": "meter",
                        "datum": "fictional_local_datum",
                    },
                },
                "altitude_b": {
                    "type": "altitude_interval",
                    "data": {
                        "min": 200,
                        "max": 260,
                        "unit": "meter",
                        "datum": "fictional_local_datum",
                    },
                },
            },
            operators=["time_overlap", "altitude_overlap"],
            assertions=[
                {
                    "id": "time_conflict",
                    "operator": "time_overlap",
                    "object_refs": ["window_a", "window_b"],
                    "expected_type": "boolean",
                },
                {
                    "id": "altitude_conflict",
                    "operator": "altitude_overlap",
                    "object_refs": ["altitude_a", "altitude_b"],
                    "expected_type": "boolean",
                },
            ],
        ),
        expected_outputs={"time_conflict": True, "altitude_conflict": True},
    ),
    _case(
        "provenance_evidence",
        _base_document(
            document_id="benchmark.provenance",
            name="Provenance benchmark",
            objects={
                "source_point": {
                    "type": "point",
                    "data": {"coordinates": [0, 0]},
                },
                "target_point": {
                    "type": "point",
                    "data": {"coordinates": [6, 8]},
                },
            },
            operators=["distance_2d"],
            assertions=[
                {
                    "id": "evidenced_distance",
                    "operator": "distance_2d",
                    "object_refs": ["source_point", "target_point"],
                    "expected_type": "number",
                    "unit": "meter",
                }
            ],
            provenance={
                "sources": [
                    {
                        "id": "fictional_dataset",
                        "kind": "dataset",
                        "title": "Fictional benchmark coordinates",
                        "uri": "urn:geotask:benchmark:fictional-dataset:0.1",
                        "version": "0.1",
                        "sha256": "3333333333333333333333333333333333333333333333333333333333333333",
                        "issued_at": "2026-08-01T00:00:00+00:00",
                        "retrieved_at": "2026-08-01T00:01:00+00:00",
                        "verified_at": "2026-08-01T00:02:00+00:00",
                    }
                ],
                "evidence_bindings": [
                    {
                        "assertion_id": "evidenced_distance",
                        "source_refs": ["fictional_dataset"],
                    }
                ],
                "audit": {
                    "generated_by": "geotask-public-core-benchmark",
                    "generator_version": "0.1",
                    "generated_at": "2026-08-01T00:03:00+00:00",
                    "audit_ref": "audit:geotask:public-core-benchmark:0.1",
                    "source_refs": ["fictional_dataset"],
                },
            },
        ),
        expected_outputs={"evidenced_distance": 10.0},
        expected_evidence_refs={"evidenced_distance": ["fictional_dataset"]},
    ),
    _case(
        "trajectory_duration",
        _base_document(
            document_id="benchmark.trajectory-duration",
            name="Discrete trajectory duration benchmark",
            objects={
                "moving_asset": {
                    "type": "moving_object",
                    "data": {
                        "object_class": "uav",
                        "identity": "fictional-benchmark-uav",
                    },
                },
                "asset_track": {
                    "type": "trajectory",
                    "data": {
                        "subject_ref": "moving_asset",
                        "interpolation": "none",
                        "samples": [
                            {
                                "observed_at": "2026-08-05T08:00:00+08:00",
                                "coordinates": [0, 0],
                            },
                            {
                                "observed_at": "2026-08-05T08:05:00+08:00",
                                "coordinates": [30, 40],
                            },
                        ],
                    },
                },
            },
            operators=["trajectory_duration_seconds"],
            assertions=[
                {
                    "id": "trajectory_duration",
                    "operator": "trajectory_duration_seconds",
                    "object_refs": ["asset_track"],
                    "expected_type": "number",
                    "unit": "second",
                }
            ],
        ),
        expected_outputs={"trajectory_duration": 300.0},
    ),
    _case(
        "trajectory_segments",
        _base_document(
            document_id="benchmark.trajectory-segments",
            name="Discrete trajectory segment benchmark",
            objects={
                "moving_asset": {
                    "type": "moving_object",
                    "data": {
                        "object_class": "uav",
                        "identity": "fictional-benchmark-segment-uav",
                    },
                },
                "asset_track": {
                    "type": "trajectory",
                    "data": {
                        "subject_ref": "moving_asset",
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
            },
            operators=["trajectory_segment_metrics"],
            assertions=[
                {
                    "id": "trajectory_segments",
                    "operator": "trajectory_segment_metrics",
                    "object_refs": ["asset_track"],
                    "expected_type": "array",
                }
            ],
        ),
        expected_outputs={
            "trajectory_segments": [
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
        },
    ),
    _case(
        "trajectory_classifications",
        _base_document(
            document_id="benchmark.trajectory-classifications",
            name="Trajectory stop move and observation gap benchmark",
            objects={
                "moving_asset": {
                    "type": "moving_object",
                    "data": {
                        "object_class": "uav",
                        "identity": "fictional-benchmark-classification-uav",
                    },
                },
                "asset_track": {
                    "type": "trajectory",
                    "data": {
                        "subject_ref": "moving_asset",
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
            },
            operators=["trajectory_segment_classifications"],
            assertions=[
                {
                    "id": "trajectory_segment_states",
                    "operator": "trajectory_segment_classifications",
                    "object_refs": ["asset_track"],
                    "parameters": {
                        "stationary_radius_in_horizontal_unit": 5,
                        "minimum_stationary_duration_seconds": 120,
                        "maximum_observation_gap_seconds": 300,
                        "allow_observation_gap": True,
                    },
                    "expected_type": "array",
                }
            ],
        ),
        expected_outputs={
            "trajectory_segment_states": [
                {
                    "segment_index": 0,
                    "start_sample_index": 0,
                    "end_sample_index": 1,
                    "start_observed_at": "2026-08-05T08:00:00+08:00",
                    "end_observed_at": "2026-08-05T08:02:00+08:00",
                    "start_coordinates": [0, 0],
                    "end_coordinates": [3, 4],
                    "duration_seconds": 120.0,
                    "distance_in_horizontal_unit": 5.0,
                    "average_speed_in_horizontal_units_per_second": 5.0 / 120.0,
                    "classification": "stationary_candidate",
                    "classification_reason": "within_declared_radius_and_meets_declared_minimum_duration",
                    "stationary_radius_in_horizontal_unit": 5.0,
                    "minimum_stationary_duration_seconds": 120.0,
                    "maximum_observation_gap_seconds": 300.0,
                    "allow_observation_gap": True,
                },
                {
                    "segment_index": 1,
                    "start_sample_index": 1,
                    "end_sample_index": 2,
                    "start_observed_at": "2026-08-05T08:02:00+08:00",
                    "end_observed_at": "2026-08-05T08:04:00+08:00",
                    "start_coordinates": [3, 4],
                    "end_coordinates": [13, 4],
                    "duration_seconds": 120.0,
                    "distance_in_horizontal_unit": 10.0,
                    "average_speed_in_horizontal_units_per_second": 10.0 / 120.0,
                    "classification": "moving_observed",
                    "classification_reason": "does_not_meet_declared_stationary_candidate_conditions",
                    "stationary_radius_in_horizontal_unit": 5.0,
                    "minimum_stationary_duration_seconds": 120.0,
                    "maximum_observation_gap_seconds": 300.0,
                    "allow_observation_gap": True,
                },
                {
                    "segment_index": 2,
                    "start_sample_index": 2,
                    "end_sample_index": 3,
                    "start_observed_at": "2026-08-05T08:04:00+08:00",
                    "end_observed_at": "2026-08-05T08:14:00+08:00",
                    "start_coordinates": [13, 4],
                    "end_coordinates": [13, 4],
                    "duration_seconds": 600.0,
                    "distance_in_horizontal_unit": 0.0,
                    "average_speed_in_horizontal_units_per_second": 0.0,
                    "classification": "observation_gap",
                    "classification_reason": "duration_exceeds_declared_maximum_gap",
                    "stationary_radius_in_horizontal_unit": 5.0,
                    "minimum_stationary_duration_seconds": 120.0,
                    "maximum_observation_gap_seconds": 300.0,
                    "allow_observation_gap": True,
                },
            ]
        },
    ),
    _case(
        "trajectory_acceleration",
        _base_document(
            document_id="benchmark.trajectory-acceleration",
            name="Trajectory acceleration and continuity benchmark",
            objects={
                "moving_asset": {
                    "type": "moving_object",
                    "data": {
                        "object_class": "uav",
                        "identity": "fictional-benchmark-acceleration-uav",
                    },
                },
                "asset_track": {
                    "type": "trajectory",
                    "data": {
                        "subject_ref": "moving_asset",
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
                        ],
                    },
                },
            },
            operators=["trajectory_segment_acceleration_estimates"],
            assertions=[
                {
                    "id": "trajectory_acceleration_estimates",
                    "operator": "trajectory_segment_acceleration_estimates",
                    "object_refs": ["asset_track"],
                    "parameters": {
                        "representative_time_method": "segment_midpoint",
                        "maximum_observation_gap_seconds": 300,
                    },
                    "expected_type": "array",
                }
            ],
        ),
        expected_outputs={
            "trajectory_acceleration_estimates": [
                {
                    "transition_index": 0,
                    "prior_segment_index": 0,
                    "next_segment_index": 1,
                    "shared_sample_index": 1,
                    "prior_start_sample_index": 0,
                    "prior_end_sample_index": 1,
                    "next_start_sample_index": 1,
                    "next_end_sample_index": 2,
                    "prior_start_observed_at": "2026-08-05T08:00:00+08:00",
                    "shared_observed_at": "2026-08-05T08:02:00+08:00",
                    "next_end_observed_at": "2026-08-05T08:05:00+08:00",
                    "prior_start_coordinates": [0, 0],
                    "shared_coordinates": [36, 48],
                    "next_end_coordinates": [36, 138],
                    "prior_duration_seconds": 120.0,
                    "next_duration_seconds": 180.0,
                    "prior_average_speed_in_horizontal_units_per_second": 0.5,
                    "next_average_speed_in_horizontal_units_per_second": 0.5,
                    "prior_representative_at": "2026-08-05T08:01:00+08:00",
                    "next_representative_at": "2026-08-05T08:03:30+08:00",
                    "representative_interval_seconds": 150.0,
                    "speed_change_in_horizontal_units_per_second": 0.0,
                    "acceleration_in_horizontal_units_per_second_squared": 0.0,
                    "continuity_state": "continuous_observation",
                    "continuity_reason": "both_segments_within_declared_maximum_gap",
                    "representative_time_method": "segment_midpoint",
                    "maximum_observation_gap_seconds": 300.0,
                },
                {
                    "transition_index": 1,
                    "prior_segment_index": 1,
                    "next_segment_index": 2,
                    "shared_sample_index": 2,
                    "prior_start_sample_index": 1,
                    "prior_end_sample_index": 2,
                    "next_start_sample_index": 2,
                    "next_end_sample_index": 3,
                    "prior_start_observed_at": "2026-08-05T08:02:00+08:00",
                    "shared_observed_at": "2026-08-05T08:05:00+08:00",
                    "next_end_observed_at": "2026-08-05T08:07:00+08:00",
                    "prior_start_coordinates": [36, 48],
                    "shared_coordinates": [36, 138],
                    "next_end_coordinates": [156, 138],
                    "prior_duration_seconds": 180.0,
                    "next_duration_seconds": 120.0,
                    "prior_average_speed_in_horizontal_units_per_second": 0.5,
                    "next_average_speed_in_horizontal_units_per_second": 1.0,
                    "prior_representative_at": "2026-08-05T08:03:30+08:00",
                    "next_representative_at": "2026-08-05T08:06:00+08:00",
                    "representative_interval_seconds": 150.0,
                    "speed_change_in_horizontal_units_per_second": 0.5,
                    "acceleration_in_horizontal_units_per_second_squared": 1.0 / 300.0,
                    "continuity_state": "continuous_observation",
                    "continuity_reason": "both_segments_within_declared_maximum_gap",
                    "representative_time_method": "segment_midpoint",
                    "maximum_observation_gap_seconds": 300.0,
                },
            ]
        },
    ),
    _case(
        "trajectory_identity",
        _base_document(
            document_id="benchmark.trajectory-identity",
            name="Trajectory identity candidate benchmark",
            objects={
                "provisional_a": {
                    "type": "moving_object",
                    "data": {
                        "object_class": "uav",
                        "identity": "fictional-benchmark-provisional-a",
                    },
                },
                "provisional_b": {
                    "type": "moving_object",
                    "data": {
                        "object_class": "uav",
                        "identity": "fictional-benchmark-provisional-b",
                    },
                },
                "track_a": {
                    "type": "trajectory",
                    "data": {
                        "subject_ref": "provisional_a",
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
                },
                "track_b": {
                    "type": "trajectory",
                    "data": {
                        "subject_ref": "provisional_b",
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
            },
            operators=["trajectory_identity_candidate"],
            assertions=[
                {
                    "id": "identity_candidate",
                    "operator": "trajectory_identity_candidate",
                    "object_refs": ["track_a", "track_b"],
                    "parameters": {
                        "maximum_identity_gap_seconds": 120,
                        "maximum_identity_distance_in_horizontal_unit": 10,
                        "require_same_object_class": True,
                    },
                    "expected_type": "object",
                }
            ],
        ),
        expected_outputs={
            "identity_candidate": {
                "candidate_state": "same_object_candidate",
                "candidate_reason": "boundary_samples_within_declared_time_and_distance_limits",
                "first_trajectory_ref": "track_a",
                "second_trajectory_ref": "track_b",
                "first_subject_ref": "provisional_a",
                "second_subject_ref": "provisional_b",
                "first_object_class": "uav",
                "second_object_class": "uav",
                "first_boundary_sample_index": 1,
                "second_boundary_sample_index": 0,
                "first_boundary_observed_at": "2026-08-05T08:02:00+08:00",
                "second_boundary_observed_at": "2026-08-05T08:03:00+08:00",
                "first_boundary_coordinates": [36, 48],
                "second_boundary_coordinates": [39, 52],
                "temporal_gap_seconds": 60.0,
                "spatial_distance_in_horizontal_unit": 5.0,
                "maximum_identity_gap_seconds": 120.0,
                "maximum_identity_distance_in_horizontal_unit": 10.0,
                "require_same_object_class": True,
                "evidence_basis": "first_trajectory_final_sample_to_second_trajectory_first_sample",
                "identity_merge_performed": False,
                "subject_refs_mutated": False,
            }
        },
    ),
)


CORE_BENCHMARK_OPERATOR_COVERAGE: tuple[str, ...] = tuple(
    sorted(
        {
            operator
            for case in CORE_BENCHMARK_CASES
            for operator in case["operators"]
        }
    )
)


__all__ = ["CORE_BENCHMARK_CASES", "CORE_BENCHMARK_OPERATOR_COVERAGE"]
