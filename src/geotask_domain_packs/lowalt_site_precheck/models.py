from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CandidateSite:
    site_id: str
    name: str
    xy: list[float]
    site_type: str = "takeoff_landing"


@dataclass
class InitialRoute:
    route_id: str
    points: list[list[float]]


@dataclass
class SensitiveSite:
    site_id: str
    category: str
    xy: list[float]
    risk_radius_m: float


@dataclass
class RestrictedZone:
    zone_id: str
    bbox: list[float]
    restriction_type: str


@dataclass
class ObstacleBand:
    obstacle_id: str
    xy: list[float]
    height_range_m: list[float]
    clearance_margin_m: float


@dataclass
class FlightTimeWindow:
    start_time: str
    end_time: str


@dataclass
class FlightAltitudeBand:
    min_alt_m: float
    max_alt_m: float


@dataclass
class LowAltPrecheckRequest:
    """Top-level request for a low-altitude site precheck."""
    request_id: str
    candidate_sites: list[CandidateSite] = field(default_factory=list)
    initial_routes: list[InitialRoute] = field(default_factory=list)
    sensitive_sites: list[SensitiveSite] = field(default_factory=list)
    restricted_zones: list[RestrictedZone] = field(default_factory=list)
    obstacles: list[ObstacleBand] = field(default_factory=list)
    flight_time_windows: list[FlightTimeWindow] = field(default_factory=list)
    flight_altitude_band: Optional[FlightAltitudeBand] = None
    restriction_time_windows: list[FlightTimeWindow] = field(default_factory=list)
    token_budget: Optional[int] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class LowAltPrecheckResult:
    """Result of a low-altitude site precheck."""
    request_id: str
    domain_pack: str = "lowalt_site_precheck"
    version: str = "0.1-mock"
    overall_status: str = "need_review"
    risk_items: list[dict] = field(default_factory=list)
    verified_items: list[dict] = field(default_factory=list)
    contradicted_items: list[dict] = field(default_factory=list)
    review_items: list[dict] = field(default_factory=list)
    planned_data_gaps: list[str] = field(default_factory=list)
    planned_model_inferred_items: list[str] = field(default_factory=list)
    summary: str = ""
    disclaimer: str = (
        "This is a mock precheck using fictional data. "
        "It does NOT constitute flight approval or regulatory authorization."
    )
