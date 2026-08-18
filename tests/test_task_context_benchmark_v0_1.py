from pathlib import Path
import sys

import pytest

# ``benchmarks`` is intentionally repository-local and not part of the
# geotask-core distribution. Import it only for this test module without
# widening the global pytest pythonpath.
_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, _ROOT)
try:
    from benchmarks.task_context_cases_v0_1 import (
        low_altitude_mission_case,
        spatial_planning_case,
    )
    from benchmarks.task_context_v0_1 import (
        POLICY_DECLARED_MIN_COST,
        POLICY_FULL_CONTEXT,
        POLICY_MANUAL_TEMPLATE,
        run_case,
    )
finally:
    sys.path.remove(_ROOT)


def _by_policy(case):
    return {result.policy: result for result in run_case(case)}


def test_low_altitude_tc1_cost_miss_tradeoff():
    results = _by_policy(low_altitude_mission_case())

    full = results[POLICY_FULL_CONTEXT]
    manual = results[POLICY_MANUAL_TEMPLATE]
    geotask = results[POLICY_DECLARED_MIN_COST]

    assert full.context_status == "over_budget"
    assert full.critical_context_miss_rate == 0.0
    assert full.context_preparation_cost == 19.0
    assert full.context_reduction_ratio_items == 0.0
    assert full.gap_requirement_ids == ()

    assert manual.context_status == "insufficient"
    assert manual.critical_context_miss_rate == pytest.approx(1 / 3)
    assert manual.context_preparation_cost == 6.0
    assert manual.context_reduction_ratio_items == pytest.approx(2 / 6)
    assert manual.gap_requirement_ids == ("obstacles",)
    assert manual.refinement_requirement_ids == ("obstacles",)

    assert geotask.context_status == "sufficient_with_gaps"
    assert geotask.critical_context_miss_rate == 0.0
    assert geotask.context_preparation_cost == 8.0
    assert geotask.context_reduction_ratio_items == pytest.approx(3 / 6)
    assert geotask.gap_requirement_ids == ("poi_labels",)
    assert geotask.selected_candidate_ids == (
        "airspace-notice",
        "obstacles-10m",
        "weather-500m",
    )
    assert geotask.task_outcome_regret is None


def test_spatial_planning_tc1_uses_coarse_district_and_local_refinement():
    results = _by_policy(spatial_planning_case())

    full = results[POLICY_FULL_CONTEXT]
    manual = results[POLICY_MANUAL_TEMPLATE]
    geotask = results[POLICY_DECLARED_MIN_COST]

    assert full.context_status == "over_budget"
    assert full.critical_context_miss_rate == 0.0
    assert full.context_preparation_cost == 38.0
    assert full.gap_requirement_ids == ()

    assert manual.context_status == "insufficient"
    assert manual.critical_context_miss_rate == pytest.approx(1 / 3)
    assert manual.context_preparation_cost == 6.0
    assert manual.gap_requirement_ids == ("hotspot_building_demand",)
    # No hotspot candidate was selected by the fixed template, so this is a
    # missing-context gap rather than a selected-but-too-coarse refinement.
    assert manual.refinement_requirement_ids == ()

    assert geotask.context_status == "sufficient_with_gaps"
    assert geotask.critical_context_miss_rate == 0.0
    assert geotask.context_preparation_cost == 8.0
    assert geotask.context_reduction_ratio_items == pytest.approx(4 / 7)
    assert geotask.gap_requirement_ids == ("poi_labels",)
    assert geotask.selected_candidate_ids == (
        "capacity-1km",
        "demand-1km",
        "hotspot-buildings-100m",
    )
    assert "demand-100m" not in geotask.selected_candidate_ids
    assert "capacity-100m" not in geotask.selected_candidate_ids
    assert "district-buildings-10m" not in geotask.selected_candidate_ids


def test_tc1_policy_does_not_select_noncritical_context_by_default():
    for case in (low_altitude_mission_case(), spatial_planning_case()):
        result = _by_policy(case)[POLICY_DECLARED_MIN_COST]
        assert all("poi" not in candidate_id for candidate_id in result.selected_candidate_ids)


def test_synthetic_tc1_never_claims_task_outcome_regret():
    for case in (low_altitude_mission_case(), spatial_planning_case()):
        for result in run_case(case):
            assert result.task_outcome_regret is None
