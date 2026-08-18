from __future__ import annotations

from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
_ROOT = str(ROOT)
sys.path.insert(0, _ROOT)
try:
    from benchmarks.resolution_stress.envelope_policy import (
        REFINE,
        STOP_BLOCKED,
        STOP_CLEAR,
        aggregate_minmax,
        evaluate_resolution_ladder,
    )
    from benchmarks.resolution_stress.experiment_spec import CorridorRect
finally:
    sys.path.remove(_ROOT)


def _grid(value: float, size: int = 4) -> list[list[float]]:
    return [[value for _ in range(size)] for _ in range(size)]


def test_decision_preserving_coarse_context_stops_without_finest_data() -> None:
    fine = _grid(100.0)
    corridor = CorridorRect("west_strip", 0, 0, 1, 4)

    trace = evaluate_resolution_ladder(
        fine,
        corridor=corridor,
        threshold_meters=150.0,
        resolution_ladder_meters=(4, 2, 1),
    )

    assert trace.final_action == STOP_CLEAR
    assert trace.final_resolution_meters == 4
    assert not trace.refined
    assert len(trace.steps) == 1
    assert trace.steps[0].minimum_margin_to_threshold == 50.0


def test_uniform_high_context_can_also_stop_coarse_as_blocked() -> None:
    fine = _grid(200.0)
    corridor = CorridorRect("west_strip", 0, 0, 1, 4)

    trace = evaluate_resolution_ladder(
        fine,
        corridor=corridor,
        threshold_meters=150.0,
        resolution_ladder_meters=(4, 2, 1),
    )

    assert trace.final_action == STOP_BLOCKED
    assert trace.final_resolution_meters == 4
    assert not trace.refined


def test_off_corridor_high_terrain_forces_refine_but_not_false_block() -> None:
    fine = _grid(100.0)
    # This high fine cell is outside the 1 m-wide west corridor. At 4 m the
    # entire source block intersects the corridor and is therefore ambiguous;
    # at 2 m the high cell belongs to a different block and the corridor clears.
    fine[1][3] = 200.0
    corridor = CorridorRect("west_strip", 0, 0, 1, 4)

    trace = evaluate_resolution_ladder(
        fine,
        corridor=corridor,
        threshold_meters=150.0,
        resolution_ladder_meters=(4, 2, 1),
    )

    assert [step.action for step in trace.steps] == [REFINE, STOP_CLEAR]
    assert trace.final_resolution_meters == 2
    assert trace.refined
    assert trace.steps[0].ambiguous_cell_count == 1
    assert trace.steps[1].ambiguous_cell_count == 0


def test_true_corridor_high_terrain_refines_until_blockage_is_proven() -> None:
    fine = _grid(100.0)
    fine[1][0] = 200.0
    corridor = CorridorRect("west_strip", 0, 0, 1, 4)

    trace = evaluate_resolution_ladder(
        fine,
        corridor=corridor,
        threshold_meters=150.0,
        resolution_ladder_meters=(4, 2, 1),
    )

    assert [step.action for step in trace.steps] == [REFINE, REFINE, STOP_BLOCKED]
    assert trace.final_resolution_meters == 1


def test_aggregation_preserves_exact_min_max_not_mean() -> None:
    fine = [
        [100.0, 100.0, 100.0, 100.0],
        [100.0, 200.0, 100.0, 100.0],
        [100.0, 100.0, 90.0, 100.0],
        [100.0, 100.0, 100.0, 100.0],
    ]

    coarse = aggregate_minmax(fine, resolution_meters=2)

    assert coarse[0][0].minimum == 100.0
    assert coarse[0][0].maximum == 200.0
    assert coarse[1][1].minimum == 90.0
    assert coarse[1][1].maximum == 100.0


def test_ladder_must_end_at_fine_reference() -> None:
    fine = _grid(100.0)
    corridor = CorridorRect("west_strip", 0, 0, 1, 4)

    with pytest.raises(ValueError, match="end at the fine reference"):
        evaluate_resolution_ladder(
            fine,
            corridor=corridor,
            threshold_meters=150.0,
            resolution_ladder_meters=(4, 2),
        )
