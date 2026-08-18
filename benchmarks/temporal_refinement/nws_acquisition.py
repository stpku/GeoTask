"""Deterministic NWS hourly-forecast acquisition contract for the benchmark.

The helpers construct source requests and validate the compact hourly series.
Network acquisition remains one-shot and outside normal CI.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Sequence
from urllib.parse import urlencode

from benchmarks.temporal_refinement.envelope_policy import HourlyWeather
from benchmarks.temporal_refinement.experiment_spec import (
    FINE_PERIOD_COUNT,
    SOURCE_FEATURE_FLAGS,
    SOURCE_POINT_LATITUDE,
    SOURCE_POINT_LONGITUDE,
    SOURCE_UNITS,
)


POINTS_ENDPOINT = (
    f"https://api.weather.gov/points/"
    f"{SOURCE_POINT_LATITUDE},{SOURCE_POINT_LONGITUDE}"
)
WIND_UNIT_CODE = "wmoUnit:km_h-1"
PRECIP_UNIT_CODE = "wmoUnit:percent"


@dataclass(frozen=True)
class PinnedHourlyPeriod:
    start_time: str
    end_time: str
    wind_kmh: float
    precip_probability_percent: float

    @property
    def weather(self) -> HourlyWeather:
        return HourlyWeather(
            wind_kmh=self.wind_kmh,
            precip_probability_percent=self.precip_probability_percent,
        )


def build_hourly_forecast_url(forecast_hourly_endpoint: str) -> str:
    if not forecast_hourly_endpoint.startswith("https://api.weather.gov/"):
        raise ValueError("forecastHourly endpoint must be an api.weather.gov HTTPS URL")
    return forecast_hourly_endpoint + "?" + urlencode({"units": SOURCE_UNITS})


def request_headers() -> dict[str, str]:
    return {
        "User-Agent": "GeoTask-Temporal-Refinement/0.1 (+https://github.com/stpku/GeoTask)",
        "Accept": "application/geo+json",
        "Feature-Flags": ",".join(SOURCE_FEATURE_FLAGS),
    }


def extract_forecast_hourly_endpoint(points_document: Mapping[str, object]) -> str:
    properties = points_document.get("properties")
    if not isinstance(properties, Mapping):
        raise ValueError("NWS points response has no properties mapping")
    value = properties.get("forecastHourly")
    if not isinstance(value, str) or not value:
        raise ValueError("NWS points response has no forecastHourly endpoint")
    if not value.startswith("https://api.weather.gov/"):
        raise ValueError("forecastHourly endpoint is outside api.weather.gov")
    return value


def _quantity(
    value: object,
    *,
    expected_unit: str,
    label: str,
) -> float:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a QuantitativeValue mapping")
    if value.get("unitCode") != expected_unit:
        raise ValueError(
            f"{label} unit mismatch: expected {expected_unit}, got {value.get('unitCode')}"
        )
    number = value.get("value")
    if isinstance(number, bool) or not isinstance(number, (int, float)):
        raise ValueError(f"{label} must contain a numeric value")
    return float(number)


def _parse_time(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty ISO timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must be timezone-aware")
    return parsed


def extract_pinned_periods(
    forecast_document: Mapping[str, object],
) -> tuple[PinnedHourlyPeriod, ...]:
    properties = forecast_document.get("properties")
    if not isinstance(properties, Mapping):
        raise ValueError("NWS hourly forecast has no properties mapping")
    periods = properties.get("periods")
    if not isinstance(periods, Sequence) or isinstance(periods, (str, bytes)):
        raise ValueError("NWS hourly forecast has no periods sequence")
    if len(periods) < FINE_PERIOD_COUNT:
        raise ValueError(
            f"NWS hourly forecast returned fewer than {FINE_PERIOD_COUNT} periods"
        )

    result: list[PinnedHourlyPeriod] = []
    previous_end: datetime | None = None
    for index, raw_period in enumerate(periods[:FINE_PERIOD_COUNT]):
        if not isinstance(raw_period, Mapping):
            raise ValueError(f"forecast period {index} is not a mapping")
        start = _parse_time(raw_period.get("startTime"), f"period {index} startTime")
        end = _parse_time(raw_period.get("endTime"), f"period {index} endTime")
        duration_seconds = (end - start).total_seconds()
        if duration_seconds != 3600:
            raise ValueError(f"forecast period {index} is not exactly one hour")
        if previous_end is not None and start != previous_end:
            raise ValueError(f"forecast period {index} is not contiguous")

        wind = _quantity(
            raw_period.get("windSpeed"),
            expected_unit=WIND_UNIT_CODE,
            label=f"period {index} windSpeed",
        )
        precip = _quantity(
            raw_period.get("probabilityOfPrecipitation"),
            expected_unit=PRECIP_UNIT_CODE,
            label=f"period {index} probabilityOfPrecipitation",
        )
        weather = HourlyWeather(
            wind_kmh=wind,
            precip_probability_percent=precip,
        )
        result.append(
            PinnedHourlyPeriod(
                start_time=start.isoformat(),
                end_time=end.isoformat(),
                wind_kmh=weather.wind_kmh,
                precip_probability_percent=weather.precip_probability_percent,
            )
        )
        previous_end = end

    return tuple(result)
