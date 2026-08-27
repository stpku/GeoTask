from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmarks.tc1_real.spatial_planning.provider_truncation_proof import (
    analyze_provider_truncation_evidence,
)


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "benchmarks"
    / "tc1_real"
    / "fixtures"
    / "planning_phx_20260818"
    / "provider-truncation-evidence.json"
)


def _fixture() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_recorded_provider_truncation_rejects_attractive_naive_reduction() -> None:
    result = analyze_provider_truncation_evidence(_fixture())

    # A naive comparison would advertise roughly a 45.66% smaller task response.
    assert result.naive_task_vs_broad_byte_reduction_ratio == pytest.approx(
        0.4565958370713049
    )

    # But both ordinary responses hit the same 2,000-record ceiling, and the
    # later IDs-first retrieval proved 118,190 complete broad features.
    assert result.both_single_queries_hit_observed_ceiling
    assert result.complete_broad_exceeds_single_query
    assert result.naive_broad_return_fraction_of_complete == pytest.approx(
        0.016921905406548778
    )
    assert result.naive_broad_undercount_ratio == pytest.approx(
        0.9830780945934512
    )

    assert not result.reduction_scoreable
    assert result.verdict == "REJECT_NAIVE_REDUCTION_PROVIDER_TRUNCATED"


def test_reduction_remains_fail_closed_when_only_one_truncation_signal_is_present() -> None:
    evidence = _fixture()
    ordinary = evidence["ordinary_single_query"]
    assert isinstance(ordinary, dict)
    task = ordinary["task"]
    assert isinstance(task, dict)

    # Even if the task response does not exactly hit the observed ceiling, the
    # later complete broad cardinality still contradicts the ordinary broad
    # response and must keep the reduction non-scoreable.
    task["feature_count"] = 1500
    result = analyze_provider_truncation_evidence(evidence)

    assert not result.both_single_queries_hit_observed_ceiling
    assert result.complete_broad_exceeds_single_query
    assert not result.reduction_scoreable


def test_explicitly_incomplete_ids_first_evidence_is_rejected() -> None:
    evidence = _fixture()
    complete = evidence["ids_first_complete_broad"]
    assert isinstance(complete, dict)
    complete["complete"] = False

    with pytest.raises(ValueError, match="explicitly prove completeness"):
        analyze_provider_truncation_evidence(evidence)
