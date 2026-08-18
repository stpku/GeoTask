from __future__ import annotations

from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
_ROOT = str(ROOT)
sys.path.insert(0, _ROOT)
try:
    from benchmarks.resolution_stress.experiment_spec import (
        CORRIDORS,
        ELEVATION_THRESHOLDS_METERS,
        FINE_GRID_HEIGHT,
        FINE_GRID_WIDTH,
    )
    from benchmarks.resolution_stress.real_runner import (
        load_pinned_fine_grid,
        run_real_resolution_stress,
    )
finally:
    sys.path.remove(_ROOT)


FIXTURE_ROOT = (
    ROOT
    / "benchmarks"
    / "resolution_stress"
    / "fixtures"
    / "usgs_3dep_south_mountain_20260818"
)


def test_pinned_fine_grid_replays_without_raster_dependencies() -> None:
    grid = load_pinned_fine_grid(FIXTURE_ROOT)

    assert len(grid) == FINE_GRID_HEIGHT
    assert len(grid[0]) == FINE_GRID_WIDTH
    values = [value for row in grid for value in row]
    assert min(values) > 0
    assert max(values) > min(values)


def test_every_frozen_real_case_preserves_fine_reference_action_when_stopping() -> None:
    result = run_real_resolution_stress(FIXTURE_ROOT)

    assert result.total_cases == len(CORRIDORS) * len(ELEVATION_THRESHOLDS_METERS)
    assert result.unsafe_stop_count == 0
    assert result.unnecessary_refinement_count == 0
    assert result.coarse_stop_case_count + result.refinement_case_count == result.total_cases
    assert sum(result.final_resolution_counts.values()) == result.total_cases

    for case in result.cases:
        assert not case.unsafe_stop
        assert case.final_action == case.fine_reference_action
        assert case.steps
        assert case.final_resolution_meters == case.steps[-1].resolution_meters


def test_real_stress_result_is_frozen_after_predeclared_inputs() -> None:
    result = run_real_resolution_stress(FIXTURE_ROOT)

    assert result.total_cases == 48
    assert result.coarse_stop_case_count == 45
    assert result.refinement_case_count == 3
    assert result.final_resolution_counts == {"32": 45, "16": 2, "8": 1}
    assert result.unsafe_stop_count == 0
    assert result.unnecessary_refinement_count == 0
    assert result.mandatory_stop_control_present
    assert result.mandatory_refine_control_present
    assert result.promotion_stress_gate_pass

    assert result.adaptive_context_cells_carried == 1_624
    assert result.always_finest_context_cells_carried == 86_016
    assert result.context_cell_reduction_ratio == pytest.approx(
        0.9811197916666666
    )
    assert result.adaptive_context_payload_bytes == 12_992
    assert result.always_finest_context_payload_bytes == 344_064
    assert result.context_payload_reduction_ratio == pytest.approx(
        0.9622395833333334
    )
    assert result.fine_reference_cell_count == 262_144
    assert result.pyramid_build_reference_cell_reads == 1_310_720
    assert result.pyramid_build_is_shared_reference_cost
    assert result.context_reduction_excludes_pyramid_build_cost

    refined_cases = {
        (
            case.corridor_id,
            case.threshold_meters,
            case.final_resolution_meters,
            case.final_action,
        )
        for case in result.cases
        if case.refined
    }
    assert refined_cases == {
        ("vertical_center", 600.0, 16, "STOP_BLOCKED"),
        ("vertical_west", 600.0, 16, "STOP_BLOCKED"),
        ("horizontal_north", 550.0, 8, "STOP_CLEAR"),
    }


def test_real_promotion_gate_is_evidence_not_a_forced_test_expectation() -> None:
    result = run_real_resolution_stress(FIXTURE_ROOT)

    # A scientifically valid negative result must not be converted into a CI
    # failure by asserting that every future site necessarily contains both
    # controls. This fixture is now frozen because its inputs were predeclared.
    assert result.promotion_stress_gate_pass == (
        result.mandatory_stop_control_present
        and result.mandatory_refine_control_present
        and result.unsafe_stop_count == 0
        and result.unnecessary_refinement_count == 0
    )
