"""Population-selection policy for the TC1-Real spatial-planning benchmark.

This module is deliberately scenario-local. It binds the already frozen
``HHPop @ 2030`` experiment input to a set of spatially selected planning-unit
IDs. It is not a generic GeoTask Relevance operator and must not be promoted to
Core merely because it is useful in this benchmark.
"""

from __future__ import annotations

from typing import Iterable

from benchmarks.tc1_real.spatial_planning.arcgis_acquisition import (
    build_numeric_in_where,
)
from benchmarks.tc1_real.spatial_planning.experiment_spec import (
    FROZEN_POPULATION_VARIABLE,
    FROZEN_POPULATION_YEAR,
)


def build_frozen_population_where(newluau_values: Iterable[int]) -> str:
    """Build the exact population predicate frozen before headline scoring."""

    unit_clause = build_numeric_in_where("newluau", newluau_values)
    # The variable and year are module constants observed/frozen before R0/R1/RG
    # scoring. They are not caller-controlled strings, avoiding an injection
    # surface while keeping the experiment definition explicit.
    return (
        f"{unit_clause} AND popvar = '{FROZEN_POPULATION_VARIABLE}' "
        f"AND year = {FROZEN_POPULATION_YEAR}"
    )
