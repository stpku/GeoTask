"""Lightweight data structures for GeoTask Core.

These models represent spatial objects and the top-level GeoTask document.
They are deliberately simple -- no heavy inheritance, no ORM, no GIS frameworks.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PointObject:
    """A 2D point in local coordinates."""

    name: str
    xy: list[float]  # [x, y]


@dataclass
class LineObject:
    """A 2D polyline defined by two or more points.

    Current deterministic polyline operators inspect all consecutive segments.
    """

    name: str
    points: list[list[float]]  # [[x1, y1], [x2, y2], ...]


@dataclass
class RectObject:
    """An axis-aligned rectangle defined by a bounding box."""

    name: str
    bbox: list[float]  # [min_x, min_y, max_x, max_y]


@dataclass
class PolygonObject:
    """A closed 2D polygon ring.

    The first and last coordinate must be identical. Holes and multi-polygons
    are intentionally outside this Core object contract.
    """

    name: str
    coordinates: list[list[float]]


@dataclass
class MultiPolylineObject:
    """A collection of independent 2D polylines."""

    name: str
    coordinates: list[list[list[float]]]


@dataclass
class MovingObject:
    """A caller-declared moving-entity identity without implied position."""

    name: str
    object_class: str
    identity: str


@dataclass
class TrajectorySample:
    """One explicitly timestamped 2D observation."""

    observed_at: str
    coordinates: list[float]


@dataclass
class TrajectoryObject:
    """A discrete, ordered trajectory bound to one moving object."""

    name: str
    subject_ref: str
    samples: list[TrajectorySample]
    interpolation: str = "none"


@dataclass
class TrajectorySegment:
    """One adjacent-sample segment with explicit deterministic metrics."""

    segment_index: int
    start_sample_index: int
    end_sample_index: int
    start_observed_at: str
    end_observed_at: str
    start_coordinates: list[float]
    end_coordinates: list[float]
    duration_seconds: float
    distance_in_horizontal_unit: float
    average_speed_in_horizontal_units_per_second: float


@dataclass
class TrajectorySegmentClassification:
    """One adjacent trajectory segment classified by caller-declared thresholds."""

    segment_index: int
    start_sample_index: int
    end_sample_index: int
    start_observed_at: str
    end_observed_at: str
    start_coordinates: list[float]
    end_coordinates: list[float]
    duration_seconds: float
    distance_in_horizontal_unit: float
    average_speed_in_horizontal_units_per_second: float
    classification: str
    classification_reason: str
    stationary_radius_in_horizontal_unit: float
    minimum_stationary_duration_seconds: float
    maximum_observation_gap_seconds: float
    allow_observation_gap: bool


@dataclass
class StirDocument:
    """Top-level GeoTask (formerly STIR) document after parsing."""

    version: str
    name: str
    goal: str
    crs: str
    unit: str
    axes: dict
    objects: dict  # name -> supported lightweight object model
    ops: dict  # operation_name -> formula string
    task: dict  # raw task definition, including questions
    raw: dict = field(repr=False)  # original parsed YAML dict
