"""Deterministic spatial operators for GeoTask Core.

These are the *only* computational operations in Core.
All values computed here are verifiable without an LLM.
"""

import math
from datetime import datetime


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


def _point_on_segment(
    point: list[float], start: list[float], end: list[float]
) -> bool:
    """Return whether *point* lies on the closed segment *start*→*end*."""
    cross = (
        (end[0] - start[0]) * (point[1] - start[1])
        - (end[1] - start[1]) * (point[0] - start[0])
    )
    if abs(cross) > 1e-12:
        return False
    return (
        min(start[0], end[0]) <= point[0] <= max(start[0], end[0])
        and min(start[1], end[1]) <= point[1] <= max(start[1], end[1])
    )


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


def multi_polyline_intersects_rect(
    multi_polyline: list[list[list[float]]], bbox: list[float]
) -> bool:
    """Check whether any member polyline intersects an axis-aligned rectangle.

    Boundary contact counts as intersection. Empty collections return ``False``;
    malformed members are rejected by document validation before execution.
    """
    return any(line_intersects_rect(polyline, bbox) for polyline in multi_polyline)


def point_in_polygon(
    point: list[float], polygon: list[list[float]]
) -> bool:
    """Check whether a point is inside or on the boundary of a closed polygon.

    Uses the even-odd rule over the polygon ring. Validation requires a closed
    ring with at least three distinct vertices; this operator deliberately does
    not infer holes or repair self-intersections.
    """
    if len(polygon) < 4:
        return False

    inside = False
    x, y = point
    for index in range(len(polygon) - 1):
        start = polygon[index]
        end = polygon[index + 1]
        if _point_on_segment(point, start, end):
            return True

        y_crosses = (start[1] > y) != (end[1] > y)
        if not y_crosses:
            continue
        intersection_x = (
            (end[0] - start[0]) * (y - start[1]) / (end[1] - start[1])
            + start[0]
        )
        if x < intersection_x:
            inside = not inside

    return inside


def polygon_contains_point(
    polygon: list[list[float]], point: list[float]
) -> bool:
    """Check whether a closed polygon contains a point.

    This predicate has the same deterministic even-odd and closed-boundary
    semantics as :func:`point_in_polygon`, but exposes the container-first
    argument order used by ``rect_contains_point`` and GeoTask assertions with
    ``object_refs: [polygon, point]``.
    """
    return point_in_polygon(point, polygon)


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


def trajectory_duration_seconds(samples: list[dict]) -> float:
    """Return elapsed seconds between the first and last trajectory samples.

    Validation guarantees at least two samples, timezone-aware timestamps, and
    strict chronological ordering. The operator performs no interpolation,
    prediction, map matching, resampling, or action execution.
    """
    start = datetime.fromisoformat(
        str(samples[0]["observed_at"]).replace("Z", "+00:00")
    )
    end = datetime.fromisoformat(
        str(samples[-1]["observed_at"]).replace("Z", "+00:00")
    )
    return (end - start).total_seconds()


def trajectory_segment_metrics(samples: list[dict]) -> list[dict]:
    """Return deterministic metrics for each adjacent explicit sample pair.

    Validation guarantees finite 2D coordinates and strictly increasing,
    timezone-aware timestamps. Distances are expressed in the document's
    horizontal unit; average speeds are therefore horizontal units per second.
    The operator performs no interpolation, smoothing, resampling, prediction,
    map matching, external lookup, or real-world action.
    """
    segments: list[dict] = []
    for index in range(len(samples) - 1):
        start_sample = samples[index]
        end_sample = samples[index + 1]
        start_time = datetime.fromisoformat(
            str(start_sample["observed_at"]).replace("Z", "+00:00")
        )
        end_time = datetime.fromisoformat(
            str(end_sample["observed_at"]).replace("Z", "+00:00")
        )
        duration_seconds = (end_time - start_time).total_seconds()
        if duration_seconds <= 0:
            raise ValueError(
                "trajectory_segment_metrics requires strictly increasing sample times"
            )
        start_coordinates = list(start_sample["coordinates"])
        end_coordinates = list(end_sample["coordinates"])
        distance = distance_2d(start_coordinates, end_coordinates)
        segments.append(
            {
                "segment_index": index,
                "start_sample_index": index,
                "end_sample_index": index + 1,
                "start_observed_at": str(start_sample["observed_at"]),
                "end_observed_at": str(end_sample["observed_at"]),
                "start_coordinates": start_coordinates,
                "end_coordinates": end_coordinates,
                "duration_seconds": duration_seconds,
                "distance_in_horizontal_unit": distance,
                "average_speed_in_horizontal_units_per_second": distance / duration_seconds,
            }
        )
    return segments


