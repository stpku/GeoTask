from pathlib import Path
import sys
from urllib.parse import parse_qs, urlparse

import pytest


_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, _ROOT)
try:
    from benchmarks.tc1_real.hrrr_acquisition import (
        build_hrrr_query_url,
        hrrr_run_and_valid_time,
    )
    from benchmarks.tc1_real.source_profiles import NOAA_HRRR
finally:
    sys.path.remove(_ROOT)


def _query(url: str):
    return parse_qs(urlparse(url).query, keep_blank_values=True)


def test_hrrr_profile_records_bounded_subset_capability():
    assert NOAA_HRRR.spatial_resolution_meters == 3000.0
    assert NOAA_HRRR.temporal_update_seconds == 3600
    assert NOAA_HRRR.query_formats == ("grib2-subset",)
    assert NOAA_HRRR.observed_machine_endpoint.endswith("filter_hrrr_2d.pl")
    assert "subregion" in NOAA_HRRR.notes


def test_hrrr_url_binds_run_forecast_variables_levels_and_bbox():
    url = build_hrrr_query_url(
        date="20260818",
        cycle=12,
        forecast_hour=3,
        bbox=(-112.10, 33.40, -112.00, 33.50),
        variables=("UGRD", "VGRD", "GUST", "VIS"),
        levels=("10_m_above_ground", "surface"),
    )
    query = _query(url)

    assert url.startswith("https://")
    assert query["file"] == ["hrrr.t12z.wrfsfcf03.grib2"]
    assert query["var_UGRD"] == ["on"]
    assert query["var_VGRD"] == ["on"]
    assert query["var_GUST"] == ["on"]
    assert query["var_VIS"] == ["on"]
    assert query["lev_10_m_above_ground"] == ["on"]
    assert query["lev_surface"] == ["on"]
    assert query["leftlon"] == ["-112.1"]
    assert query["rightlon"] == ["-112"]
    assert query["toplat"] == ["33.5"]
    assert query["bottomlat"] == ["33.4"]
    assert query["dir"] == ["/hrrr.20260818/conus"]
    assert "subregion" in query


def test_hrrr_run_and_valid_time_are_explicit():
    run_time, valid_time = hrrr_run_and_valid_time(
        date="20260818",
        cycle=23,
        forecast_hour=3,
    )

    assert run_time == "2026-08-18T23:00:00Z"
    assert valid_time == "2026-08-19T02:00:00Z"


def test_hrrr_request_deduplicates_variables_and_levels():
    url = build_hrrr_query_url(
        date="20260818",
        cycle=0,
        forecast_hour=0,
        bbox=(-112.10, 33.40, -112.00, 33.50),
        variables=("ugrd", "UGRD"),
        levels=("surface", "surface"),
    )
    query = _query(url)

    assert list(key for key in query if key == "var_UGRD") == ["var_UGRD"]
    assert list(key for key in query if key == "lev_surface") == ["lev_surface"]


def test_hrrr_invalid_run_or_scope_fails_before_network():
    common = dict(
        date="20260818",
        cycle=12,
        forecast_hour=3,
        bbox=(-112.10, 33.40, -112.00, 33.50),
        variables=("UGRD",),
        levels=("10_m_above_ground",),
    )

    with pytest.raises(ValueError, match="YYYYMMDD"):
        build_hrrr_query_url(**{**common, "date": "2026-08-18"})
    with pytest.raises(ValueError, match="cycle"):
        build_hrrr_query_url(**{**common, "cycle": 24})
    with pytest.raises(ValueError, match="forecast_hour"):
        build_hrrr_query_url(**{**common, "forecast_hour": 49})
    with pytest.raises(ValueError, match="minimums"):
        build_hrrr_query_url(
            **{**common, "bbox": (-112.00, 33.50, -112.10, 33.40)}
        )


def test_hrrr_invalid_variable_level_or_endpoint_is_rejected():
    common = dict(
        date="20260818",
        cycle=12,
        forecast_hour=3,
        bbox=(-112.10, 33.40, -112.00, 33.50),
    )

    with pytest.raises(ValueError, match="variables"):
        build_hrrr_query_url(**common, variables=(), levels=("surface",))
    with pytest.raises(ValueError, match="levels"):
        build_hrrr_query_url(**common, variables=("GUST",), levels=())
    with pytest.raises(ValueError, match="variables"):
        build_hrrr_query_url(
            **common,
            variables=("UGRD&var_ALL",),
            levels=("surface",),
        )
    with pytest.raises(ValueError, match="https"):
        build_hrrr_query_url(
            **common,
            variables=("GUST",),
            levels=("surface",),
            endpoint="http://example.invalid/filter_hrrr_2d.pl",
        )
