"""Public-source profiles for the first TC1-Real experiment.

The profiles describe source semantics observed during experiment design. They
are not immutable authority records. Every acquisition must record the exact
endpoint, request, retrieval time, and content hash actually used.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PublicSourceProfile:
    source_id: str
    source_family: str
    role: str
    official_landing_url: str
    observed_machine_endpoint: str | None = None
    spatial_reference: str | None = None
    spatial_resolution_meters: float | None = None
    temporal_update_seconds: int | None = None
    query_formats: tuple[str, ...] = ()
    can_authorize_real_action: bool = False
    notes: str = ""


FAA_UASFM = PublicSourceProfile(
    source_id="faa-uasfm",
    source_family="FAA UAS Facility Maps",
    role="controlled-airspace planning context and grid altitude guidance",
    official_landing_url=(
        "https://www.faa.gov/uas/commercial_operators/uas_facility_maps"
    ),
    observed_machine_endpoint=(
        "https://services6.arcgis.com/ssFJjBXIUyZDrSYZ/ArcGIS/rest/services/"
        "FAA_UAS_FacilityMap_Data/FeatureServer/0"
    ),
    spatial_reference="EPSG:4326",
    query_formats=("json", "geojson", "pbf"),
    can_authorize_real_action=False,
    notes=(
        "FAA describes UAS Facility Maps as informational/job-aid data for "
        "airspace authorization requests; the maps do not themselves authorize "
        "an operation. Endpoint identity must be re-recorded per acquisition."
    ),
)


FAA_DDOF = PublicSourceProfile(
    source_id="faa-ddof",
    source_family="FAA Daily Digital Obstacle File",
    role="aviation obstacle context",
    official_landing_url=(
        "https://www.faa.gov/air_traffic/flight_info/aeronav/"
        "digital_products/dailydof/"
    ),
    observed_machine_endpoint=(
        "https://aeronav.faa.gov/Obst_Data/DAILY_DOF_CSV.ZIP"
    ),
    spatial_reference="WGS84",
    query_formats=("zip-csv",),
    can_authorize_real_action=False,
    notes=(
        "FAA states the Daily DOF CSV contains the same obstacle data as DDOF "
        "with decimal-degree latitude/longitude added for GIS use. The source "
        "is a broad file download rather than a bounded query service. FAA's "
        "May 21, 2026 DDOF README cautions that the file contains only man-made "
        "obstructions affecting domestic aeronautical charting and does not "
        "purport to contain every obstruction. It also contains both verified "
        "('O') and unverified ('U') records; unverified position and height have "
        "not been verified by the FAA Obstacle Data Team."
    ),
)


NOAA_HRRR = PublicSourceProfile(
    source_id="noaa-hrrr",
    source_family="NOAA/NCEP High-Resolution Rapid Refresh",
    role="time-varying atmospheric context",
    official_landing_url="https://rapidrefresh.noaa.gov/hrrr/",
    observed_machine_endpoint=(
        "https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl"
    ),
    spatial_reference=None,
    spatial_resolution_meters=3000.0,
    temporal_update_seconds=3600,
    query_formats=("grib2-subset",),
    can_authorize_real_action=False,
    notes=(
        "NOAA describes HRRR as a real-time 3-km, hourly updated atmospheric "
        "model. NCEP NOMADS Grib Filter supports variable, level, and geographic "
        "subregion selection. A TC1-Real acquisition must record the exact run, "
        "forecast hour/valid time, variables, levels, region, and endpoint used."
    ),
)


TC1_REAL_SOURCE_PROFILES = (FAA_UASFM, FAA_DDOF, NOAA_HRRR)


def get_source_profile(source_id: str) -> PublicSourceProfile:
    for profile in TC1_REAL_SOURCE_PROFILES:
        if profile.source_id == source_id:
            return profile
    raise KeyError(f"unknown TC1-Real source profile: {source_id}")
