from __future__ import annotations

from benchmarks.tc1_real.spatial_planning.experiment_spec import (
    CRITICAL_REQUIREMENT_IDS,
    EXISTING_LIBRARIES_REQUIREMENT_ID,
    FROZEN_POPULATION_VARIABLE,
    FROZEN_POPULATION_VARIABLE_SOURCE_DESCRIPTION,
    FROZEN_POPULATION_YEAR,
    HOTSPOT_BBOX,
    HOTSPOT_LAND_USE_REQUIREMENT_ID,
    PROJECTED_POPULATION_REQUIREMENT_ID,
    R0_BROAD_BBOX,
    TASK_BBOX,
)
from benchmarks.tc1_real.spatial_planning.population_selection import (
    build_frozen_population_where,
)


def _contains(outer: tuple[float, ...], inner: tuple[float, ...]) -> bool:
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and outer[2] >= inner[2]
        and outer[3] >= inner[3]
    )


def test_nested_scopes_and_critical_requirements_are_frozen() -> None:
    assert _contains(R0_BROAD_BBOX, TASK_BBOX)
    assert _contains(TASK_BBOX, HOTSPOT_BBOX)
    assert CRITICAL_REQUIREMENT_IDS == (
        PROJECTED_POPULATION_REQUIREMENT_ID,
        EXISTING_LIBRARIES_REQUIREMENT_ID,
        HOTSPOT_LAND_USE_REQUIREMENT_ID,
    )


def test_population_semantics_are_frozen_before_scoring() -> None:
    assert FROZEN_POPULATION_VARIABLE == "HHPop"
    assert FROZEN_POPULATION_VARIABLE_SOURCE_DESCRIPTION == "Houshold Population"
    assert FROZEN_POPULATION_YEAR == 2030


def test_population_where_uses_only_frozen_semantics_and_sorted_units() -> None:
    assert build_frozen_population_where((7, 3, 7)) == (
        "newluau IN (3,7) AND popvar = 'HHPop' AND year = 2030"
    )
