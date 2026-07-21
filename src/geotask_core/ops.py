"""Deterministic spatial operators for GeoTask Core.

These are the *only* computational operations in Core.
All values computed here are verifiable without an LLM.
"""

import math


def distance_2d(a: list[float], b: list[float]) -> float:
    """Compute 2D Euclidean distance between two points."""
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
    """Check if any segment of a polyline intersects an axis-aligned rectangle.

    Iterates **all** consecutive point pairs (segments):
        points[0]→points[1], points[1]→points[2], …, points[n-2]→points[n-1]

    Returns ``True`` as soon as any segment touches or crosses the rectangle.
    Boundary contact counts as intersection.
    """
    if len(line_points) < 2:
        return False

    # Pre-compute rectangle edges once
    min_x, min_y, max_x, max_y = bbox[0], bbox[1], bbox[2], bbox[3]
    edges = [
        ([min_x, min_y], [max_x, min_y]),
        ([max_x, min_y], [max_x, max_y]),
        ([max_x, max_y], [min_x, max_y]),
        ([min_x, max_y], [min_x, min_y]),
    ]

    # Check every consecutive segment
    for i in range(len(line_points) - 1):
        p1 = line_points[i]
        p2 = line_points[i + 1]

        if _point_in_rect(p1, bbox) or _point_in_rect(p2, bbox):
            return True

        for e1, e2 in edges:
            if _segments_intersect(p1, p2, e1, e2):
                return True

    return False


def _point_to_segment_distance(
    px: float, py: float,
    x1: float, y1: float, x2: float, y2: float,
) -> float:
    """Compute the shortest 2D distance from point (px,py) to segment (x1,y1)-(x2,y2)."""
    dx = x2 - x1
    dy = y2 - y1

    if dx == 0.0 and dy == 0.0:
        # Degenerate segment — distance to the point itself
        return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)

    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))

    proj_x = x1 + t * dx
    proj_y = y1 + t * dy

    return math.sqrt((px - proj_x) ** 2 + (py - proj_y) ** 2)


def point_to_line_distance_2d(point: list[float], line_points: list[list[float]]) -> float:
    """Compute the shortest 2D distance from a point to a polyline.

    Iterates **all** consecutive segments and returns the minimum distance.
    Degenerate (zero-length) segments are handled gracefully.

    Args:
        point: ``[x, y]``
        line_points: ``[[x1,y1], [x2,y2], ...]`` — must have ≥ 2 points.

    Returns:
        Minimum Euclidean distance from *point* to any segment of the polyline.

    Raises:
        ValueError: If fewer than 2 points are provided.
    """
    if len(line_points) < 2:
        raise ValueError(
            f"point_to_line_distance_2d requires at least 2 points, "
            f"got {len(line_points)}"
        )

    px, py = point[0], point[1]
    min_dist = float("inf")

    for i in range(len(line_points) - 1):
        x1, y1 = line_points[i][0], line_points[i][1]
        x2, y2 = line_points[i + 1][0], line_points[i + 1][1]
        dist = _point_to_segment_distance(px, py, x1, y1, x2, y2)
        if dist < min_dist:
            min_dist = dist

    return min_dist


def rect_contains_point(bbox: list[float], point: list[float]) -> bool:
    """Check if a point is inside or on the boundary of an axis-aligned rectangle."""
    x, y = point[0], point[1]
    min_x, min_y, max_x, max_y = bbox[0], bbox[1], bbox[2], bbox[3]
    return min_x <= x <= max_x and min_y <= y <= max_y


def time_overlap(a: list[str], b: list[str]) -> bool:
    """Check if two time intervals ["HH:MM","HH:MM"] overlap (boundary contact counts)."""
    a_start = _time_to_minutes(a[0])
    a_end = _time_to_minutes(a[1])
    b_start = _time_to_minutes(b[0])
    b_end = _time_to_minutes(b[1])
    return a_start <= b_end and b_start <= a_end


def altitude_overlap(a: list[float], b: list[float]) -> bool:
    """Check if two altitude ranges [min, max] overlap (boundary contact counts)."""
    return a[0] <= b[1] and b[0] <= a[1]


def _time_to_minutes(t: str) -> int:
    """Convert HH:MM string to minutes since midnight."""
    parts = t.split(":")
    return int(parts[0]) * 60 + int(parts[1])
