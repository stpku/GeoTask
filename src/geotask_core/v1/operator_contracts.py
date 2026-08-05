"""GeoTask Core v1.0 — Structured operator contracts with implementation binding.

This module defines all current Core operators as v1.0 OperatorContracts
and provides an OperatorRegistry for lookup plus an AssertionDispatcher
that replaces the v0.x runner.py type-based auto-detection with
assertion-driven execution.
"""

from __future__ import annotations

import importlib
import math
from typing import Any, Callable

from geotask_core.v1.ir import Assertion, GeoObject, OperatorContract


# -- v1.0 Operator Contracts

DISTANCE_2D = OperatorContract(
    name="distance_2d",
    version="1.0",
    family="measurement",
    description="Euclidean distance between two planar points.",
    arity=2,
    input_types=["point", "point"],
    output={
        "type": "number",
        "unit_behavior": "inherit_horizontal_unit",
    },
    deterministic=True,
    semantics={
        "formula": "sqrt((x2-x1)^2 + (y2-y1)^2)",
        "boundary_rules": [
            "Distance is non-negative.",
            "Identical points produce zero.",
        ],
    },
    model_execution={
        "level": "M1",
        "supported": True,
        "recommended_max_items": 50,
        "precision_tolerance": 0.01,
    },
    invariants=[
        {"id": "non_negative", "expression": "result >= 0"},
        {"id": "symmetric", "expression": "distance(a,b) == distance(b,a)"},
    ],
    error_codes=[
        "invalid_coordinates",
        "arity_mismatch",
        "object_type_mismatch",
    ],
    examples=[
        {
            "inputs": {"a": [0, 0], "b": [3, 4]},
            "expected": 5.0,
        },
    ],
    implementation="geotask_core.ops.distance_2d",
)

LINE_INTERSECTS_RECT = OperatorContract(
    name="line_intersects_rect",
    version="1.0",
    family="topology",
    description=(
        "Check if any segment of a polyline intersects "
        "an axis-aligned rectangle."
    ),
    arity=2,
    input_types=["polyline", "rect"],
    output={"type": "boolean"},
    deterministic=True,
    semantics={
        "boundary_rules": [
            "Boundary contact counts as intersection.",
            "All consecutive point pairs are checked as segments.",
        ],
        "legacy_input_aliases": {
            "line": "polyline",
        },
    },
    model_execution={
        "level": "M1",
        "supported": True,
        "recommended_max_items": 20,
    },
    invariants=[
        {"id": "bool_output", "expression": "result in (True, False)"},
    ],
    error_codes=[
        "insufficient_points",
        "invalid_bbox",
        "object_type_mismatch",
    ],
    examples=[
        {
            "inputs": {
                "polyline": [[-200, 0], [400, 0]],
                "rect": [250, -100, 350, 100],
            },
            "expected": True,
        },
    ],
    implementation="geotask_core.ops.line_intersects_rect",
)

MULTI_POLYLINE_INTERSECTS_RECT = OperatorContract(
    name="multi_polyline_intersects_rect",
    version="1.0",
    family="topology",
    description=(
        "Check if any member of a multi-polyline intersects an axis-aligned "
        "rectangle."
    ),
    arity=2,
    input_types=["multi_polyline", "rect"],
    output={"type": "boolean"},
    deterministic=True,
    semantics={
        "boundary_rules": [
            "Boundary contact counts as intersection.",
            "Each member polyline is evaluated independently.",
        ],
    },
    model_execution={
        "level": "M1",
        "supported": True,
        "recommended_max_items": 20,
    },
    invariants=[
        {"id": "bool_output", "expression": "result in (True, False)"},
        {"id": "any_member", "expression": "result == any(member intersects rect)"},
    ],
    error_codes=[
        "invalid_geometry",
        "invalid_bbox",
        "object_type_mismatch",
    ],
    examples=[
        {
            "inputs": {
                "multi_polyline": [
                    [[-10, -10], [-5, -5]],
                    [[-2, 5], [12, 5]],
                ],
                "rect": [0, 0, 10, 10],
            },
            "expected": True,
        },
    ],
    implementation="geotask_core.ops.multi_polyline_intersects_rect",
)

