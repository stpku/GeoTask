from __future__ import annotations

from pathlib import Path
import sys


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


def test_real_promotion_gate_is_evidence_not_a_forced_test_expectation() -> None:
    result = run_real_resolution_stress(FIXTURE_ROOT)

    # A scientifically valid negative result must not be converted into a CI
    # failure by asserting that the site necessarily contains both controls.
    assert result.promotion_stress_gate_pass == (
        result.mandatory_stop_control_present
        and result.mandatory_refine_control_present
        and result.unsafe_stop_count == 0
        and result.unnecessary_refinement_count == 0
    )
