from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "benchmarks" / "tc1_real" / "fixtures"

_ROOT = str(ROOT)
sys.path.insert(0, _ROOT)
try:
    from benchmarks.tc1_real.temporal_applicability import (
        CARRIED_BYTES,
        M3_CONTROL_VALID_TIME,
        M3_MISMATCH_VALID_TIME,
        M3_WINDOW_END,
        M3_WINDOW_START,
        NETWORK_BYTES,
        TemporalWindow,
        assess_recorded_m3,
        evaluate_temporal_applicability,
    )
finally:
    sys.path.remove(_ROOT)


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_m3_real_hrrr_pair_holds_non_temporal_request_dimensions_constant():
    control = _load(
        FIXTURE_ROOT / "hrrr_phx_20260818" / "hrrr-task.record.json"
    )
    mismatch = _load(
        FIXTURE_ROOT
        / "hrrr_phx_m3_wrong_time_20260818"
        / "hrrr-m3-wrong-time.record.json"
    )

    control_provenance = control["provenance"]
    mismatch_provenance = mismatch["provenance"]
    control_params = control_provenance["request_parameters"]
    mismatch_params = mismatch_provenance["request_parameters"]

    assert control_provenance["source_id"] == "noaa-hrrr"
    assert mismatch_provenance["source_id"] == "noaa-hrrr"
    assert control_provenance["source_effective_at"] == "2026-08-18T06:00:00Z"
    assert mismatch_provenance["source_effective_at"] == "2026-08-18T06:00:00Z"
    assert control_params["bbox"] == mismatch_params["bbox"]
    assert control_params["variables"] == mismatch_params["variables"]
    assert control_params["levels"] == mismatch_params["levels"]
    assert control_params["cycle_utc"] == mismatch_params["cycle_utc"] == 6
    assert control_params["date"] == mismatch_params["date"] == "20260818"

    assert control_params["forecast_hour"] == 4
    assert mismatch_params["forecast_hour"] == 2
    assert control_provenance["valid_from"] == M3_CONTROL_VALID_TIME
    assert mismatch_provenance["valid_from"] == M3_MISMATCH_VALID_TIME
    assert control_provenance["content_sha256"] != mismatch_provenance["content_sha256"]


def test_m3_window_uses_explicit_half_open_boundary():
    window = TemporalWindow(M3_WINDOW_START, M3_WINDOW_END)

    assert window.contains_instant("2026-08-18T10:00:00Z") is True
    assert window.contains_instant("2026-08-18T10:59:59Z") is True
    assert window.contains_instant("2026-08-18T11:00:00Z") is False
    assert window.contains_instant("2026-08-18T08:00:00Z") is False


def test_recorded_m3_real_wrong_valid_time_gaps_only_weather_requirements():
    for projection in (NETWORK_BYTES, CARRIED_BYTES):
        comparison = assess_recorded_m3(
            FIXTURE_ROOT,
            cost_projection=projection,
        )

        assert comparison.control.context.status == "sufficient"
        assert comparison.control.context.gap_requirement_ids == ()
        assert comparison.control.applicability.applicable is True
        assert comparison.control.weather_candidate.temporal_scope == (
            "recorded-experiment-window"
        )

        assert comparison.mismatch.context.status == "insufficient"
        assert set(comparison.mismatch.context.gap_requirement_ids) == {
            "weather_wind",
            "weather_visibility",
        }
        assert comparison.mismatch.applicability.applicable is False
        assert comparison.mismatch.applicability.reason == (
            "validity_before_task_window"
        )
        assert comparison.mismatch.weather_candidate.temporal_scope.startswith(
            "outside-task-window:"
        )
        assert {
            assessment.requirement_id
            for assessment in comparison.mismatch.weather_assessments
        } == {"weather_wind", "weather_visibility"}
        assert all(
            assessment.reasons == ("temporal_scope_mismatch",)
            for assessment in comparison.mismatch.weather_assessments
        )

        control_coverage = {
            item.requirement_id: item.candidate_ids
            for item in comparison.control.context.coverage
        }
        mismatch_coverage = {
            item.requirement_id: item.candidate_ids
            for item in comparison.mismatch.context.coverage
        }
        assert control_coverage["airspace_guidance"] == mismatch_coverage[
            "airspace_guidance"
        ]
        assert control_coverage["obstacle_context"] == mismatch_coverage[
            "obstacle_context"
        ]
        assert mismatch_coverage["weather_wind"] == ()
        assert mismatch_coverage["weather_visibility"] == ()


def test_temporal_applicability_fails_closed_on_missing_or_naive_validity():
    control = _load(
        FIXTURE_ROOT / "hrrr_phx_20260818" / "hrrr-task.record.json"
    )
    window = TemporalWindow(M3_WINDOW_START, M3_WINDOW_END)

    missing = deepcopy(control)
    del missing["provenance"]["valid_from"]
    with pytest.raises(ValueError, match="valid_from"):
        evaluate_temporal_applicability(missing, window=window)

    naive = deepcopy(control)
    naive["provenance"]["valid_from"] = "2026-08-18T10:00:00"
    naive["provenance"]["valid_until"] = "2026-08-18T10:00:00"
    with pytest.raises(ValueError, match="timezone"):
        evaluate_temporal_applicability(naive, window=window)


def test_invalid_temporal_window_is_rejected():
    with pytest.raises(ValueError, match="start must be before end"):
        TemporalWindow("2026-08-18T11:00:00Z", "2026-08-18T10:00:00Z")
