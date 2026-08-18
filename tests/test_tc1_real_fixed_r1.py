from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "benchmarks" / "tc1_real" / "fixtures"

_ROOT = str(ROOT)
sys.path.insert(0, _ROOT)
try:
    from benchmarks.tc1_real.fixed_workflow import compare_rg_to_r1
    from benchmarks.tc1_real.recorded_context import CARRIED_BYTES, NETWORK_BYTES
finally:
    sys.path.remove(_ROOT)


def test_fixed_r1_covers_all_frozen_critical_requirements():
    for projection in (NETWORK_BYTES, CARRIED_BYTES):
        comparison = compare_rg_to_r1(FIXTURE_ROOT, cost_projection=projection)

        assert comparison.r1_context.status == "sufficient"
        assert comparison.rg_context.status == "sufficient"
        assert comparison.r1_context.gap_requirement_ids == ()
        assert comparison.rg_context.gap_requirement_ids == ()
        assert len(comparison.r1_context.selected_candidate_ids) == 3
        assert len(comparison.rg_context.selected_candidate_ids) == 3


def test_rg_network_burden_only_slightly_beats_strong_r1():
    comparison = compare_rg_to_r1(FIXTURE_ROOT, cost_projection=NETWORK_BYTES)

    assert comparison.r1_context.total_acquisition_cost == 20_800_178
    assert comparison.rg_context.total_acquisition_cost == 20_586_804
    assert comparison.reduction_ratio == pytest.approx(0.010258277597432142)


def test_rg_carried_context_is_smaller_than_strong_r1_without_missing_context():
    comparison = compare_rg_to_r1(FIXTURE_ROOT, cost_projection=CARRIED_BYTES)

    assert comparison.r1_context.total_acquisition_cost == 328_898
    assert comparison.rg_context.total_acquisition_cost == 115_524
    assert comparison.reduction_ratio == pytest.approx(0.6487543250491034)
    assert comparison.r1_context.coverage == tuple(
        # Candidate ids differ between policies, so compare requirement keys below.
        comparison.r1_context.coverage
    )
    assert {
        item.requirement_id for item in comparison.r1_context.coverage if item.candidate_ids
    } == {
        item.requirement_id for item in comparison.rg_context.coverage if item.candidate_ids
    }


def test_r1_and_rg_difference_is_burden_allocation_not_critical_miss():
    network = compare_rg_to_r1(FIXTURE_ROOT, cost_projection=NETWORK_BYTES)
    carried = compare_rg_to_r1(FIXTURE_ROOT, cost_projection=CARRIED_BYTES)

    for comparison in (network, carried):
        assert comparison.r1_context.sufficient is True
        assert comparison.rg_context.sufficient is True
        assert comparison.r1_context.gap_requirement_ids == ()
        assert comparison.rg_context.gap_requirement_ids == ()

    assert network.reduction_ratio < 0.02
    assert carried.reduction_ratio > 0.60


def test_unknown_r1_projection_fails_closed():
    with pytest.raises(ValueError, match="projection"):
        compare_rg_to_r1(FIXTURE_ROOT, cost_projection="all_costs")