POINT_IN_POLYGON = OperatorContract(
    name="point_in_polygon",
    version="1.0",
    family="topology",
    description="Check if a point is inside or on the boundary of a polygon.",
    arity=2,
    input_types=["point", "polygon"],
    output={"type": "boolean"},
    deterministic=True,
    semantics={
        "algorithm": "even_odd_rule",
        "boundary_rules": [
            "Boundary contact counts as containment.",
            "The polygon is one closed exterior ring without holes.",
        ],
    },
    model_execution={
        "level": "M1",
        "supported": True,
        "recommended_max_items": 50,
    },
    invariants=[
        {"id": "bool_output", "expression": "result in (True, False)"},
        {"id": "boundary_included", "expression": "point on ring => result == True"},
    ],
    error_codes=[
        "invalid_coordinates",
        "invalid_geometry",
        "object_type_mismatch",
    ],
    examples=[
        {
            "inputs": {
                "point": [5, 5],
                "polygon": [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
            },
            "expected": True,
        },
    ],
    implementation="geotask_core.ops.point_in_polygon",
)

POLYGON_CONTAINS_POINT = OperatorContract(
    name="polygon_contains_point",
    version="1.0",
    family="topology",
    description="Check if a polygon contains a point or touches it on the boundary.",
    arity=2,
    input_types=["polygon", "point"],
    output={"type": "boolean"},
    deterministic=True,
    semantics={
        "algorithm": "even_odd_rule",
        "equivalent_predicate": "point_in_polygon(point, polygon)",
        "argument_order": ["polygon", "point"],
        "boundary_rules": [
            "Boundary contact counts as containment.",
            "The polygon is one closed exterior ring without holes.",
        ],
        "coordinate_constraints": [
            "Polygon and point coordinates use the document SpaceDefinition.",
            "Both objects must use the same coordinate order and CRS.",
            "The boolean result is dimensionless and performs no unit conversion.",
        ],
    },
    model_execution={
        "level": "M1",
        "supported": True,
        "recommended_max_items": 50,
    },
    invariants=[
        {"id": "bool_output", "expression": "result in (True, False)"},
        {"id": "boundary_included", "expression": "point on ring => result == True"},
        {
            "id": "predicate_equivalence",
            "expression": "polygon_contains_point(p, q) == point_in_polygon(q, p)",
        },
    ],
    error_codes=[
        "invalid_coordinates",
        "invalid_geometry",
        "object_type_mismatch",
    ],
    examples=[
        {
            "inputs": {
                "polygon": [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
                "point": [5, 5],
            },
            "expected": True,
        },
    ],
    implementation="geotask_core.ops.polygon_contains_point",
)

POINT_TO_LINE_DISTANCE_2D = OperatorContract(
    name="point_to_line_distance_2d",
    version="1.0",
    family="measurement",
    description="Shortest distance from a point to a polyline.",
    arity=2,
    input_types=["point", "polyline"],
    output={
        "type": "number",
        "unit_behavior": "inherit_horizontal_unit",
    },
    deterministic=True,
    semantics={
        "note": (
            "Iterates all consecutive segments of the polyline "
            "and returns the minimum point-to-segment distance."
        ),
    },
    model_execution={
        "level": "M1",
        "supported": True,
        "recommended_max_items": 30,
        "precision_tolerance": 0.01,
    },
    invariants=[
        {"id": "non_negative", "expression": "result >= 0"},
        {
            "id": "zero_on_segment",
            "expression": "point on segment => result == 0",
        },
    ],
    error_codes=[
        "invalid_coordinates",
        "insufficient_line_points",
        "object_type_mismatch",
    ],
    examples=[
        {
            "inputs": {
                "point": [5, 7],
                "polyline": [[0, 2], [10, 2]],
            },
            "expected": 5.0,
        },
    ],
    implementation="geotask_core.ops.point_to_line_distance_2d",
)

RECT_CONTAINS_POINT = OperatorContract(
    name="rect_contains_point",
    version="1.0",
    family="topology",
    description=(
        "Check if a point is inside or on the boundary of "
        "an axis-aligned rectangle."
    ),
    arity=2,
    input_types=["rect", "point"],
    output={"type": "boolean"},
    deterministic=True,
    semantics={
        "boundary_rules": [
            "Boundary contact counts as containment.",
        ],
    },
    model_execution={
        "level": "M1",
        "supported": True,
        "recommended_max_items": 100,
    },
    invariants=[
        {"id": "bool_output", "expression": "result in (True, False)"},
        {
            "id": "self_contains",
            "expression": "point inside rect => result == True",
        },
    ],
    error_codes=[
        "invalid_bbox",
        "invalid_coordinates",
        "object_type_mismatch",
    ],
    examples=[
        {
            "inputs": {
                "rect": [0, 0, 10, 10],
                "point": [5, 5],
            },
            "expected": True,
        },
    ],
    implementation="geotask_core.ops.rect_contains_point",
)

TIME_OVERLAP = OperatorContract(
    name="time_overlap",
    version="1.0",
    family="temporal",
    description=(
        "Check if two time intervals overlap. "
        "Boundary contact counts as overlap."
    ),
    arity=2,
    input_types=["time_interval", "time_interval"],
    output={"type": "boolean"},
    deterministic=True,
    semantics={
        "time_format": "HH:MM (24-hour)",
        "boundary_rules": [
            "Boundary contact counts as overlap.",
            "Intervals in any order are supported.",
        ],
    },
    model_execution={
        "level": "M1",
        "supported": True,
        "recommended_max_items": 50,
    },
    invariants=[
        {"id": "bool_output", "expression": "result in (True, False)"},
        {
            "id": "symmetric",
            "expression": "overlap(a,b) == overlap(b,a)",
        },
    ],
    error_codes=[
        "invalid_time_format",
        "invalid_interval",
        "object_type_mismatch",
    ],
    examples=[
        {
            "inputs": {
                "a": ["08:00", "10:00"],
                "b": ["09:00", "11:00"],
            },
            "expected": True,
        },
    ],
    implementation="geotask_core.ops.time_overlap",
)

ALTITUDE_OVERLAP = OperatorContract(
    name="altitude_overlap",
    version="1.0",
    family="vertical",
    description=(
        "Check if two altitude ranges overlap. "
        "Boundary contact counts as overlap."
    ),
    arity=2,
    input_types=["altitude_interval", "altitude_interval"],
    output={"type": "boolean"},
    deterministic=True,
    semantics={
        "unit": "meter (relative or absolute)",
        "boundary_rules": [
            "Boundary contact counts as overlap.",
            "Ranges in any order are supported.",
        ],
    },
    model_execution={
        "level": "M1",
        "supported": True,
        "recommended_max_items": 50,
    },
    invariants=[
        {"id": "bool_output", "expression": "result in (True, False)"},
        {
            "id": "symmetric",
            "expression": "overlap(a,b) == overlap(b,a)",
        },
    ],
    error_codes=[
        "invalid_altitude_range",
        "object_type_mismatch",
    ],
    examples=[
        {
            "inputs": {
                "a": [100, 200],
                "b": [150, 250],
            },
            "expected": True,
        },
    ],
    implementation="geotask_core.ops.altitude_overlap",
)

TRAJECTORY_DURATION_SECONDS = OperatorContract(
    name="trajectory_duration_seconds",
    version="1.0",
    family="temporal",
    description="Elapsed seconds between the first and last explicit trajectory samples.",
    arity=1,
    input_types=["trajectory"],
    output={"type": "number", "unit_behavior": "fixed_second"},
    deterministic=True,
    semantics={
        "sample_order": "strictly increasing timezone-aware observed_at",
        "interpolation": "none",
        "excluded_behaviors": [
            "trajectory interpolation",
            "future-position prediction",
            "map matching",
            "resampling",
            "action execution",
        ],
    },
    model_execution={
        "level": "M1",
        "supported": True,
        "recommended_max_items": 1000,
    },
    invariants=[
        {"id": "non_negative", "expression": "result >= 0"},
        {"id": "endpoint_only", "expression": "result == last_time - first_time"},
    ],
    error_codes=[
        "invalid_interval",
        "invalid_coordinates",
        "invalid_reference",
        "object_type_mismatch",
    ],
    examples=[
        {
            "inputs": {
                "trajectory": [
                    {
                        "observed_at": "2026-08-05T08:00:00+08:00",
                        "coordinates": [0, 0],
                    },
                    {
                        "observed_at": "2026-08-05T08:05:00+08:00",
                        "coordinates": [30, 40],
                    },
                ]
            },
            "expected": 300.0,
        },
    ],
    implementation="geotask_core.ops.trajectory_duration_seconds",
)


TRAJECTORY_SEGMENT_METRICS = OperatorContract(
    name="trajectory_segment_metrics",
    version="1.0",
    family="trajectory_measurement",
    description=(
        "Ordered duration, planar distance, and average-speed metrics for every "
        "adjacent pair of explicit trajectory samples."
    ),
    arity=1,
    input_types=["trajectory"],
    output={
        "type": "array",
        "unit_behavior": "horizontal_unit_and_second_fields",
    },
    deterministic=True,
    semantics={
        "segment_definition": "every adjacent explicit sample pair",
        "sample_order": "strictly increasing timezone-aware observed_at",
        "distance_unit": "inherit_horizontal_unit",
        "duration_unit": "second",
        "speed_unit": "horizontal_unit_per_second",
        "interpolation": "none",
        "excluded_behaviors": [
            "trajectory interpolation",
            "smoothing",
            "resampling",
            "future-position prediction",
            "map matching",
            "external truth verification",
            "output release",
            "command delivery",
            "action authorization",
            "action execution",
        ],
    },
    model_execution={
        "level": "M1",
        "supported": True,
        "recommended_max_items": 1000,
    },
    invariants=[
        {
            "id": "segment_count",
            "expression": "len(result) == len(samples) - 1",
        },
        {
            "id": "positive_duration",
            "expression": "all(segment.duration_seconds > 0)",
        },
        {
            "id": "non_negative_distance",
            "expression": "all(segment.distance_in_horizontal_unit >= 0)",
        },
        {
            "id": "average_speed_ratio",
            "expression": "speed == distance / duration_seconds",
        },
    ],
    error_codes=[
        "invalid_interval",
        "invalid_coordinates",
        "invalid_reference",
        "object_type_mismatch",
    ],
    examples=[
        {
            "inputs": {
                "trajectory": [
                    {
                        "observed_at": "2026-08-05T08:00:00+08:00",
                        "coordinates": [0, 0],
                    },
                    {
                        "observed_at": "2026-08-05T08:02:00+08:00",
                        "coordinates": [12, 5],
                    },
                ]
            },
            "expected": [
                {
                    "segment_index": 0,
                    "start_sample_index": 0,
                    "end_sample_index": 1,
                    "start_observed_at": "2026-08-05T08:00:00+08:00",
                    "end_observed_at": "2026-08-05T08:02:00+08:00",
                    "start_coordinates": [0, 0],
                    "end_coordinates": [12, 5],
                    "duration_seconds": 120.0,
                    "distance_in_horizontal_unit": 13.0,
                    "average_speed_in_horizontal_units_per_second": 13.0 / 120.0,
                }
            ],
        }
    ],
    implementation="geotask_core.ops.trajectory_segment_metrics",
)


TRAJECTORY_SEGMENT_CLASSIFICATIONS = OperatorContract(
    name="trajectory_segment_classifications",
    version="1.0",
    family="trajectory_classification",
    description=(
        "Classify every adjacent explicit trajectory segment using caller-declared "
        "stationary and observation-gap thresholds."
    ),
    arity=1,
    input_types=["trajectory"],
    output={
        "type": "array",
        "unit_behavior": "caller_declared_horizontal_and_second_thresholds",
    },
    deterministic=True,
    semantics={
        "segment_definition": "every adjacent explicit sample pair",
        "classification_vocabulary": [
            "stationary_candidate",
            "moving_observed",
            "observation_gap",
            "unverifiable",
        ],
        "required_parameters": [
            "stationary_radius_in_horizontal_unit",
            "minimum_stationary_duration_seconds",
            "maximum_observation_gap_seconds",
            "allow_observation_gap",
        ],
        "stationary_candidate_rule": (
            "distance <= stationary_radius and duration >= minimum_stationary_duration"
        ),
        "observation_gap_rule": (
            "duration > maximum_observation_gap and allow_observation_gap == true"
        ),
        "unverifiable_rule": (
            "duration > maximum_observation_gap and allow_observation_gap == false"
        ),
        "interpolation": "none",
        "excluded_behaviors": [
            "implicit threshold selection",
            "trajectory interpolation",
            "smoothing",
            "resampling",
            "loss-of-link inference",
            "anomaly inference",
            "future-position prediction",
            "map matching",
            "external truth verification",
            "output release",
            "command delivery",
            "action authorization",
            "action execution",
        ],
    },
    model_execution={
        "level": "M1",
        "supported": True,
        "recommended_max_items": 1000,
    },
    invariants=[
        {
            "id": "segment_count",
            "expression": "len(result) == len(samples) - 1",
        },
        {
            "id": "closed_vocabulary",
            "expression": (
                "all(classification in stationary_candidate, moving_observed, "
                "observation_gap, unverifiable)"
            ),
        },
        {
            "id": "thresholds_preserved",
            "expression": "every result record repeats the caller-declared thresholds",
        },
    ],
    error_codes=[
        "invalid_parameters",
        "invalid_interval",
        "invalid_coordinates",
        "invalid_reference",
        "object_type_mismatch",
    ],
    examples=[
        {
            "inputs": {
                "trajectory": [
                    {
                        "observed_at": "2026-08-05T08:00:00+08:00",
                        "coordinates": [0, 0],
                    },
                    {
                        "observed_at": "2026-08-05T08:02:00+08:00",
                        "coordinates": [3, 4],
                    },
                ],
                "parameters": {
                    "stationary_radius_in_horizontal_unit": 5,
                    "minimum_stationary_duration_seconds": 120,
                    "maximum_observation_gap_seconds": 300,
                    "allow_observation_gap": True,
                },
            },
            "expected_classification": "stationary_candidate",
        }
    ],
    implementation="geotask_core.ops.trajectory_segment_classifications",
)


TRAJECTORY_SEGMENT_ACCELERATION_ESTIMATES = OperatorContract(
    name="trajectory_segment_acceleration_estimates",
    version="1.0",
    family="trajectory_acceleration",
    description=(
        "Estimate scalar acceleration between adjacent segment-average speeds "
        "using explicit midpoint timing and a caller-declared continuity limit."
    ),
    arity=1,
    input_types=["trajectory"],
    output={
        "type": "array",
        "unit_behavior": "horizontal_unit_per_second_squared_when_continuous",
    },
    deterministic=True,
    semantics={
        "transition_definition": "every adjacent pair of trajectory segments",
        "representative_time_method": "segment_midpoint",
        "required_parameters": [
            "representative_time_method",
            "maximum_observation_gap_seconds",
        ],
        "continuity_vocabulary": ["continuous_observation", "unverifiable"],
        "acceleration_formula": (
            "(next_average_speed - prior_average_speed) / "
            "(next_midpoint_time - prior_midpoint_time)"
        ),
        "unverifiable_rule": (
            "prior_duration > maximum_observation_gap or "
            "next_duration > maximum_observation_gap"
        ),
        "interpolation": "none",
        "excluded_behaviors": [
            "implicit representative-time selection",
            "implicit maximum-gap selection",
            "instantaneous acceleration claim",
            "vector acceleration claim",
            "direction-change inference",
            "trajectory interpolation",
            "smoothing",
            "resampling",
            "loss-of-link inference",
            "anomaly inference",
            "future-position prediction",
            "map matching",
            "external truth verification",
            "output release",
            "command delivery",
            "action authorization",
            "action execution",
        ],
    },
    model_execution={
        "level": "M1",
        "supported": True,
        "recommended_max_items": 1000,
    },
    invariants=[
        {
            "id": "transition_count",
            "expression": "len(result) == max(len(samples) - 2, 0)",
        },
        {
            "id": "shared_sample_binding",
            "expression": (
                "prior_end_sample_index == next_start_sample_index == shared_sample_index"
            ),
        },
        {
            "id": "unverifiable_has_no_acceleration",
            "expression": (
                "continuity_state == unverifiable implies speed_change == null "
                "and acceleration == null"
            ),
        },
    ],
    error_codes=[
        "invalid_parameters",
        "invalid_interval",
        "invalid_coordinates",
        "invalid_reference",
        "object_type_mismatch",
    ],
    examples=[
        {
            "inputs": {
                "trajectory": [
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
                "parameters": {
                    "representative_time_method": "segment_midpoint",
                    "maximum_observation_gap_seconds": 300,
                },
            },
            "expected": [
                {
                    "continuity_state": "continuous_observation",
                    "acceleration_in_horizontal_units_per_second_squared": 0.0,
                }
            ],
        }
    ],
    implementation="geotask_core.ops.trajectory_segment_acceleration_estimates",
)


TRAJECTORY_IDENTITY_CANDIDATE = OperatorContract(
    name="trajectory_identity_candidate",
    version="1.0",
    family="trajectory_identity",
    description=(
        "Classify whether two discrete trajectory fragments are a same-object "
        "candidate, different-object candidate, or unverifiable using only "
        "their explicit boundary samples and caller-declared limits."
    ),
    arity=2,
    input_types=["trajectory", "trajectory"],
    output={"type": "object", "unit_behavior": "structured_boundary_evidence"},
    deterministic=True,
    semantics={
        "comparison_boundary": (
            "first trajectory final explicit sample to second trajectory first explicit sample"
        ),
        "required_parameters": [
            "maximum_identity_gap_seconds",
            "maximum_identity_distance_in_horizontal_unit",
            "require_same_object_class",
        ],
        "candidate_vocabulary": [
            "same_object_candidate",
            "different_object_candidate",
            "unverifiable",
        ],
        "temporal_precedence": (
            "a positive gap above the declared maximum is unverifiable before "
            "class or distance candidate evaluation"
        ),
        "identity_merge_performed": False,
        "subject_refs_mutated": False,
        "excluded_behaviors": [
            "automatic identity merge",
            "subject reference mutation",
            "identity inference beyond boundary samples",
            "trajectory interpolation",
            "trajectory smoothing",
            "trajectory resampling",
            "map matching",
            "future-position prediction",
            "external identity verification",
            "output release",
            "command delivery",
            "action authorization",
            "action execution",
        ],
    },
    model_execution={"level": "M1", "supported": True, "recommended_max_items": 2},
    invariants=[
        {
            "id": "boundary_sample_binding",
            "expression": (
                "first_boundary_sample_index is final first sample and "
                "second_boundary_sample_index == 0"
            ),
        },
        {
            "id": "no_identity_mutation",
            "expression": (
                "identity_merge_performed == false and subject_refs_mutated == false"
            ),
        },
        {
            "id": "gap_fail_closed",
            "expression": (
                "temporal_gap_seconds > maximum_identity_gap_seconds implies "
                "candidate_state == unverifiable"
            ),
        },
    ],
    error_codes=[
        "invalid_parameters",
        "invalid_interval",
        "invalid_coordinates",
        "invalid_reference",
        "object_type_mismatch",
    ],
    examples=[
        {
            "inputs": {
                "first_trajectory": {
                    "trajectory_ref": "track_a",
                    "subject_ref": "provisional_a",
                    "object_class": "uav",
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
                "second_trajectory": {
                    "trajectory_ref": "track_b",
                    "subject_ref": "provisional_b",
                    "object_class": "uav",
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
            "parameters": {
                "maximum_identity_gap_seconds": 120,
                "maximum_identity_distance_in_horizontal_unit": 10,
                "require_same_object_class": True,
            },
            "expected": {"candidate_state": "same_object_candidate"},
        }
    ],
    implementation="geotask_core.ops.trajectory_identity_candidate",
)


# -- Operator Registry


class OperatorRegistry:
    """Registry of v1.0 operator contracts with name-based lookup.

    All built-in Core operators are registered at construction time. Additional
    contracts can be registered via :meth:`register`.
    """

    def __init__(self) -> None:
        self._contracts: dict[str, OperatorContract] = {}
        for contract in _BUILTIN_CONTRACTS:
            self.register(contract)

    def register(self, contract: OperatorContract) -> None:
        """Register an operator contract.

        Args:
            contract: The OperatorContract to register.

        Raises:
            ValueError: If a contract with the same name is already registered.
        """
        if contract.name in self._contracts:
            raise ValueError(
                f"Operator '{contract.name}' is already registered."
            )
        self._contracts[contract.name] = contract

    def get(self, name: str) -> OperatorContract:
        """Get an operator contract by name.

        Args:
            name: The operator name to look up.

        Returns:
            The matching OperatorContract.

        Raises:
            KeyError: If no contract is registered under *name*.
        """
        if name not in self._contracts:
            raise KeyError(
                f"Operator '{name}' is not registered. "
                f"Available: {self.list_names()}"
            )
        return self._contracts[name]

    def list_names(self) -> list[str]:
        """Return all registered operator names in insertion order."""
        return list(self._contracts.keys())

    def list_all(self) -> list[OperatorContract]:
        """Return all registered operator contracts in insertion order."""
        return list(self._contracts.values())

    def is_registered(self, name: str) -> bool:
        """Check whether an operator is registered.

        Args:
            name: The operator name to check.

        Returns:
            ``True`` if *name* is a registered operator.
        """
        return name in self._contracts


# -- Assertion Dispatcher


class AssertionDispatcher:
    """Assertion-driven execution dispatcher for v1.0.

    Replaces the v0.x runner.py type-based auto-detection with
    contract-bound dispatch:

    1. Look up the operator contract from the registry.
    2. Validate arity against the assertion's object_refs.
    3. Resolve object references to actual GeoObject data.
    4. Call the bound implementation with extracted parameters.
    """

    def __init__(self, registry: OperatorRegistry) -> None:
        self._registry = registry

    # -- Public API

    def dispatch(
        self,
        assertion: Assertion,
        objects: dict[str, GeoObject],
    ) -> Any:
        """Execute an assertion against a set of GeoObjects.

        Args:
            assertion: The Assertion describing what to compute.
            objects: Dictionary mapping object ids to GeoObject instances.

        Returns:
            The result of calling the operator implementation with the
            resolved parameters.

        Raises:
            KeyError: If the operator is not registered.
            ValueError: If arity does not match or object refs are missing.
        """
        contract = self._registry.get(assertion.operator)

        # Validate arity
        if len(assertion.object_refs) != contract.arity:
            raise ValueError(
                f"Operator '{contract.name}' expects {contract.arity} "
                f"object ref(s), got {len(assertion.object_refs)}: "
                f"{assertion.object_refs}"
            )

        # Extract parameters. Identity-candidate evaluation needs the stable
        # trajectory/subject/class reference chain in addition to samples.
        if contract.name == "trajectory_identity_candidate":
            params = [
                self._extract_trajectory_identity_context(ref, objects)
                for ref in assertion.object_refs
            ]
        else:
            params = self._extract_params(
                contract, assertion.object_refs, objects
            )

        # Get and call implementation — pass assertion.parameters as kwargs
        impl = self._get_implementation(contract)
        kwargs: dict[str, Any] = dict(assertion.parameters) if assertion.parameters else {}
        return impl(*params, **kwargs)

    def _extract_trajectory_identity_context(
        self,
        trajectory_ref: str,
        objects: dict[str, GeoObject],
    ) -> dict[str, Any]:
        """Resolve a trajectory and its moving-object class without mutation."""
        trajectory = objects.get(trajectory_ref)
        if trajectory is None or trajectory.type != "trajectory":
            raise ValueError(
                f"Identity candidate requires trajectory '{trajectory_ref}'."
            )
        subject_ref = trajectory.data.get("subject_ref")
        if not isinstance(subject_ref, str) or not subject_ref:
            raise ValueError(
                f"Trajectory '{trajectory_ref}' has no valid subject_ref."
            )
        subject = objects.get(subject_ref)
        if subject is None or subject.type != "moving_object":
            raise ValueError(
                f"Trajectory '{trajectory_ref}' subject '{subject_ref}' is not a moving_object."
            )
        object_class = subject.data.get("object_class")
        if not isinstance(object_class, str) or not object_class:
            raise ValueError(
                f"Moving object '{subject_ref}' has no valid object_class."
            )
        return {
            "trajectory_ref": trajectory_ref,
            "subject_ref": subject_ref,
            "object_class": object_class,
            "samples": trajectory.data.get("samples"),
        }

    # -- Parameter Extraction

    def _extract_params(
        self,
        contract: OperatorContract,
        obj_refs: list[str],
        objects: dict[str, GeoObject],
    ) -> list:
        """Extract positional parameters from GeoObjects.

        Mapping rules by type:
          - ``point`` → ``data["coordinates"]`` (fallback: ``data["xy"]``)
          - ``polyline`` / ``line`` → ``data["coordinates"]``
            (fallback: ``data["points"]``)
          - ``multi_polyline`` → ``data["coordinates"]``
            (fallback: ``data["lines"]``)
          - ``polygon`` → ``data["coordinates"]``
            (fallback: ``data["points"]``)
          - ``rect`` → ``data["bbox"]``
          - ``time_interval`` → ``[data["start"], data["end"]]``
            (fallback: ``data["interval"]``)
          - ``altitude_interval`` → ``[data["min"], data["max"]]``
            (fallback: ``data["range"]``)
          - ``trajectory`` → ``data["samples"]``
        """
        params: list = []
        for ref, expected_type in zip(obj_refs, contract.input_types):
            obj = objects.get(ref)
            if obj is None:
                raise ValueError(
                    f"Object reference '{ref}' not found in objects dict. "
                    f"Available: {list(objects.keys())}"
                )
            value = self._extract_typed_param(obj, expected_type)
            params.append(value)
        return params

    def _extract_typed_param(
        self, obj: GeoObject, expected_type: str
    ) -> Any:
        """Extract the geometry data from a single GeoObject.

        Handles legacy type aliases (e.g. ``line`` → ``polyline``) and
        field fallbacks for backward compatibility with v0.x data shapes.
        """
        data = obj.data
        obj_type = obj.type

        # point
        if expected_type == "point":
            if obj_type not in ("point",):
                raise ValueError(
                    f"Expected type 'point' for '{obj.id}', "
                    f"got '{obj_type}'"
                )
            coords = data.get("coordinates") or data.get("xy")
            if coords is None:
                raise ValueError(
                    f"Point object '{obj.id}' has no coordinates or xy field."
                )
            return coords

        # polyline (legacy alias: line)
        if expected_type == "polyline":
            if obj_type not in ("polyline", "line"):
                raise ValueError(
                    f"Expected type 'polyline' (or legacy 'line') "
                    f"for '{obj.id}', got '{obj_type}'"
                )
            coords = data.get("coordinates") or data.get("points")
            if coords is None:
                raise ValueError(
                    f"Polyline object '{obj.id}' has no coordinates "
                    f"or points field."
                )
            return coords

        # multi_polyline
        if expected_type == "multi_polyline":
            if obj_type != "multi_polyline":
                raise ValueError(
                    f"Expected type 'multi_polyline' for '{obj.id}', "
                    f"got '{obj_type}'"
                )
            coords = data.get("coordinates") or data.get("lines")
            if coords is None:
                raise ValueError(
                    f"Multi-polyline object '{obj.id}' has no coordinates "
                    f"or lines field."
                )
            return coords

        # polygon
        if expected_type == "polygon":
            if obj_type != "polygon":
                raise ValueError(
                    f"Expected type 'polygon' for '{obj.id}', got '{obj_type}'"
                )
            coords = data.get("coordinates") or data.get("points")
            if coords is None:
                raise ValueError(
                    f"Polygon object '{obj.id}' has no coordinates or points field."
                )
            return coords

        # rect
        if expected_type == "rect":
            if obj_type not in ("rect",):
                raise ValueError(
                    f"Expected type 'rect' for '{obj.id}', "
                    f"got '{obj_type}'"
                )
            bbox = data.get("bbox")
            if bbox is None:
                raise ValueError(
                    f"Rect object '{obj.id}' has no bbox field."
                )
            return bbox

        # time_interval
        if expected_type == "time_interval":
            if obj_type not in ("time_interval", "time"):
                raise ValueError(
                    f"Expected type 'time_interval' for '{obj.id}', "
                    f"got '{obj_type}'"
                )
            interval = None
            if "start" in data and "end" in data:
                interval = [data["start"], data["end"]]
            elif "interval" in data:
                interval = data["interval"]
            if interval is None:
                raise ValueError(
                    f"Time interval object '{obj.id}' has no "
                    f"start/end or interval field."
                )
            return interval

        # altitude_interval
        if expected_type == "altitude_interval":
            if obj_type not in ("altitude_interval", "altitude"):
                raise ValueError(
                    f"Expected type 'altitude_interval' for '{obj.id}', "
                    f"got '{obj_type}'"
                )
            range_val = None
            if "min" in data and "max" in data:
                range_val = [data["min"], data["max"]]
            elif "range" in data:
                range_val = data["range"]
            if range_val is None:
                raise ValueError(
                    f"Altitude interval object '{obj.id}' has no "
                    f"min/max or range field."
                )
            return range_val

        # trajectory
        if expected_type == "trajectory":
            if obj_type != "trajectory":
                raise ValueError(
                    f"Expected type 'trajectory' for '{obj.id}', got '{obj_type}'"
                )
            samples = data.get("samples")
            if samples is None:
                raise ValueError(f"Trajectory object '{obj.id}' has no samples field.")
            return samples

        raise ValueError(
            f"Unsupported expected type '{expected_type}' "
            f"for object '{obj.id}'."
        )

    # -- Implementation Binding

    def _get_implementation(self, contract: OperatorContract) -> Callable:
        """Dynamically import and return the bound implementation.

        Parses the ``implementation`` field of the contract (e.g.
        ``"geotask_core.ops.distance_2d"``), imports the module,
        and returns the named callable.

        Returns:
            The imported callable.

        Raises:
            ImportError: If the module cannot be imported.
            AttributeError: If the function is not found in the module.
        """
        impl_path: str = contract.implementation
        if not impl_path:
            raise ValueError(
                f"Operator '{contract.name}' has no implementation bound."
            )

        module_name, func_name = impl_path.rsplit(".", 1)
        module = importlib.import_module(module_name)
        func = getattr(module, func_name, None)
        if func is None:
            raise AttributeError(
                f"Function '{func_name}' not found in module '{module_name}' "
                f"(bound by operator '{contract.name}')."
            )
        if not callable(func):
            raise TypeError(
                f"'{impl_path}' is not callable "
                f"(bound by operator '{contract.name}')."
            )
        return func


# -- Built-in contract list & default registry

_BUILTIN_CONTRACTS: list[OperatorContract] = [
    DISTANCE_2D,
    LINE_INTERSECTS_RECT,
    MULTI_POLYLINE_INTERSECTS_RECT,
    POINT_IN_POLYGON,
    POLYGON_CONTAINS_POINT,
    POINT_TO_LINE_DISTANCE_2D,
    RECT_CONTAINS_POINT,
    TIME_OVERLAP,
    ALTITUDE_OVERLAP,
    TRAJECTORY_DURATION_SECONDS,
    TRAJECTORY_SEGMENT_METRICS,
    TRAJECTORY_SEGMENT_CLASSIFICATIONS,
    TRAJECTORY_SEGMENT_ACCELERATION_ESTIMATES,
    TRAJECTORY_IDENTITY_CANDIDATE,
]

#: Default pre-populated registry with all built-in Core operators.
default_registry = OperatorRegistry()
