from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
_ROOT = str(ROOT)
sys.path.insert(0, _ROOT)
try:
    from benchmarks.temporal_refinement.experiment_spec import (
        FINE_PERIOD_COUNT,
        PRECIP_PROBABILITY_THRESHOLDS_PERCENT,
        TASK_ACTION_AVAILABLE,
        TASK_WINDOW_COUNT,
        WIND_THRESHOLDS_KMH,
    )
    from benchmarks.temporal_refinement.real_runner import (
        load_pinned_hourly_fixture,
        run_temporal_real_stress,
    )
finally:
    sys.path.remove(_ROOT)


FIXTURE_ROOT = (
    ROOT
    / "benchmarks"
    / "temporal_refinement"
    / "fixtures"
    / "nws_south_mountain_20260818"
)
FIXTURE_PATH = FIXTURE_ROOT / "hourly-reference.json"
RESULT_PATH = FIXTURE_ROOT / "real-result.json"


def test_pinned_hourly_fixture_replays_without_network_access() -> None:
    hourly = load_pinned_hourly_fixture(FIXTURE_PATH)
    document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert len(hourly) == FINE_PERIOD_COUNT
    assert document["normalized_source_documents_committed"] is True
    assert document["original_http_response_bytes_committed"] is False
    assert document["original_http_response_hashes_recorded"] is True
    assert document["points_response_sha256"]
    assert document["hourly_response_sha256"]


def test_every_frozen_temporal_case_preserves_hourly_reference_action() -> None:
    result = run_temporal_real_stress(FIXTURE_PATH)

    assert result.total_cases == (
        TASK_WINDOW_COUNT
        * len(WIND_THRESHOLDS_KMH)
        * len(PRECIP_PROBABILITY_THRESHOLDS_PERCENT)
    )
    assert result.unsafe_stop_count == 0
    assert result.unnecessary_refinement_count == 0
    assert result.coarse_stop_case_count + result.refinement_case_count == result.total_cases
    assert sum(result.final_resolution_counts.values()) == result.total_cases

    for case in result.cases:
        assert not case.unsafe_stop
        assert case.final_action == case.fine_reference_action
        assert case.trace.steps
        assert case.final_resolution_hours == case.trace.steps[-1].resolution_hours


def test_real_temporal_result_freezes_positive_and_countermetrics() -> None:
    result = run_temporal_real_stress(FIXTURE_PATH)
    recorded = json.loads(RESULT_PATH.read_text(encoding="utf-8"))

    assert result.coarse_stop_case_count == 24
    assert result.refinement_case_count == 8
    assert result.final_resolution_counts == {"12": 24, "6": 4, "3": 4}
    assert result.context_payload_reduction_ratio == pytest.approx(2 / 3)

    # Counter-metric: selective refinement is not cheaper for every boundary case.
    assert result.payload_overhead_case_count == 4
    assert result.worst_case_payload_ratio == pytest.approx(28 / 24)

    assert recorded["payload_overhead_case_count"] == result.payload_overhead_case_count
    assert recorded["worst_case_payload_ratio"] == pytest.approx(
        result.worst_case_payload_ratio
    )
    assert recorded["context_payload_reduction_ratio"] == pytest.approx(
        result.context_payload_reduction_ratio
    )


def test_real_refinement_case_identities_are_frozen() -> None:
    result = run_temporal_real_stress(FIXTURE_PATH)

    refined = {
        (
            case.window_index,
            case.wind_threshold_kmh,
            case.precip_threshold_percent,
            case.final_resolution_hours,
        )
        for case in result.cases
        if case.refined
    }
    expected = {
        (1, 10.0, precip, 3)
        for precip in PRECIP_PROBABILITY_THRESHOLDS_PERCENT
    } | {
        (1, 20.0, precip, 6)
        for precip in PRECIP_PROBABILITY_THRESHOLDS_PERCENT
    }
    assert refined == expected


def test_current_real_fixture_does_not_overclaim_negative_action_coverage() -> None:
    result = run_temporal_real_stress(FIXTURE_PATH)

    actions = {case.fine_reference_action for case in result.cases}
    assert actions == {TASK_ACTION_AVAILABLE}

    # The current real stress gate proves coarse-stop/refine behavior and safe
    # agreement with the hourly reference, but it does not prove a real
    # STOP_UNAVAILABLE path. General Core promotion therefore remains a separate
    # review decision rather than an automatic consequence of this boolean gate.
    assert result.cross_domain_stress_gate_pass
