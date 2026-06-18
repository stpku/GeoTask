"""Mock data for LowAlt Site Precheck v0.1.

ALL COORDINATES ARE FICTIONAL local_xy_m. No real locations.
"""

from .models import (
    CandidateSite, InitialRoute, SensitiveSite, RestrictedZone,
    ObstacleBand, FlightTimeWindow, FlightAltitudeBand,
    LowAltPrecheckRequest,
)


def basic_safe_case() -> LowAltPrecheckRequest:
    """Case 1: Safe — no conflicts, all checks pass."""
    return LowAltPrecheckRequest(
        request_id="safe_case_001",
        candidate_sites=[
            CandidateSite(site_id="S001", name="Mock Helipad Alpha", xy=[100.0, 200.0]),
        ],
        initial_routes=[],
        sensitive_sites=[
            SensitiveSite(site_id="SS001", category="school", xy=[500.0, 600.0], risk_radius_m=200.0),
        ],
        restricted_zones=[],
        obstacles=[],
        flight_time_windows=[
            FlightTimeWindow(start_time="09:00", end_time="10:00"),
        ],
        flight_altitude_band=FlightAltitudeBand(min_alt_m=50.0, max_alt_m=120.0),
        restriction_time_windows=[],
    )


def route_zone_conflict_case() -> LowAltPrecheckRequest:
    """Case 2: Route intersects a restricted zone."""
    return LowAltPrecheckRequest(
        request_id="conflict_case_002",
        candidate_sites=[
            CandidateSite(site_id="S002", name="Mock Vertiport Beta", xy=[0.0, 0.0]),
        ],
        initial_routes=[
            InitialRoute(route_id="R001", points=[[0.0, 0.0], [500.0, 500.0]]),
        ],
        sensitive_sites=[],
        restricted_zones=[
            RestrictedZone(
                zone_id="Z001", bbox=[200.0, 200.0, 300.0, 300.0],
                restriction_type="no_fly",
            ),
        ],
        obstacles=[],
        flight_time_windows=[
            FlightTimeWindow(start_time="08:00", end_time="12:00"),
        ],
        restriction_time_windows=[],
    )


def missing_data_case() -> LowAltPrecheckRequest:
    """Case 3: Missing obstacle and time restriction data."""
    return LowAltPrecheckRequest(
        request_id="missing_data_003",
        candidate_sites=[
            CandidateSite(site_id="S003", name="Mock Site Gamma", xy=[300.0, 400.0]),
        ],
        initial_routes=[],
        sensitive_sites=[],
        restricted_zones=[],
        obstacles=[],
        flight_time_windows=[
            FlightTimeWindow(start_time="06:00", end_time="18:00"),
        ],
        flight_altitude_band=FlightAltitudeBand(min_alt_m=0.0, max_alt_m=150.0),
        restriction_time_windows=[],
    )


def invalid_reference_case() -> LowAltPrecheckRequest:
    """Case 4: Request with empty input — produces need_review due to gaps."""
    return LowAltPrecheckRequest(
        request_id="invalid_ref_004",
        candidate_sites=[],
        initial_routes=[],
        sensitive_sites=[],
        restricted_zones=[],
        obstacles=[],
    )
