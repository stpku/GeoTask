from __future__ import annotations

import copy

import pytest

from benchmarks.tc1_real.spatial_planning.recorded_context import (
    NETWORK_BYTES,
    compare_policies,
)


def _measurement() -> dict[str, object]:
    return {
        "growth": {
            "broad": {"complete": True, "network_bytes": 24_000, "id_count": 471},
            "task": {"complete": True, "network_bytes": 6_600, "id_count": 125},
        },
        "population": {
            "broad": {
                "complete": True,
                "network_bytes": 48_000,
                "id_count": 471,
                "variable": "HHPop",
                "year": 2030,
                "unit_coverage_complete": True,
                "missing_unit_count": 0,
            },
            "task": {
                "complete": True,
                "network_bytes": 12_000,
                "id_count": 125,
                "variable": "HHPop",
                "year": 2030,
                "unit_coverage_complete": True,
                "missing_unit_count": 0,
            },
        },
        "libraries": {
            "broad": {"complete": True, "network_bytes": 2_500, "id_count": 12},
            "task": {"complete": True, "network_bytes": 500, "id_count": 2},
        },
        "land_use": {
            "broad": {"complete": True, "network_bytes": 380_000, "id_count": 45},
            "task": {"complete": True, "network_bytes": 145_000, "id_count": 17},
            "hotspot": {"complete": True, "network_bytes": 26_000, "id_count": 3},
        },
        "relations": {
            "task_units_subset_broad": True,
            "library_task_subset_broad": True,
            "land_task_subset_broad": True,
            "land_hotspot_subset_task": True,
        },
    }


def test_offline_comparison_uses_existing_task_context_contract() -> None:
    result = compare_policies(_measurement())

    assert result.r0.context.sufficient
    assert result.r1.context.sufficient
    assert result.rg.context.sufficient
    assert result.r0.context.gap_requirement_ids == ()
    assert result.r1.context.gap_requirement_ids == ()
    assert result.rg.context.gap_requirement_ids == ()
    assert result.rg.context.cost_unit == NETWORK_BYTES
    assert len(result.rg.context.selected_candidate_ids) == 3

    assert result.r0.context.total_acquisition_cost == 454_500
    assert result.r1.context.total_acquisition_cost == 164_100
    assert result.rg.context.total_acquisition_cost == 45_100
    assert result.rg_vs_r1_network_reduction_ratio == pytest.approx(
        1 - 45_100 / 164_100
    )

    assert result.r0.irrelevant_land_use_admission_rate == pytest.approx(42 / 45)
    assert result.r1.irrelevant_land_use_admission_rate == pytest.approx(14 / 17)
    assert result.rg.irrelevant_land_use_admission_rate == 0.0


def test_broad_scope_normalization_requires_measured_containment() -> None:
    measurement = _measurement()
    relations = measurement["relations"]
    assert isinstance(relations, dict)
    relations["library_task_subset_broad"] = False

    with pytest.raises(ValueError, match="library_task_subset_broad"):
        compare_policies(measurement)


def test_population_coverage_fails_closed() -> None:
    measurement = _measurement()
    population = measurement["population"]
    assert isinstance(population, dict)
    task = population["task"]
    assert isinstance(task, dict)
    task["unit_coverage_complete"] = False
    task["missing_unit_count"] = 1

    with pytest.raises(ValueError, match="does not cover every selected base unit"):
        compare_policies(measurement)


def test_population_semantics_are_frozen_before_scoring() -> None:
    measurement = copy.deepcopy(_measurement())
    population = measurement["population"]
    assert isinstance(population, dict)
    task = population["task"]
    assert isinstance(task, dict)
    task["variable"] = "TotalDU"

    with pytest.raises(ValueError, match="differs from frozen experiment input"):
        compare_policies(measurement)


def test_truncated_provider_response_is_not_scored() -> None:
    measurement = _measurement()
    land_use = measurement["land_use"]
    assert isinstance(land_use, dict)
    hotspot = land_use["hotspot"]
    assert isinstance(hotspot, dict)
    hotspot["complete"] = False

    with pytest.raises(ValueError, match="not proven complete"):
        compare_policies(measurement)
