from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
_ROOT = str(ROOT)
sys.path.insert(0, _ROOT)
try:
    from benchmarks.temporal_refinement.envelope_policy import (
        HourlyWeather,
        evaluate_temporal_refinement,
    )
    from benchmarks.temporal_refinement.experiment_spec import (
        TASK_ACTION_AVAILABLE,
        TASK_ACTION_UNAVAILABLE,
    )
finally:
    sys.path.remove(_ROOT)


LADDER = (12, 6, 3, 1)


def _hour(wind: float, pop: float) -> HourlyWeather:
    return HourlyWeather(wind_kmh=wind, precip_probability_percent=pop)


def test_uniform_good_window_stops_at_12_hours() -> None:
    hourly = [_hour(8, 5) for _ in range(12)]
    trace = evaluate_temporal_refinement(
        hourly,
        wind_threshold_kmh=10,
        precip_threshold_percent=10,
        ladder_hours=LADDER,
    )

    assert trace.final_action == TASK_ACTION_AVAILABLE
    assert trace.final_resolution_hours == 12
    assert not trace.refined
    assert trace.evaluated_block_count == 1
    assert trace.payload_float_count == 4
    assert trace.always_hourly_payload_float_count == 24


def test_uniform_bad_wind_window_stops_at_12_hours_unavailable() -> None:
    hourly = [_hour(25, 0) for _ in range(12)]
    trace = evaluate_temporal_refinement(
        hourly,
        wind_threshold_kmh=20,
        precip_threshold_percent=70,
        ladder_hours=LADDER,
    )

    assert trace.final_action == TASK_ACTION_UNAVAILABLE
    assert trace.final_resolution_hours == 12
    assert not trace.refined


def test_mixed_coarse_block_refines_and_finds_available_half() -> None:
    hourly = (
        [_hour(25, 5) for _ in range(6)]
        + [_hour(8, 5) for _ in range(6)]
    )
    trace = evaluate_temporal_refinement(
        hourly,
        wind_threshold_kmh=20,
        precip_threshold_percent=10,
        ladder_hours=LADDER,
    )

    assert [step.action for step in trace.steps] == ["REFINE", TASK_ACTION_AVAILABLE]
    assert trace.final_resolution_hours == 6
    assert trace.refined
    assert trace.evaluated_block_count == 3


def test_correlation_ambiguity_can_require_one_hour_resolution() -> None:
    # Every 3h block has low-wind and low-precip hours, but never in the same
    # hour except the final hour. Separate min/max envelopes therefore remain
    # conservative and ambiguous until the exact hourly correlation is visible.
    pattern = [
        _hour(8, 80),
        _hour(30, 5),
        _hour(8, 80),
    ]
    hourly = pattern * 3 + [_hour(8, 80), _hour(30, 5), _hour(8, 5)]
    trace = evaluate_temporal_refinement(
        hourly,
        wind_threshold_kmh=20,
        precip_threshold_percent=30,
        ladder_hours=LADDER,
    )

    assert trace.final_action == TASK_ACTION_AVAILABLE
    assert trace.final_resolution_hours == 1
    assert trace.refined
    assert [step.action for step in trace.steps] == [
        "REFINE",
        "REFINE",
        "REFINE",
        TASK_ACTION_AVAILABLE,
    ]


def test_all_hours_fail_for_different_reasons_resolves_unavailable_at_one_hour() -> None:
    # Coarse extrema cannot prove a common failure criterion, but hourly context
    # proves that every slot violates at least one criterion.
    hourly = [
        _hour(8, 80) if index % 2 == 0 else _hour(30, 5)
        for index in range(12)
    ]
    trace = evaluate_temporal_refinement(
        hourly,
        wind_threshold_kmh=20,
        precip_threshold_percent=30,
        ladder_hours=LADDER,
    )

    assert trace.final_action == TASK_ACTION_UNAVAILABLE
    assert trace.final_resolution_hours == 1
    assert trace.refined
    assert trace.steps[-1].ambiguous_block_count == 0
