"""LowAlt Site Precheck Rules — mock deterministic checks using GeoTask Core ops.

All checks use the 6 production Core operators. No external data or APIs.
Results are for demonstration only.
"""

from geotask_core.ops import (
    distance_2d,
    line_intersects_rect,
    rect_contains_point,
    altitude_overlap,
    time_overlap,
    point_to_line_distance_2d,
)
from .models import (
    CandidateSite, InitialRoute, SensitiveSite, RestrictedZone,
    ObstacleBand, FlightTimeWindow, FlightAltitudeBand,
)


def check_sensitive_site_distance(
    site: CandidateSite,
    sensitive: SensitiveSite,
) -> dict:
    """Check if candidate site is too close to a sensitive site."""
    dist = distance_2d(site.xy, sensitive.xy)
    risk = dist < sensitive.risk_radius_m
    return {
        "name": f"site_{site.site_id}_sensitive_{sensitive.site_id}",
        "status": "contradicted" if risk else "verified",
        "operator": "distance_2d",
        "value": round(dist, 2),
        "threshold": sensitive.risk_radius_m,
        "risk": risk,
        "detail": (
            f"Distance {dist:.2f}m {'<' if risk else '>='} "
            f"risk radius {sensitive.risk_radius_m}m"
        ),
    }


def check_route_restricted_zone_conflict(
    route: InitialRoute,
    zone: RestrictedZone,
) -> dict:
    """Check if initial route intersects a restricted zone."""
    if len(route.points) < 2:
        return {
            "name": f"route_{route.route_id}_zone_{zone.zone_id}",
            "status": "need_review",
            "operator": "line_intersects_rect",
            "value": None,
            "detail": "Route has fewer than 2 points",
        }
    line_start = route.points[0]
    line_end = route.points[-1]
    intersects = line_intersects_rect(
        [line_start, line_end],
        zone.bbox,
    )
    return {
        "name": f"route_{route.route_id}_zone_{zone.zone_id}",
        "status": "contradicted" if intersects else "verified",
        "operator": "line_intersects_rect",
        "value": intersects,
        "risk": intersects,
        "detail": (
            f"Route {'intersects' if intersects else 'does not intersect'} "
            f"restricted zone {zone.zone_id}"
        ),
    }


def check_site_in_restricted_zone(
    site: CandidateSite,
    zone: RestrictedZone,
) -> dict:
    """Check if candidate site is within a restricted zone."""
    inside = rect_contains_point(zone.bbox, site.xy)
    return {
        "name": f"site_{site.site_id}_zone_{zone.zone_id}",
        "status": "contradicted" if inside else "verified",
        "operator": "rect_contains_point",
        "value": inside,
        "risk": inside,
        "detail": (
            f"Site {'is inside' if inside else 'is outside'} "
            f"restricted zone {zone.zone_id}"
        ),
    }


def check_obstacle_altitude_conflict(
    obstacle: ObstacleBand,
    flight_altitude: FlightAltitudeBand,
) -> dict:
    """Check if flight altitude conflicts with obstacle height + clearance."""
    effective_min = obstacle.height_range_m[0] - obstacle.clearance_margin_m
    effective_max = obstacle.height_range_m[1] + obstacle.clearance_margin_m
    conflicts = altitude_overlap(
        [flight_altitude.min_alt_m, flight_altitude.max_alt_m],
        [effective_min, effective_max],
    )
    return {
        "name": f"obstacle_{obstacle.obstacle_id}_altitude",
        "status": "contradicted" if conflicts else "verified",
        "operator": "altitude_overlap",
        "value": conflicts,
        "risk": conflicts,
        "detail": (
            f"Flight altitude [{flight_altitude.min_alt_m}, {flight_altitude.max_alt_m}]m "
            f"{'overlaps' if conflicts else 'clear of'} "
            f"obstacle effective range [{effective_min}, {effective_max}]m"
        ),
    }


def check_time_window_conflict(
    flight_window: FlightTimeWindow,
    restriction_window: FlightTimeWindow,
) -> dict:
    """Check if flight time window conflicts with restriction time window."""
    conflicts = time_overlap(
        [flight_window.start_time, flight_window.end_time],
        [restriction_window.start_time, restriction_window.end_time],
    )
    return {
        "name": f"time_{flight_window.start_time}_{restriction_window.start_time}",
        "status": "contradicted" if conflicts else "verified",
        "operator": "time_overlap",
        "value": conflicts,
        "risk": conflicts,
        "detail": (
            f"Flight time {flight_window.start_time}-{flight_window.end_time} "
            f"{'overlaps' if conflicts else 'does not overlap'} "
            f"restriction {restriction_window.start_time}-{restriction_window.end_time}"
        ),
    }


def identify_data_gaps(request) -> list[str]:
    """Identify missing data that would be needed for a complete precheck."""
    gaps = []
    if not request.sensitive_sites:
        gaps.append("sensitive_sites: no sensitive sites provided")
    if not request.restricted_zones:
        gaps.append("restricted_zones: no restricted zones provided")
    if not request.obstacles:
        gaps.append("obstacles: no obstacle data provided")
    if not request.restriction_time_windows:
        gaps.append("restriction_time_windows: no time restrictions provided")
    if not request.flight_altitude_band:
        gaps.append("flight_altitude_band: no flight altitude band defined")
    if not request.flight_time_windows:
        gaps.append("flight_time_windows: no flight time windows defined")
    return gaps