def trajectory_segment_classifications(
    samples: list[dict],
    *,
    stationary_radius_in_horizontal_unit: float,
    minimum_stationary_duration_seconds: float,
    maximum_observation_gap_seconds: float,
    allow_observation_gap: bool,
) -> list[dict]:
    """Classify adjacent explicit samples using only caller-declared thresholds.

    The operator returns exactly one classification for each adjacent sample
    pair: ``stationary_candidate``, ``moving_observed``, ``observation_gap``,
    or ``unverifiable``. It performs no interpolation and does not interpret an
    observation gap as loss of link, anomaly, or a real-world action condition.
    """
    numeric_parameters = {
        "stationary_radius_in_horizontal_unit": stationary_radius_in_horizontal_unit,
        "minimum_stationary_duration_seconds": minimum_stationary_duration_seconds,
        "maximum_observation_gap_seconds": maximum_observation_gap_seconds,
    }
    for name, value in numeric_parameters.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be a finite number")
        if not math.isfinite(float(value)):
            raise ValueError(f"{name} must be a finite number")
    if stationary_radius_in_horizontal_unit < 0:
        raise ValueError("stationary_radius_in_horizontal_unit must be non-negative")
    if minimum_stationary_duration_seconds <= 0:
        raise ValueError("minimum_stationary_duration_seconds must be positive")
    if maximum_observation_gap_seconds <= 0:
        raise ValueError("maximum_observation_gap_seconds must be positive")
    if not isinstance(allow_observation_gap, bool):
        raise ValueError("allow_observation_gap must be boolean")

    classifications: list[dict] = []
    for segment in trajectory_segment_metrics(samples):
        duration = segment["duration_seconds"]
        distance = segment["distance_in_horizontal_unit"]
        if duration > maximum_observation_gap_seconds:
            if allow_observation_gap:
                classification = "observation_gap"
                reason = "duration_exceeds_declared_maximum_gap"
            else:
                classification = "unverifiable"
                reason = "duration_exceeds_maximum_gap_but_gap_marking_is_disallowed"
        elif (
            distance <= stationary_radius_in_horizontal_unit
            and duration >= minimum_stationary_duration_seconds
        ):
            classification = "stationary_candidate"
            reason = "within_declared_radius_and_meets_declared_minimum_duration"
        else:
            classification = "moving_observed"
            reason = "does_not_meet_declared_stationary_candidate_conditions"

        classifications.append(
            {
                **segment,
                "classification": classification,
                "classification_reason": reason,
                "stationary_radius_in_horizontal_unit": float(
                    stationary_radius_in_horizontal_unit
                ),
                "minimum_stationary_duration_seconds": float(
                    minimum_stationary_duration_seconds
                ),
                "maximum_observation_gap_seconds": float(
                    maximum_observation_gap_seconds
                ),
                "allow_observation_gap": allow_observation_gap,
            }
        )
    return classifications


