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
    """A 2D line segment defined by two or more points.

    In GeoTask Core v0.1-lite, only the first two points are used as a segment.
    """

    name: str
    points: list[list[float]]  # [[x1, y1], [x2, y2], ...]


@dataclass
class RectObject:
    """An axis-aligned rectangle defined by a bounding box."""

    name: str
    bbox: list[float]  # [min_x, min_y, max_x, max_y]


@dataclass
class StirDocument:
    """Top-level GeoTask (formerly STIR) document after parsing."""

    version: str
    name: str
    goal: str
    crs: str
    unit: str
    axes: dict
    objects: dict  # name -> PointObject | LineObject | RectObject
    ops: dict  # operation_name -> formula string
    task: dict  # raw task definition, including questions
    raw: dict = field(repr=False)  # original parsed YAML dict
