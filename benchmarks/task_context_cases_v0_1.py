"""Synthetic TC1 benchmark fixtures.

These cases are deliberately fictional and deterministic. They test the
cost/context trade-off contract only; they are not evidence of real flight,
planning, or safety accuracy.
"""

from __future__ import annotations

from geotask_core.task_context import ContextCandidate, ContextRequirement, TaskFrame

from benchmarks.task_context_v0_1 import BenchmarkCase


COST_UNIT = "fixture_cost_point"


def low_altitude_mission_case() -> BenchmarkCase:
    task = TaskFrame(
        task_id="tc1-low-altitude-mission",
        goal="Prepare context for a fictional low-altitude delivery mission",
        subject_refs=("uav-logistics-small",),
        spatial_scope="corridor-a-b",
        temporal_scope="window-1500-1600",
        outputs=("route_risk_input",),
        context_budget=10.0,
        context_budget_unit=COST_UNIT,
    )
    requirements = (
        ContextRequirement(
            requirement_id="weather",
            what="weather along the mission corridor",
            reason="wind and precipitation can change route feasibility",
            spatial_scope="corridor-a-b",
            temporal_scope="window-1500-1600",
            max_spatial_resolution=1000.0,
            spatial_resolution_unit="meter",
            max_temporal_resolution_seconds=1800.0,
        ),
        ContextRequirement(
            requirement_id="airspace",
            what="temporary airspace restrictions",
            reason="applicable restrictions can invalidate a candidate route",
            spatial_scope="corridor-a-b",
            temporal_scope="window-1500-1600",
        ),
        ContextRequirement(
            requirement_id="obstacles",
            what="local obstacle context",
            reason="corridor clearance needs local spatial detail",
            spatial_scope="corridor-a-b",
            max_spatial_resolution=10.0,
            spatial_resolution_unit="meter",
        ),
        ContextRequirement(
            requirement_id="poi_labels",
            what="nearby POI labels",
            reason="useful for explanation but not required for route-risk input",
            critical=False,
            spatial_scope="corridor-a-b",
        ),
    )
    candidates = (
        ContextCandidate(
            candidate_id="weather-500m",
            source="fictional-weather-standard",
            requirement_ids=("weather",),
            spatial_scope="corridor-a-b",
            temporal_scope="window-1500-1600",
            spatial_resolution=500.0,
            spatial_resolution_unit="meter",
            temporal_resolution_seconds=900.0,
            acquisition_cost=2.0,
            cost_unit=COST_UNIT,
        ),
        ContextCandidate(
            candidate_id="weather-100m-premium",
            source="fictional-weather-premium",
            requirement_ids=("weather",),
            spatial_scope="corridor-a-b",
            temporal_scope="window-1500-1600",
            spatial_resolution=100.0,
            spatial_resolution_unit="meter",
            temporal_resolution_seconds=300.0,
            acquisition_cost=8.0,
            cost_unit=COST_UNIT,
        ),
        ContextCandidate(
            candidate_id="airspace-notice",
            source="fictional-airspace-provider",
            requirement_ids=("airspace",),
            spatial_scope="corridor-a-b",
            temporal_scope="window-1500-1600",
            acquisition_cost=1.0,
            cost_unit=COST_UNIT,
        ),
        ContextCandidate(
            candidate_id="obstacles-100m",
            source="fictional-regional-map",
            requirement_ids=("obstacles",),
            spatial_scope="corridor-a-b",
            spatial_resolution=100.0,
            spatial_resolution_unit="meter",
            acquisition_cost=1.0,
            cost_unit=COST_UNIT,
        ),
        ContextCandidate(
            candidate_id="obstacles-10m",
            source="fictional-local-map",
            requirement_ids=("obstacles",),
            spatial_scope="corridor-a-b",
            spatial_resolution=10.0,
            spatial_resolution_unit="meter",
            acquisition_cost=5.0,
            cost_unit=COST_UNIT,
        ),
        ContextCandidate(
            candidate_id="poi-labels",
            source="fictional-poi-provider",
            requirement_ids=("poi_labels",),
            spatial_scope="corridor-a-b",
            acquisition_cost=2.0,
            cost_unit=COST_UNIT,
        ),
    )
    return BenchmarkCase(
        case_id="low-altitude-mission",
        domain="low_altitude",
        task=task,
        requirements=requirements,
        candidates=candidates,
        # Fixed checklist uses cheap regional obstacles and adds explanatory POI,
        # but it does not adapt the obstacle resolution to the declared task need.
        manual_candidate_ids=(
            "weather-500m",
            "airspace-notice",
            "obstacles-100m",
            "poi-labels",
        ),
        notes="Synthetic context-selection fixture; no real flight authorization.",
    )