def trajectory_segment_acceleration_estimates(
    samples: list[dict],
    *,
    representative_time_method: str,
    maximum_observation_gap_seconds: float,
) -> list[dict]:
    """Estimate scalar acceleration between adjacent segment-average speeds.

    Each segment is represented at its temporal midpoint. Acceleration is the
    change between two adjacent segment-average speeds divided by the elapsed
    time between those midpoints. If either participating segment exceeds the
    caller-declared maximum observation interval, the transition is returned as
    ``unverifiable`` and no speed change or acceleration value is emitted.

    The result is not an instantaneous or vector acceleration measurement and
    performs no interpolation, smoothing, resampling, prediction, map matching,
    lost-link inference, anomaly inference, authorization, or action execution.
    """
    if representative_time_method != "segment_midpoint":
        raise ValueError("representative_time_method must be 'segment_midpoint'")
    if (
        isinstance(maximum_observation_gap_seconds, bool)
        or not isinstance(maximum_observation_gap_seconds, (int, float))
        or not math.isfinite(float(maximum_observation_gap_seconds))
    ):
        raise ValueError("maximum_observation_gap_seconds must be a finite number")
    if maximum_observation_gap_seconds <= 0:
        raise ValueError("maximum_observation_gap_seconds must be positive")

    segments = trajectory_segment_metrics(samples)
    estimates: list[dict] = []
    for transition_index in range(len(segments) - 1):
        prior = segments[transition_index]
        next_segment = segments[transition_index + 1]

        prior_start = datetime.fromisoformat(
            str(prior["start_observed_at"]).replace("Z", "+00:00")
        )
        prior_end = datetime.fromisoformat(
            str(prior["end_observed_at"]).replace("Z", "+00:00")
        )
        next_start = datetime.fromisoformat(
            str(next_segment["start_observed_at"]).replace("Z", "+00:00")
        )
        next_end = datetime.fromisoformat(
            str(next_segment["end_observed_at"]).replace("Z", "+00:00")
        )
        if prior_end != next_start:
            raise ValueError(
                "trajectory_segment_acceleration_estimates requires adjacent segments "
                "to share one explicit sample"
            )

        prior_midpoint = prior_start + (prior_end - prior_start) / 2
        next_midpoint = next_start + (next_end - next_start) / 2
        representative_interval_seconds = (
            next_midpoint - prior_midpoint
        ).total_seconds()
        if representative_interval_seconds <= 0:
            raise ValueError(
                "trajectory_segment_acceleration_estimates requires increasing "
                "segment midpoint times"
            )

        prior_gap = prior["duration_seconds"] > maximum_observation_gap_seconds
        next_gap = next_segment["duration_seconds"] > maximum_observation_gap_seconds
        if prior_gap or next_gap:
            continuity_state = "unverifiable"
            if prior_gap and next_gap:
                continuity_reason = "both_segments_exceed_declared_maximum_gap"
            elif prior_gap:
                continuity_reason = "prior_segment_exceeds_declared_maximum_gap"
            else:
                continuity_reason = "next_segment_exceeds_declared_maximum_gap"
            speed_change = None
            acceleration = None
        else:
            continuity_state = "continuous_observation"
            continuity_reason = "both_segments_within_declared_maximum_gap"
            speed_change = (
                next_segment["average_speed_in_horizontal_units_per_second"]
                - prior["average_speed_in_horizontal_units_per_second"]
            )
            acceleration = speed_change / representative_interval_seconds

        estimates.append(
            {
                "transition_index": transition_index,
                "prior_segment_index": prior["segment_index"],
                "next_segment_index": next_segment["segment_index"],
                "shared_sample_index": prior["end_sample_index"],
                "prior_start_sample_index": prior["start_sample_index"],
                "prior_end_sample_index": prior["end_sample_index"],
                "next_start_sample_index": next_segment["start_sample_index"],
                "next_end_sample_index": next_segment["end_sample_index"],
                "prior_start_observed_at": prior["start_observed_at"],
                "shared_observed_at": prior["end_observed_at"],
                "next_end_observed_at": next_segment["end_observed_at"],
                "prior_start_coordinates": prior["start_coordinates"],
                "shared_coordinates": prior["end_coordinates"],
                "next_end_coordinates": next_segment["end_coordinates"],
                "prior_duration_seconds": prior["duration_seconds"],
                "next_duration_seconds": next_segment["duration_seconds"],
                "prior_average_speed_in_horizontal_units_per_second": prior[
                    "average_speed_in_horizontal_units_per_second"
                ],
                "next_average_speed_in_horizontal_units_per_second": next_segment[
                    "average_speed_in_horizontal_units_per_second"
                ],
                "prior_representative_at": prior_midpoint.isoformat(timespec="seconds"),
                "next_representative_at": next_midpoint.isoformat(timespec="seconds"),
                "representative_interval_seconds": representative_interval_seconds,
                "speed_change_in_horizontal_units_per_second": speed_change,
                "acceleration_in_horizontal_units_per_second_squared": acceleration,
                "continuity_state": continuity_state,
                "continuity_reason": continuity_reason,
                "representative_time_method": representative_time_method,
                "maximum_observation_gap_seconds": float(
                    maximum_observation_gap_seconds
                ),
            }
        )
    return estimates


