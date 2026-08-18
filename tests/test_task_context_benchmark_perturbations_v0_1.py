from dataclasses import replace
from pathlib import Path
import sys

import pytest

from geotask_core.task_context import ContextCandidate

# ``benchmarks`` remains repository-local rather than part of geotask-core.
_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, _ROOT)
try:
    from benchmarks.task_context_cases_v0_1 import COST_UNIT, low_altitude_mission_case
    from benchmarks.task_context_v0_1 import (
        POLICY_DECLARED_MIN_COST,
        POLICY_FULL_CONTEXT,
        run_case,
    )
finally:
    sys.path.remove(_ROOT)


def _by_policy(case):
    return {result.policy: result for result in run_case(case)}


def test_irrelevant_context_expansion_does_not_change_g0_selection_or_cost():
    base = low_altitude_mission_case()
    base_g0 = _by_policy(base)[POLICY_DECLARED_MIN_COST]

    extra_poi = tuple(
        ContextCandidate(
            candidate_id=f"poi-extra-{index:03d}",
            source="fictional-poi-expansion",
            requirement_ids=("poi_labels",),
            spatial_scope="corridor-a-b",
            acquisition_cost=0.2,
            cost_unit=COST_UNIT,
        )
        for index in range(50)
    )
    expanded = replace(base, candidates=base.candidates + extra_poi)
    results = _by_policy(expanded)
    expanded_g0 = results[POLICY_DECLARED_MIN_COST]
    expanded_full = results[POLICY_FULL_CONTEXT]

    assert expanded_g0.selected_candidate_ids == base_g0.selected_candidate_ids
    assert expanded_g0.context_preparation_cost == base_g0.context_preparation_cost
    assert expanded_g0.critical_context_miss_rate == 0.0
    assert expanded_g0.gap_requirement_ids == ("poi_labels",)

    # Full-context cost grows with irrelevant context; G0 cost does not.
    assert expanded_full.context_preparation_cost > 19.0
    assert expanded_g0.context_reduction_ratio_items > base_g0.context_reduction_ratio_items


def test_missing_fine_obstacle_context_exposes_critical_gap():
    base = low_altitude_mission_case()
    reduced = replace(
        base,
        candidates=tuple(
            candidate
            for candidate in base.candidates
            if candidate.candidate_id != "obstacles-10m"
        ),
    )

    g0 = _by_policy(reduced)[POLICY_DECLARED_MIN_COST]

    assert g0.context_status == "insufficient"
    assert g0.critical_context_miss_rate == pytest.approx(1 / 3)
    assert "obstacles" in g0.gap_requirement_ids
    # G0 selects only usable candidates; the remaining 100 m obstacle item is
    # intentionally not selected. The Core-level demo separately proves that a
    # selected-but-too-coarse candidate creates a refinement requirement.
    assert g0.refinement_requirement_ids == ()


def test_wrong_scope_weather_cannot_be_promoted_to_current_task():
    base = low_altitude_mission_case()
    shifted_candidates = tuple(
        replace(candidate, spatial_scope="corridor-c-d")
        if candidate.candidate_id.startswith("weather-")
        else candidate
        for candidate in base.candidates
    )
    shifted = replace(base, candidates=shifted_candidates)

    g0 = _by_policy(shifted)[POLICY_DECLARED_MIN_COST]

    assert g0.context_status == "insufficient"
    assert g0.critical_context_miss_rate == pytest.approx(1 / 3)
    assert "weather" in g0.gap_requirement_ids
    assert all(
        not candidate_id.startswith("weather-")
        for candidate_id in g0.selected_candidate_ids
    )


def test_information_can_be_sufficient_while_selected_context_is_over_budget():
    base = low_altitude_mission_case()
    expensive_candidates = tuple(
        replace(candidate, acquisition_cost=9.0)
        if candidate.candidate_id == "obstacles-10m"
        else candidate
        for candidate in base.candidates
    )
    expensive = replace(base, candidates=expensive_candidates)

    g0 = _by_policy(expensive)[POLICY_DECLARED_MIN_COST]

    assert g0.context_status == "over_budget"
    assert g0.critical_context_miss_rate == 0.0
    assert g0.context_preparation_cost == 12.0
    assert g0.gap_requirement_ids == ("poi_labels",)
