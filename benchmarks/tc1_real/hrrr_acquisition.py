"""Read-only bounded NOAA/NCEP HRRR acquisition for TC1-Real.

The helper uses the official NOMADS HRRR 2-D Grib Filter interface so an
experiment can measure a task-bounded variable/level/region request rather than
implicitly treating a full model product as context.

Live network access is optional/manual and is never required by CI.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import time
from typing import Sequence
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from benchmarks.tc1_real.measurement import (
    AcquisitionMeasurement,
    AcquisitionRecord,
    build_offline_record,
)
from benchmarks.tc1_real.source_profiles import NOAA_HRRR


_VARIABLE_RE = re.compile(r"^[A-Z0-9]+$")
_LEVEL_RE = re.compile(r"^[a-z0-9_]+$")


def _normalize_date(value: str) -> str:
    try:
        parsed = datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise ValueError("date must use YYYYMMDD") from exc
    return parsed.strftime("%Y%m%d")


def _normalize_cycle(cycle: int) -> int:
    value = int(cycle)
    if not 0 <= value <= 23:
        raise ValueError("cycle must be within 0..23 UTC")
    return value


def _normalize_forecast_hour(forecast_hour: int) -> int:
    value = int(forecast_hour)
    if not 0 <= value <= 48:
        raise ValueError("forecast_hour must be within 0..48")
    return value


def _normalize_bbox(
    bbox: Sequence[float],
) -> tuple[float, float, float, float]:
    if len(bbox) != 4:
        raise ValueError("bbox must contain min_lon,min_lat,max_lon,max_lat")
    min_lon, min_lat, max_lon, max_lat = map(float, bbox)
    if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
        raise ValueError("bbox longitude must be within [-180, 180]")
    if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
        raise ValueError("bbox latitude must be within [-90, 90]")
    if min_lon >= max_lon or min_lat >= max_lat:
        raise ValueError("bbox minimums must be smaller than maximums")
    return min_lon, min_lat, max_lon, max_lat


def _normalize_variables(values: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(dict.fromkeys(str(value).upper() for value in values))
    if not normalized:
        raise ValueError("at least one HRRR variable is required")
    if any(not _VARIABLE_RE.fullmatch(value) for value in normalized):
        raise ValueError("HRRR variables must contain only A-Z, 0-9")
    return normalized


def _normalize_levels(values: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(dict.fromkeys(str(value).lower() for value in values))
    if not normalized:
        raise ValueError("at least one HRRR level is required")
    if any(not _LEVEL_RE.fullmatch(value) for value in normalized):
        raise ValueError("HRRR level names must use lowercase letters/digits/underscore")
    return normalized


def hrrr_run_and_valid_time(
    *,
    date: str,
    cycle: int,
    forecast_hour: int,
) -> tuple[str, str]:
    normalized_date = _normalize_date(date)
    normalized_cycle = _normalize_cycle(cycle)
    normalized_forecast = _normalize_forecast_hour(forecast_hour)
    run = datetime.strptime(
        f"{normalized_date}{normalized_cycle:02d}", "%Y%m%d%H"
    ).replace(tzinfo=timezone.utc)
    valid = run + timedelta(hours=normalized_forecast)
    return (
        run.isoformat().replace("+00:00", "Z"),
        valid.isoformat().replace("+00:00", "Z"),
    )


def build_hrrr_query_url(
    *,
    date: str,
    cycle: int,
    forecast_hour: int,
    bbox: Sequence[float],
    variables: Sequence[str],
    levels: Sequence[str],
    endpoint: str | None = None,
) -> str:
    """Build one bounded NOMADS HRRR hourly 2-D GRIB2 subset URL."""

    normalized_date = _normalize_date(date)
    normalized_cycle = _normalize_cycle(cycle)
    normalized_forecast = _normalize_forecast_hour(forecast_hour)
    min_lon, min_lat, max_lon, max_lat = _normalize_bbox(bbox)
    normalized_variables = _normalize_variables(variables)
    normalized_levels = _normalize_levels(levels)

    base = endpoint or NOAA_HRRR.observed_machine_endpoint
    if not base:
        raise ValueError("HRRR NOMADS endpoint must be supplied")
    if not base.startswith("https://"):
        raise ValueError("HRRR NOMADS endpoint must use https")

    params: list[tuple[str, str]] = [
        (
            "file",
            f"hrrr.t{normalized_cycle:02d}z.wrfsfcf{normalized_forecast:02d}.grib2",
        )
    ]
    params.extend((f"lev_{level}", "on") for level in normalized_levels)
    params.extend((f"var_{variable}", "on") for variable in normalized_variables)
    params.extend(
        [
            ("subregion", ""),
            ("leftlon", f"{min_lon:g}"),
            ("rightlon", f"{max_lon:g}"),
            ("toplat", f"{max_lat:g}"),
            ("bottomlat", f"{min_lat:g}"),
            ("dir", f"/hrrr.{normalized_date}/conus"),
        ]
    )
    return f"{base}?{urlencode(params)}"


def acquire_hrrr_subset(
    *,
    date: str,
    cycle: int,
    forecast_hour: int,
    bbox: Sequence[float],
    variables: Sequence[str],
    levels: Sequence[str],
    output_path: Path,
    record_path: Path,
    endpoint: str | None = None,
    timeout_seconds: float = 60.0,
    monetary_cost: float | None = None,
) -> AcquisitionRecord:
    """Acquire exact bounded HRRR GRIB2 bytes and write measurement provenance."""

    normalized_bbox = _normalize_bbox(bbox)
    normalized_variables = _normalize_variables(variables)
    normalized_levels = _normalize_levels(levels)
    url = build_hrrr_query_url(
        date=date,
        cycle=cycle,
        forecast_hour=forecast_hour,
        bbox=normalized_bbox,
        variables=normalized_variables,
        levels=normalized_levels,
        endpoint=endpoint,
    )

    request = Request(
        url,
        headers={
            "Accept": "application/octet-stream",
            "User-Agent": "GeoTask-TC1-Real/0.1 (+https://github.com/stpku/GeoTask)",
        },
        method="GET",
    )
    started = time.perf_counter()
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
        payload = response.read()
    elapsed = time.perf_counter() - started

    if len(payload) < 8 or payload[:4] != b"GRIB" or payload[7] != 2:
        raise ValueError("HRRR response is not a GRIB2 payload")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(payload)

    run_time, valid_time = hrrr_run_and_valid_time(
        date=date,
        cycle=cycle,
        forecast_hour=forecast_hour,
    )
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    record = build_offline_record(
        source_id=NOAA_HRRR.source_id,
        source_family=NOAA_HRRR.source_family,
        retrieval_timestamp=now,
        source_url=url,
        payload=payload,
        measurement=AcquisitionMeasurement(
            monetary_cost=monetary_cost,
            request_count=1,
            bytes_transferred=len(payload),
            wall_clock_seconds=elapsed,
            storage_bytes=len(payload),
        ),
        fixture_path=str(output_path),
        request_parameters={
            "date": _normalize_date(date),
            "cycle_utc": _normalize_cycle(cycle),
            "forecast_hour": _normalize_forecast_hour(forecast_hour),
            "bbox": list(normalized_bbox),
            "variables": list(normalized_variables),
            "levels": list(normalized_levels),
        },
        source_effective_at=run_time,
        valid_from=valid_time,
        valid_until=valid_time,
        source_resolution="3 km nominal HRRR grid",
        notes=(
            "Read-only bounded NOMADS HRRR GRIB2 subset. Exact variable/level "
            "interpretation remains part of downstream task context semantics."
        ),
    )
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(
        json.dumps(record.to_json_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return record


def _parse_bbox(value: str) -> tuple[float, float, float, float]:
    try:
        return _normalize_bbox(tuple(float(item) for item in value.split(",")))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Acquire a bounded read-only NOAA/NCEP HRRR GRIB2 subset."
    )
    parser.add_argument("--date", required=True, help="YYYYMMDD")
    parser.add_argument("--cycle", required=True, type=int, help="UTC hour 0..23")
    parser.add_argument("--forecast-hour", required=True, type=int)
    parser.add_argument("--bbox", required=True, type=_parse_bbox)
    parser.add_argument("--variable", action="append", required=True)
    parser.add_argument("--level", action="append", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--endpoint", default=None)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--monetary-cost", type=float, default=None)
    args = parser.parse_args()

    acquire_hrrr_subset(
        date=args.date,
        cycle=args.cycle,
        forecast_hour=args.forecast_hour,
        bbox=args.bbox,
        variables=args.variable,
        levels=args.level,
        output_path=args.output,
        record_path=args.record,
        endpoint=args.endpoint,
        timeout_seconds=args.timeout,
        monetary_cost=args.monetary_cost,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
