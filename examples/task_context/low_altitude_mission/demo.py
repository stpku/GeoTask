"""Task-first GeoTask context demo.

The example is fictional and offline. It does not fetch live weather,
airspace, maps, or authorize a real flight.
"""

from geotask_core.task_context import (
    ContextCandidate,
    ContextRequirement,
    TaskFrame,
    assess_task_context,
)


task = TaskFrame(
    task_id="delivery-a-b-1500",
    goal="Prepare context for a fictional low-altitude delivery mission",
    subject_refs=("uav-logistics-small",),
    spatial_scope="corridor-a-b",
    temporal_scope="2026-08-19T15:00/16:00",
    outputs=("route_risk_input",),
    context_budget=12.0,
    context_budget_unit="credits",
)

requirements = [
    ContextRequirement(
        requirement_id="weather",
        what="wind and precipitation for the mission corridor",
        reason="weather can change route feasibility",
        spatial_scope="corridor-a-b",
        temporal_scope="2026-08-19T15:00/16:00",
        max_spatial_resolution=1000.0,
        spatial_resolution_unit="meter",
        max_temporal_resolution_seconds=1800.0,
    ),
    ContextRequirement(
        requirement_id="airspace",
        what="applicable temporary airspace restrictions",
        reason="the route must avoid restrictions applicable to this corridor and window",
        spatial_scope="corridor-a-b",
        temporal_scope="2026-08-19T15:00/16:00",
    ),
    ContextRequirement(
        requirement_id="obstacles",
        what="local obstacle context near the candidate corridor",
        reason="local clearance checking requires finer spatial detail",
        spatial_scope="corridor-a-b",
        max_spatial_resolution=10.0,
        spatial_resolution_unit="meter",
    ),
    ContextRequirement(
        requirement_id="poi_labels",
        what="nearby POI labels",
        reason="useful for human explanation but not required for route-risk input",
        critical=False,
        spatial_scope="corridor-a-b",
    ),
]

selected_context = [
    ContextCandidate(
        candidate_id="weather-forecast-500m",
        source="fictional-weather-provider",
        requirement_ids=("weather",),
        spatial_scope="corridor-a-b",
        temporal_scope="2026-08-19T15:00/16:00",
        spatial_resolution=500.0,
        spatial_resolution_unit="meter",
        temporal_resolution_seconds=900.0,
        acquisition_cost=2.0,
        cost_unit="credits",
    ),
    ContextCandidate(
        candidate_id="airspace-notice",
        source="fictional-airspace-provider",
        requirement_ids=("airspace",),
        spatial_scope="corridor-a-b",
        temporal_scope="2026-08-19T15:00/16:00",
        acquisition_cost=1.0,
        cost_unit="credits",
    ),
    ContextCandidate(
        candidate_id="regional-obstacle-grid-100m",
        source="fictional-map-provider",
        requirement_ids=("obstacles",),
        spatial_scope="corridor-a-b",
        spatial_resolution=100.0,
        spatial_resolution_unit="meter",
        acquisition_cost=1.0,
        cost_unit="credits",
    ),
]

result = assess_task_context(task, requirements, selected_context)

print(f"task_id={result.task_id}")
print(f"status={result.status}")
print(f"gaps={','.join(result.gap_requirement_ids) or '-'}")
print(
    "refinement_needed="
    f"{','.join(result.refinement_requirement_ids) or '-'}"
)
print(f"context_cost={result.total_acquisition_cost} {result.cost_unit or ''}".rstrip())
print(f"budget_exceeded={str(result.budget_exceeded).lower()}")

# Expected interpretation:
# - weather and airspace are usable;
# - obstacle context is relevant/applicable but too coarse (100 m > 10 m);
# - POI labels are non-critical and may remain absent;
# - the task context is insufficient only because a critical obstacle
#   requirement still needs refinement.
