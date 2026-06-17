"""Deterministic spatial operators for GeoTask Core.

These are the *only* computational operations in Core.
All values computed here are verifiable without an LLM.
"""

import math


def distance_2d(a: list[float], b: list[float]) -> float:
    """Compute 2D Euclidean distance between two points.

    Args:
        a: [x1, y1]
        b: [x2, y2]

    Returns:
        Euclidean distance sqrt((x1 - x2)^2 + (y1 - y2)^2)
    """
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return math.sqrt(dx * dx + dy * dy)


def _segments_intersect(
    p1: list[float], p2: list[float], p3: list[float], p4: list[float]
) -> bool:
    """Check if segment p1-p2 intersects segment p3-p4 (including endpoints)."""
    def _cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def _on_segment(p, q, r):
        return (
            (min(p[0], r[0]) <= q[0] <= max(p[0], r[0]))
            and (min(p[1], r[1]) <= q[1] <= max(p[1], r[1]))
        )

    d1 = _cross(p3, p4, p1)
    d2 = _cross(p3, p4, p2)
    d3 = _cross(p1, p2, p3)
    d4 = _cross(p1, p2, p4)

    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and (
        (d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)
    ):
        return True

    if d1 == 0 and _on_segment(p3, p1, p4):
        return True
    if d2 == 0 and _on_segment(p3, p2, p4):
        return True
    if d3 == 0 and _on_segment(p1, p3, p2):
        return True
    if d4 == 0 and _on_segment(p1, p4, p2):
        return True

    return False


def _point_in_rect(p: list[float], bbox: list[float]) -> bool:
    """Check if point p is inside (or on the boundary of) the axis-aligned rect."""
    x, y = p[0], p[1]
    min_x, min_y, max_x, max_y = bbox[0], bbox[1], bbox[2], bbox[3]
    return min_x <= x <= max_x and min_y <= y <= max_y


def line_intersects_rect(
    line_points: list[list[float]], bbox: list[float]
) -> bool:
    """Check if a 2D line segment intersects an axis-aligned rectangle.

    In GeoTask Core v0.1-lite, only the first two points of line_points
    are used as the line segment.

    Boundary contact is considered intersection.

    Args:
        line_points: [[x1, y1], [x2, y2], ...]
        bbox: [min_x, min_y, max_x, max_y]

    Returns:
        True if any part of the line segment crosses or touches the rectangle.
    """
    if len(line_points) < 2:
        return False

    p1 = line_points[0]
    p2 = line_points[1]

    # If either endpoint is inside (or on boundary), it intersects
    if _point_in_rect(p1, bbox) or _point_in_rect(p2, bbox):
        return True

    min_x, min_y, max_x, max_y = bbox[0], bbox[1], bbox[2], bbox[3]

    # Check intersection with each of the 4 edges of the rect
    edges = [
        ([min_x, min_y], [max_x, min_y]),  # bottom
        ([max_x, min_y], [max_x, max_y]),  # right
        ([max_x, max_y], [min_x, max_y]),  # top
        ([min_x, max_y], [min_x, min_y]),  # left
    ]

    for e1, e2 in edges:
        if _segments_intersect(p1, p2, e1, e2):
            return True

    return False
