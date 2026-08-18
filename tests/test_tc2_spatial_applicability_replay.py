from __future__ import annotations

import json
from pathlib import Path

import pytest

from geotask_core.spatial_scope import rect_contains_rect, rect_intersects_rect

from benchmarks.tc1_real.recorded_context import (
    CARRIED_BYTES,
    assess_recorded_m1,
)
from benchmarks.tc1_real.spatial_planning.experiment_spec import (
    HOTSPOT_BBOX,
    R0_BROAD_BBOX,
    TASK_BBOX,
)
from benchmarks.tc1_real.spatial_planning.recorded_context import (
    compare_task_scoped_policies,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "benchmarks" / "tc1_real" / "fixtures"


def _json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _bbox(value: object) -> tuple[float, float, float, float]:
    assert isinstance(value, list) and len(value) == 4
    return tuple(float(item) for item in value)  # type: ignore[return-value]


def _planning_measurement() -> dict[str, object]:
    root = FIXTURE_ROOT / "planning_phx_20260818"
    spatial = _json(root / "spatial-measurement.json")
    population = _json(root / "population-task-measurement.json")
    population_map = population["population"]
    assert isinstance(population_map, dict)
    spatial["population"] = population_map
    return spatial


def test_low_altitude_m1_broad_scope_relation_is_now_core_computable() -> None:
    task = _json(FIXTURE_ROOT / "uasfm_phx_20260818" / "summary.json")
    broad = _json(
        FIXTURE_ROOT / "uasfm_phx_r0_regional_20260818" / "summary.json"
    )
    task_bbox = _bbox(task["bbox"])
    broad_bbox = _bbox(broad["bbox"])

    assert rect_contains_rect(broad_bbox, task_bbox)
    assert rect_intersects_rect(broad_bbox, task_bbox)
    assert not rect_contains_rect(task_bbox, broad_bbox)

    replay = assess_recorded_m1(FIXTURE_ROOT, cost_projection=CARRIED_BYTES)
    assert replay.r0.context.sufficient
    assert replay.rg.context.sufficient
    assert replay.r0.context.gap_requirement_ids == ()
    assert replay.rg.context.gap_requirement_ids == ()
    # Existing recorded-context contract: operator promotion must not change it.
    assert replay.r0.context.total_acquisition_cost == 99_122_202
    assert replay.rg.context.total_acquisition_cost == 115_524
    assert replay.reduction_ratio == pytest.approx(0.9988345295234664)


def test_spatial_planning_scope_hierarchy_is_now_core_computable() -> None:
    assert rect_contains_rect(R0_BROAD_BBOX, TASK_BBOX)
    assert rect_contains_rect(TASK_BBOX, HOTSPOT_BBOX)
    assert rect_contains_rect(R0_BROAD_BBOX, HOTSPOT_BBOX)
    assert rect_intersects_rect(TASK_BBOX, HOTSPOT_BBOX)
    assert not rect_contains_rect(HOTSPOT_BBOX, TASK_BBOX)

    replay = compare_task_scoped_policies(_planning_measurement())
    assert replay.r1.context.sufficient
    assert replay.rg.context.sufficient
    assert replay.r1.context.gap_requirement_ids == ()
    assert replay.rg.context.gap_requirement_ids == ()
    # Frozen planning result: operator promotion must not change it.
    assert replay.r1.context.total_acquisition_cost == 171_036
    assert replay.rg.context.total_acquisition_cost == 51_313
    assert replay.rg_vs_r1_network_reduction_ratio == pytest.approx(
        1 - 51_313 / 171_036
    )
