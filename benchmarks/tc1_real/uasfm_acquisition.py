"""Read-only bounded acquisition helper for FAA UAS Facility Map data.

Live network acquisition is optional/manual. CI tests only request construction
and offline parsing boundaries; it never depends on FAA/ArcGIS availability.

This module retrieves context data only. It does not grant or evaluate real
flight authorization.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Sequence
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from benchmarks.tc1_real.measurement import (
    AcquisitionMeasurement,
    build_offline_record,
)
from benchmarks.tc1_real.source_profiles import FAA_UASFM


DEFAULT_OUT_FIELDS = (
    "OBJECTID",
    "CEILING",
    "UNIT",
    "MAP_EFF",
    "LAST_EDIT",
    "LATITUDE",
    "LONGITUDE",
    "APT1_FAAID",
    "APT1_ICAO",
    "APT1_NAME",
    "APT1_LAANC",
    "AIRSPACE_1",
    "REGION",
)


def _format_bbox(bbox: Sequence[float]) -> str:
    if len(bbox) != 4:
        raise ValueError("bbox must contain min_lon,min_lat,max_lon,max_lat")
    min_lon, min_lat, max_lon, max_lat = map(float, bbox)
    if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
        raise ValueError("bbox longitude must be within [-180, 180]")
    if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
        raise ValueError("bbox latitude must be within [-90, 90]")
    if min_lon >= max_lon or min_lat >= max_lat:
        raise ValueError("bbox minimums must be smaller than maximums")
    return f"{min_lon:g},{min_lat:g},{max_lon:g},{max_lat:g}"


def build_uasfm_query_url(
    *,
    bbox: Sequence[float],
    endpoint: str | None = None,
    out_fields: Sequence[str] = DEFAULT_OUT_FIELDS,
    return_geometry: bool = True,
) -> str:
    """Build one bounded ArcGIS FeatureServer query URL."""

    base = endpoint or FAA_UASFM.observed_machine_endpoint
    if not base:
        raise ValueError("UASFM machine endpoint must be supplied")
    if not base.startswith("https://"):
        raise ValueError("UASFM endpoint must use https")
    if not out_fields:
        raise ValueError("out_fields must not be empty")

    params = {
        "where": "1=1",
        "geometry": _format_bbox(bbox),
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": ",".join(out_fields),
        "returnGeometry": "true" if return_geometry else "false",
        "outSR": "4326",
        "f": "geojson",
    }
    return f"{base.rstrip('/')}/query?{urlencode(params)}"


def acquire_uasfm(
    *,
    bbox: Sequence[float],
    output_path: Path,
    record_path: Path,
    endpoint: str | None = None,
    timeout_seconds: float = 30.0,
    monetary_cost: float | None = None,
) -> None:
    """Acquire one bounded UASFM GeoJSON response and write provenance record."""

    url = build_uasfm_query_url(bbox=bbox, endpoint=endpoint)
    request = Request(
        url,
        headers={
            "Accept": "application/geo+json,application/json",
            "User-Agent": "GeoTask-TC1-Real/0.1 (+https://github.com/stpku/GeoTask)",
        },
        method="GET",
    )

    started = time.perf_counter()
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
        payload = response.read()
    elapsed = time.perf_counter() - started

    # Validate only that the exact response is parseable JSON/GeoJSON. Domain
    # semantics remain explicit downstream context requirements.
    parsed = json.loads(payload.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("UASFM response must be a JSON object")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(payload)

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    measurement = AcquisitionMeasurement(
        monetary_cost=monetary_cost,
        request_count=1,
        bytes_transferred=len(payload),
        wall_clock_seconds=elapsed,
        storage_bytes=len(payload),
    )
    record = build_offline_record(
        source_id=FAA_UASFM.source_id,
        source_family=FAA_UASFM.source_family,
        retrieval_timestamp=now,
        source_url=url,
        payload=payload,
        measurement=measurement,
        fixture_path=str(output_path),
        request_parameters={
            "bbox": list(map(float, bbox)),
            "format": "geojson",
            "out_fields": list(DEFAULT_OUT_FIELDS),
        },
        source_crs="EPSG:4326",
        source_units={"CEILING": "source_declared_UNIT"},
        notes=(
            "Read-only UASFM context acquisition. This record does not represent "
            "FAA flight authorization."
        ),
    )
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(
        json.dumps(record.to_json_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _parse_bbox(value: str) -> tuple[float, float, float, float]:
    parts = value.split(",")
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(
            "bbox must be min_lon,min_lat,max_lon,max_lat"
        )
    try:
        bbox = tuple(float(item) for item in parts)
        _format_bbox(bbox)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    return bbox  # type: ignore[return-value]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Acquire a bounded read-only FAA UASFM TC1-Real fixture."
    )
    parser.add_argument("--bbox", required=True, type=_parse_bbox)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--endpoint", default=None)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--monetary-cost",
        type=float,
        default=None,
        help="Measured/known monetary cost; omit when unknown instead of assuming zero.",
    )
    args = parser.parse_args()

    acquire_uasfm(
        bbox=args.bbox,
        output_path=args.output,
        record_path=args.record,
        endpoint=args.endpoint,
        timeout_seconds=args.timeout,
        monetary_cost=args.monetary_cost,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
