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
    from benchmarks.tc1_real.semantic_breadth import (
        CARRIED_BYTES,
        NETWORK_BYTES,
        _verify_comparable_records,
        assess_recorded_m4,
    )
finally:
    sys.path.remove(_ROOT)


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_m4_real_pair_changes_semantic_breadth_not_space_or_time():
    narrow = _load(
        FIXTURE_ROOT / "hrrr_phx_20260818" / "hrrr-task.record.json"
    )
    broad = _load(
        FIXTURE_ROOT
        / "hrrr_phx_m4_broad_20260818"
        / "hrrr-m4-broad-weather.record.json"
    )

    narrow_prov = narrow["provenance"]
    broad_prov = broad["provenance"]
    narrow_params = narrow_prov["request_parameters"]
    broad_params = broad_prov["request_parameters"]

    assert narrow_prov["source_id"] == broad_prov["source_id"] == "noaa-hrrr"
    assert narrow_prov["source_effective_at"] == broad_prov["source_effective_at"]
    assert narrow_prov["valid_from"] == broad_prov["valid_from"]
    assert narrow_prov["valid_until"] == broad_prov["valid_until"]
    for key in ("date", "cycle_utc", "forecast_hour", "bbox"):
        assert narrow_params[key] == broad_params[key]

    assert set(narrow_params["variables"]) == {"UGRD", "VGRD", "VIS"}
    assert set(narrow_params["levels"]) == {"10_m_above_ground", "surface"}
    assert set(narrow_params["variables"]) < set(broad_params["variables"])
    assert set(narrow_params["levels"]) < set(broad_params["levels"])
    assert set(broad_params["variables"]) - set(narrow_params["variables"]) == {
        "DPT",
        "GUST",
        "RH",
        "TMP",
    }
    assert set(broad_params["levels"]) - set(narrow_params["levels"]) == {
        "2_m_above_ground"
    }


def test_m4_real_narrow_and_broad_contexts_are_both_sufficient():
    for projection in (NETWORK_BYTES, CARRIED_BYTES):
        comparison = assess_recorded_m4(
            FIXTURE_ROOT,
            cost_projection=projection,
        )

        assert comparison.narrow.context.status == "sufficient"
        assert comparison.broad.context.status == "sufficient"
        assert comparison.narrow.context.gap_requirement_ids == ()
        assert comparison.broad.context.gap_requirement_ids == ()

        narrow_coverage = {
            item.requirement_id: bool(item.candidate_ids)
            for item in comparison.narrow.context.coverage
        }
        broad_coverage = {
            item.requirement_id: bool(item.candidate_ids)
            for item in comparison.broad.context.coverage
        }
        assert narrow_coverage == broad_coverage == {
            "airspace_guidance": True,
            "obstacle_context": True,
            "weather_visibility": True,
            "weather_wind": True,
        }


def test_m4_weather_payload_reduction_is_provider_local_and_deterministic():
    comparison = assess_recorded_m4(
        FIXTURE_ROOT,
        cost_projection=CARRIED_BYTES,
    )

    assert comparison.narrow.payload_bytes == 594
    assert comparison.broad.payload_bytes == 1_580
    assert comparison.broad.extra_variables == ("DPT", "GUST", "RH", "TMP")
    assert comparison.broad.extra_levels == ("2_m_above_ground",)
    assert comparison.weather_payload_reduction_ratio == pytest.approx(
        0.6240506329113924
    )

    # This is intentionally not a total-context reduction metric. UASFM/DDOF
    # remain present in both full contexts, so the total acquisition costs are
    # larger than the two provider-local weather payloads.
    assert comparison.narrow.context.total_acquisition_cost > 594
    assert comparison.broad.context.total_acquisition_cost > 1_580


def test_m4_cost_projection_does_not_change_weather_breadth_result():
    network = assess_recorded_m4(FIXTURE_ROOT, cost_projection=NETWORK_BYTES)
    carried = assess_recorded_m4(FIXTURE_ROOT, cost_projection=CARRIED_BYTES)

    assert network.weather_payload_reduction_ratio == carried.weather_payload_reduction_ratio
    assert network.narrow.payload_bytes == carried.narrow.payload_bytes == 594
    assert network.broad.payload_bytes == carried.broad.payload_bytes == 1_580
    assert network.narrow.context.total_acquisition_cost != carried.narrow.context.total_acquisition_cost
    assert network.broad.context.total_acquisition_cost != carried.broad.context.total_acquisition_cost


def test_m4_comparability_fails_closed_if_nonsemantic_dimension_changes():
    narrow = _load(
        FIXTURE_ROOT / "hrrr_phx_20260818" / "hrrr-task.record.json"
    )
    broad = _load(
        FIXTURE_ROOT
        / "hrrr_phx_m4_broad_20260818"
        / "hrrr-m4-broad-weather.record.json"
    )

    wrong_bbox = deepcopy(broad)
    wrong_bbox["provenance"]["request_parameters"]["bbox"] = [
        -112.2,
        33.3,
        -111.9,
        33.6,
    ]
    with pytest.raises(ValueError, match="bbox changed"):
        _verify_comparable_records(narrow, wrong_bbox)

    wrong_valid_time = deepcopy(broad)
    wrong_valid_time["provenance"]["valid_from"] = "2026-08-18T08:00:00Z"
    with pytest.raises(ValueError, match="valid_from changed"):
        _verify_comparable_records(narrow, wrong_valid_time)


def test_m4_unknown_projection_fails_closed():
    with pytest.raises(ValueError, match="projection"):
        assess_recorded_m4(FIXTURE_ROOT, cost_projection="universal_cost")