def spatial_planning_case() -> BenchmarkCase:
    task = TaskFrame(
        task_id="tc1-spatial-planning",
        goal="Prepare multi-scale context for a fictional district capacity-planning review",
        subject_refs=("district-x",),
        spatial_scope="district-x",
        temporal_scope="planning-cycle-2027",
        outputs=("planning_review_input",),
        context_budget=10.0,
        context_budget_unit=COST_UNIT,
    )
    requirements = (
        ContextRequirement(
            requirement_id="district_demand",
            what="district-scale demand density",
            reason="coarse demand pattern identifies where capacity review matters",
            spatial_scope="district-x",
            temporal_scope="planning-cycle-2027",
            max_spatial_resolution=1000.0,
            spatial_resolution_unit="meter",
        ),
        ContextRequirement(
            requirement_id="facility_capacity",
            what="district-scale facility capacity",
            reason="capacity must be compared with the demand pattern",
            spatial_scope="district-x",
            temporal_scope="planning-cycle-2027",
            max_spatial_resolution=1000.0,
            spatial_resolution_unit="meter",
        ),
        ContextRequirement(
            requirement_id="hotspot_building_demand",
            what="building-demand detail inside hotspot-c",
            reason="only the ambiguous hotspot needs local refinement",
            spatial_scope="hotspot-c",
            temporal_scope="planning-cycle-2027",
            max_spatial_resolution=100.0,
            spatial_resolution_unit="meter",
        ),
        ContextRequirement(
            requirement_id="poi_labels",
            what="district POI labels",
            reason="useful for explanation but not required for capacity comparison",
            critical=False,
            spatial_scope="district-x",
        ),
    )
    candidates = (
        ContextCandidate(
            candidate_id="demand-1km",
            source="fictional-demand-grid",
            requirement_ids=("district_demand",),
            spatial_scope="district-x",
            temporal_scope="planning-cycle-2027",
            spatial_resolution=1000.0,
            spatial_resolution_unit="meter",
            acquisition_cost=2.0,
            cost_unit=COST_UNIT,
        ),
        ContextCandidate(
            candidate_id="demand-100m",
            source="fictional-demand-grid-premium",
            requirement_ids=("district_demand",),
            spatial_scope="district-x",
            temporal_scope="planning-cycle-2027",
            spatial_resolution=100.0,
            spatial_resolution_unit="meter",
            acquisition_cost=8.0,
            cost_unit=COST_UNIT,
        ),
        ContextCandidate(
            candidate_id="capacity-1km",
            source="fictional-capacity-grid",
            requirement_ids=("facility_capacity",),
            spatial_scope="district-x",
            temporal_scope="planning-cycle-2027",
            spatial_resolution=1000.0,
            spatial_resolution_unit="meter",
            acquisition_cost=2.0,
            cost_unit=COST_UNIT,
        ),
        ContextCandidate(
            candidate_id="capacity-100m",
            source="fictional-capacity-grid-premium",
            requirement_ids=("facility_capacity",),
            spatial_scope="district-x",
            temporal_scope="planning-cycle-2027",
            spatial_resolution=100.0,
            spatial_resolution_unit="meter",
            acquisition_cost=8.0,
            cost_unit=COST_UNIT,
        ),
        ContextCandidate(
            candidate_id="hotspot-buildings-100m",
            source="fictional-building-demand",
            requirement_ids=("hotspot_building_demand",),
            spatial_scope="hotspot-c",
            temporal_scope="planning-cycle-2027",
            spatial_resolution=100.0,
            spatial_resolution_unit="meter",
            acquisition_cost=4.0,
            cost_unit=COST_UNIT,
        ),
        ContextCandidate(
            candidate_id="district-buildings-10m",
            source="fictional-citywide-building-demand",
            requirement_ids=("hotspot_building_demand",),
            # Expensive detail exists, but its declared scope is district-wide;
            # v0.1 Core will not infer that it can substitute for hotspot-c.
            spatial_scope="district-x",
            temporal_scope="planning-cycle-2027",
            spatial_resolution=10.0,
            spatial_resolution_unit="meter",
            acquisition_cost=12.0,
            cost_unit=COST_UNIT,
        ),
        ContextCandidate(
            candidate_id="district-poi-labels",
            source="fictional-poi-provider",
            requirement_ids=("poi_labels",),
            spatial_scope="district-x",
            acquisition_cost=2.0,
            cost_unit=COST_UNIT,
        ),
    )
    return BenchmarkCase(
        case_id="spatial-planning",
        domain="spatial_planning",
        task=task,
        requirements=requirements,
        candidates=candidates,
        # A fixed district checklist never drills into hotspot-c, so it misses
        # the one context requirement created by local decision ambiguity.
        manual_candidate_ids=(
            "demand-1km",
            "capacity-1km",
            "district-poi-labels",
        ),
        notes="Synthetic multi-scale planning fixture; no real investment decision.",
    )


def tc1_cases() -> tuple[BenchmarkCase, ...]:
    return (low_altitude_mission_case(), spatial_planning_case())
