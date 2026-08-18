from __future__ import annotations

from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
_ROOT = str(ROOT)
sys.path.insert(0, _ROOT)
try:
    from benchmarks.temporal_refinement.nws_acquisition import (
        PRECIP_UNIT_CODE,
        WIND_UNIT_CODE,
        build_hourly_forecast_url,
        extract_forecast_hourly_endpoint,
        extract_pinned_periods,
        request_headers,
    )
finally:
    sys.path.remove(_ROOT)


def _period(index: int, *, wind: float = 12.0, pop: float = 20.0) -> dict[str, object]:
    return {
        "startTime": f"2026-08-18T{index:02d}:00:00+00:00",
        "endTime": f"2026-08-18T{index + 1:02d}:00:00+00:00",
        "windSpeed": {"unitCode": WIND_UNIT_CODE, "value": wind},
        "probabilityOfPrecipitation": {"unitCode": PRECIP_UNIT_CODE, "value": pop},
    }


def test_points_response_must_supply_official_hourly_endpoint() -> None:
    endpoint = "https://api.weather.gov/gridpoints/PSR/160,60/forecast/hourly"
    assert extract_forecast_hourly_endpoint(
        {"properties": {"forecastHourly": endpoint}}
    ) == endpoint
    assert build_hourly_forecast_url(endpoint).endswith("?units=si")

    with pytest.raises(ValueError, match="outside api.weather.gov"):
        extract_forecast_hourly_endpoint(
            {"properties": {"forecastHourly": "https://example.test/hourly"}}
        )


def test_request_requires_quantitative_wind_feature_flag() -> None:
    headers = request_headers()
    assert "forecast_wind_speed_qv" in headers["Feature-Flags"]
    assert "GeoTask-Temporal-Refinement" in headers["User-Agent"]


def test_hourly_periods_require_contiguous_quantitative_values() -> None:
    periods = [_period(index) for index in range(24)]
    result = extract_pinned_periods({"properties": {"periods": periods}})

    assert len(result) == 24
    assert result[0].wind_kmh == 12.0
    assert result[0].precip_probability_percent == 20.0


def test_hourly_periods_fail_closed_on_null_or_wrong_units() -> None:
    periods = [_period(index) for index in range(24)]
    periods[3]["windSpeed"] = {"unitCode": "wmoUnit:m_s-1", "value": 4.0}
    with pytest.raises(ValueError, match="unit mismatch"):
        extract_pinned_periods({"properties": {"periods": periods}})

    periods = [_period(index) for index in range(24)]
    periods[5]["probabilityOfPrecipitation"] = {
        "unitCode": PRECIP_UNIT_CODE,
        "value": None,
    }
    with pytest.raises(ValueError, match="numeric value"):
        extract_pinned_periods({"properties": {"periods": periods}})
