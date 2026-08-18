"""Frozen inputs for the TC1-Real spatial-planning proof.

These constants are benchmark inputs, not domain recommendations. In
particular, the 2030 horizon is fixed before headline R0/R1/RG scoring only to
prevent post-result cherry-picking; GeoTask does not claim that 2030 is the
correct real-world library-planning horizon.
"""

from __future__ import annotations


R0_BROAD_BBOX = (-112.20, 33.30, -111.90, 33.60)
TASK_BBOX = (-112.10, 33.40, -112.00, 33.50)
HOTSPOT_BBOX = (-112.075, 33.425, -112.050, 33.450)

PROJECTED_POPULATION_REQUIREMENT_ID = "projected_population_context"
EXISTING_LIBRARIES_REQUIREMENT_ID = "existing_library_locations"
HOTSPOT_LAND_USE_REQUIREMENT_ID = "hotspot_land_use_detail"

CRITICAL_REQUIREMENT_IDS = (
    PROJECTED_POPULATION_REQUIREMENT_ID,
    EXISTING_LIBRARIES_REQUIREMENT_ID,
    HOTSPOT_LAND_USE_REQUIREMENT_ID,
)

# Observed from the exact table-13 distinct dictionary on 2026-08-18.
FROZEN_POPULATION_VARIABLE = "HHPop"
FROZEN_POPULATION_VARIABLE_SOURCE_DESCRIPTION = "Houshold Population"
FROZEN_POPULATION_YEAR = 2030

# This is an experiment label, not a claim that the horizon is the uniquely
# correct planning horizon for a real public-library decision.
FROZEN_POPULATION_HORIZON_RATIONALE = (
    "2030 future household-population context fixed before R0/R1/RG scoring"
)