def trajectory_identity_candidate(
    first_trajectory: dict,
    second_trajectory: dict,
    *,
    maximum_identity_gap_seconds: float,
    maximum_identity_distance_in_horizontal_unit: float,
    require_same_object_class: bool,
) -> dict:
    """Classify a boundary-sample identity candidate for two trajectories.

    The function compares only the final explicit sample of the first
    trajectory with the first explicit sample of the second trajectory. It
    never mutates subject references, creates a merged identity, interpolates,
    smooths, map matches, predicts, verifies external identity, publishes
    output, authorizes action, or executes action.
    """
    for name, value, allow_zero in (
        ("maximum_identity_gap_seconds", maximum_identity_gap_seconds, False),
        (
            "maximum_identity_distance_in_horizontal_unit",
            maximum_identity_distance_in_horizontal_unit,
            True,
        ),
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
        ):
            raise ValueError(f"{name} must be a finite number")
        if allow_zero:
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
        elif value <= 0:
            raise ValueError(f"{name} must be positive")
    if not isinstance(require_same_object_class, bool):
        raise ValueError("require_same_object_class must be a boolean")

    def _validate_context(name: str, context: dict) -> tuple[list[dict], str, str, str]:
        if not isinstance(context, dict):
            raise ValueError(f"{name} must be a trajectory context object")
        required = {"trajectory_ref", "subject_ref", "object_class", "samples"}
        missing = sorted(required - set(context))
        if missing:
            raise ValueError(f"{name} is missing required fields: {missing}")
        trajectory_ref = context["trajectory_ref"]
        subject_ref = context["subject_ref"]
        object_class = context["object_class"]
        if not isinstance(trajectory_ref, str) or not trajectory_ref.strip():
            raise ValueError(f"{name}.trajectory_ref must be a non-empty string")
        if not isinstance(subject_ref, str) or not subject_ref.strip():
            raise ValueError(f"{name}.subject_ref must be a non-empty string")
        if not isinstance(object_class, str) or not object_class.strip():
            raise ValueError(f"{name}.object_class must be a non-empty string")
        samples = context["samples"]
        trajectory_segment_metrics(samples)
        return samples, trajectory_ref, subject_ref, object_class

    first_samples, first_ref, first_subject, first_class = _validate_context(
        "first_trajectory", first_trajectory
    )
    second_samples, second_ref, second_subject, second_class = _validate_context(
        "second_trajectory", second_trajectory
    )
    if first_ref == second_ref:
        raise ValueError("trajectory_identity_candidate requires two distinct trajectories")

    first_index = len(first_samples) - 1
    second_index = 0
    first_sample = first_samples[first_index]
    second_sample = second_samples[second_index]
    first_time = datetime.fromisoformat(
        str(first_sample["observed_at"]).replace("Z", "+00:00")
    )
    second_time = datetime.fromisoformat(
        str(second_sample["observed_at"]).replace("Z", "+00:00")
    )
    if first_time.tzinfo is None or second_time.tzinfo is None:
        raise ValueError("trajectory_identity_candidate requires timezone-aware timestamps")
    temporal_gap_seconds = (second_time - first_time).total_seconds()
    if temporal_gap_seconds <= 0:
        raise ValueError(
            "trajectory_identity_candidate requires the second trajectory to start "
            "after the first trajectory ends"
        )

    def _boundary_coordinates(value: object, *, label: str) -> list[float]:
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ValueError(f"{label} must contain exactly two coordinates")
        coordinates = list(value)
        for coordinate in coordinates:
            if (
                isinstance(coordinate, bool)
                or not isinstance(coordinate, (int, float))
                or not math.isfinite(float(coordinate))
            ):
                raise ValueError(f"{label} coordinates must be finite numbers")
        return coordinates

    first_coordinates = _boundary_coordinates(
        first_sample["coordinates"], label="first boundary sample"
    )
    second_coordinates = _boundary_coordinates(
        second_sample["coordinates"], label="second boundary sample"
    )
    spatial_distance = distance_2d(first_coordinates, second_coordinates)

    if temporal_gap_seconds > maximum_identity_gap_seconds:
        state = "unverifiable"
        reason = "temporal_gap_exceeds_declared_maximum"
    elif require_same_object_class and first_class != second_class:
        state = "different_object_candidate"
        reason = "object_classes_differ_under_declared_requirement"
    elif spatial_distance <= maximum_identity_distance_in_horizontal_unit:
        state = "same_object_candidate"
        reason = "boundary_samples_within_declared_time_and_distance_limits"
    else:
        state = "different_object_candidate"
        reason = "boundary_distance_exceeds_declared_maximum"

    return {
        "candidate_state": state,
        "candidate_reason": reason,
        "first_trajectory_ref": first_ref,
        "second_trajectory_ref": second_ref,
        "first_subject_ref": first_subject,
        "second_subject_ref": second_subject,
        "first_object_class": first_class,
        "second_object_class": second_class,
        "first_boundary_sample_index": first_index,
        "second_boundary_sample_index": second_index,
        "first_boundary_observed_at": first_time.isoformat(timespec="seconds"),
        "second_boundary_observed_at": second_time.isoformat(timespec="seconds"),
        "first_boundary_coordinates": first_coordinates,
        "second_boundary_coordinates": second_coordinates,
        "temporal_gap_seconds": temporal_gap_seconds,
        "spatial_distance_in_horizontal_unit": spatial_distance,
        "maximum_identity_gap_seconds": float(maximum_identity_gap_seconds),
        "maximum_identity_distance_in_horizontal_unit": float(
            maximum_identity_distance_in_horizontal_unit
        ),
        "require_same_object_class": require_same_object_class,
        "evidence_basis": (
            "first_trajectory_final_sample_to_second_trajectory_first_sample"
        ),
        "identity_merge_performed": False,
        "subject_refs_mutated": False,
    }


def _time_to_minutes(t: str) -> int:
    """Convert HH:MM string to minutes since midnight."""
    parts = t.split(":")
    return int(parts[0]) * 60 + int(parts[1])
