from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "benchmarks" / "tc1_real" / "fixtures"

_ROOT = str(ROOT)
sys.path.insert(0, _ROOT)
try:
    from benchmarks.tc1_real.recorded_context import (
        CARRIED_BYTES,
        NETWORK_BYTES,
        assess_recorded_m1,
    )
finally:
    sys.path.remove(_ROOT)


def test_recorded_m1_is_informationally_sufficient_in_both_cost_views():
    network = assess_recorded_m1(FIXTURE_ROOT, cost_projection=NETWORK_BYTES)
    carried = assess_recorded_m1(FIXTURE_ROOT, cost_projection=CARRIED_BYTES)

    for comparison in (network, carried):
        assert comparison.rg.context.status == "sufficient"
        assert comparison.r0.context.status == "sufficient"
        assert comparison.rg.context.gap_requirement_ids == ()
        assert comparison.r0.context.gap_requirement_ids == ()
        assert len(comparison.rg.candidate_ids) == 3
        assert len(comparison.r0.candidate_ids) == 3
        # One HRRR payload explicitly covers both frozen weather requirements.
        coverage = {
            item.requirement_id: item.candidate_ids
            for item in comparison.rg.context.coverage
        }
        assert coverage["airspace_guidance"] == ("rg-uasfm-airspace",)
        assert coverage["obstacle_context"] == ("rg-ddof-obstacles",)
        assert coverage["weather_wind"] == ("rg-hrrr-weather",)
        assert coverage["weather_visibility"] == ("rg-hrrr-weather",)


def test_network_byte_projection_shows_ddof_dominates_total_acquisition():
    comparison = assess_recorded_m1(FIXTURE_ROOT, cost_projection=NETWORK_BYTES)

    assert comparison.rg.context.cost_unit == NETWORK_BYTES
    assert comparison.r0.context.cost_unit == NETWORK_BYTES
    assert comparison.rg.context.total_acquisition_cost == 20_586_804
    assert comparison.r0.context.total_acquisition_cost == 20_800_178
    assert comparison.reduction_ratio == pytest.approx(0.010258277597432142)


def test_carried_byte_projection_shows_large_downstream_context_reduction():
    comparison = assess_recorded_m1(FIXTURE_ROOT, cost_projection=CARRIED_BYTES)

    assert comparison.rg.context.cost_unit == CARRIED_BYTES
    assert comparison.r0.context.cost_unit == CARRIED_BYTES
    assert comparison.rg.context.total_acquisition_cost == 115_524
    assert comparison.r0.context.total_acquisition_cost == 99_122_202
    assert comparison.reduction_ratio == pytest.approx(0.9988345295234664)


def test_cost_projection_changes_burden_not_context_coverage():
    network = assess_recorded_m1(FIXTURE_ROOT, cost_projection=NETWORK_BYTES)
    carried = assess_recorded_m1(FIXTURE_ROOT, cost_projection=CARRIED_BYTES)

    assert network.rg.context.selected_candidate_ids == carried.rg.context.selected_candidate_ids
    assert network.r0.context.selected_candidate_ids == carried.r0.context.selected_candidate_ids
    assert network.rg.context.coverage == carried.rg.context.coverage
    assert network.r0.context.coverage == carried.r0.context.coverage
    assert network.rg.context.total_acquisition_cost != carried.rg.context.total_acquisition_cost
    assert network.reduction_ratio != carried.reduction_ratio


def test_unknown_cost_projection_fails_closed():
    with pytest.raises(ValueError, match="cost_projection"):
        assess_recorded_m1(FIXTURE_ROOT, cost_projection="universal_cost")
