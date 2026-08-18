"""Public source profiles for the TC1-Real spatial-planning experiment.

These are experiment observations, not an authority registry. Every live
acquisition must record the exact machine endpoint, request parameters, time and
content hash that were actually used.
"""

from __future__ import annotations

from benchmarks.tc1_real.source_profiles import PublicSourceProfile


PHX_GROWTH_PROJECTIONS = PublicSourceProfile(
    source_id="phx-growth-projections",
    source_family="City of Phoenix Growth Projections",
    role="coarse planning-unit geometry and population-projection context",
    official_landing_url=(
        "https://mapportal.phoenix.gov/pds/rest/services/Hosted/"
        "GrowthProjections_MapViewer_0524_WFL1/FeatureServer/layers"
    ),
    observed_machine_endpoint=(
        "https://mapportal.phoenix.gov/pds/rest/services/Hosted/"
        "GrowthProjections_MapViewer_0524_WFL1/FeatureServer"
    ),
    spatial_reference="EPSG:3857 source service; request/replay normalized to EPSG:4326",
    query_formats=("json", "geojson", "pbf"),
    can_authorize_real_action=False,
    notes=(
        "Experiment uses spatial planning-unit layer 2 and related population "
        "table 13. The service exposes a newluau key; table fields observed in "
        "the public service metadata include popvar, vardesc, year and popcount. "
        "No investment recommendation or population-model accuracy claim is "
        "inferred from source availability."
    ),
)


PHX_LIBRARIES = PublicSourceProfile(
    source_id="phx-libraries",
    source_family="City of Phoenix Libraries",
    role="existing public-library location context",
    official_landing_url=(
        "https://maps.phoenix.gov/pub/rest/services/Public/Libraries/MapServer/0"
    ),
    observed_machine_endpoint=(
        "https://maps.phoenix.gov/pub/rest/services/Public/Libraries/MapServer/0"
    ),
    spatial_reference="native service WKID 2868; request/replay normalized to EPSG:4326",
    query_formats=("json", "geojson", "pbf"),
    can_authorize_real_action=False,
    notes=(
        "The experiment uses library point locations only. It does not infer "
        "building capacity, service quality, staffing, opening hours or a need "
        "for a new facility."
    ),
)


PHX_LAND_USE_ZONES = PublicSourceProfile(
    source_id="phx-land-use-zones",
    source_family="City of Phoenix Land Use Area Zones",
    role="fine local land-use context for the frozen planning hotspot",
    official_landing_url=(
        "https://maps.phoenix.gov/pds/rest/services/Hosted/"
        "Land_Use_Area_Zones/FeatureServer"
    ),
    observed_machine_endpoint=(
        "https://maps.phoenix.gov/pds/rest/services/Hosted/"
        "Land_Use_Area_Zones/FeatureServer/14"
    ),
    spatial_reference="native service WKID 2868; request/replay normalized to EPSG:4326",
    query_formats=("json",),
    can_authorize_real_action=False,
    notes=(
        "The public service currently declares JSON query format rather than "
        "GeoJSON/PBF. Land-use polygons are treated as local planning context "
        "only; geometry or labels are not transformed into a recommendation "
        "score inside this benchmark."
    ),
)


SPATIAL_PLANNING_SOURCE_PROFILES = (
    PHX_GROWTH_PROJECTIONS,
    PHX_LIBRARIES,
    PHX_LAND_USE_ZONES,
)
