"""Read-only ArcGIS acquisition helpers for TC1-Real spatial planning.

The helpers keep acquisition mechanics in the benchmark layer. They do not add
planning semantics to GeoTask Core and do not infer that any source is
sufficient for a real investment decision.

ArcGIS services can cap ordinary feature queries at ``maxRecordCount``. TC1-Real
therefore treats a single bounded response as diagnostic unless completeness is
proven. The ID-query + object-ID chunk helpers below provide a deterministic way
to retrieve all matching records without silently accepting truncation.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Iterable, Sequence
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from benchmarks.tc1_real.measurement import (
    AcquisitionMeasurement,
    AcquisitionRecord,
    build_offline_record,
)


DEFAULT_USER_AGENT = "GeoTask-TC1-Real/0.1 (+https://github.com/stpku/GeoTask)"


def normalize_bbox(bbox: Sequence[float]) -> tuple[float, float, float, float]:
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


def _normalize_out_fields(out_fields: Iterable[str]) -> tuple[str, ...]:
    fields = tuple(str(field).strip() for field in out_fields)
    if not fields or any(not field for field in fields):
        raise ValueError("out_fields must contain non-empty field names")
    for field in fields:
        if not all(ch.isalnum() or ch in "_.*" for ch in field):
            raise ValueError(f"unsafe ArcGIS field name: {field}")
    return fields


def _query_endpoint(layer_endpoint: str) -> str:
    endpoint = layer_endpoint.rstrip("/")
    if not endpoint.startswith("https://"):
        raise ValueError("ArcGIS endpoint must use https")
    if endpoint.endswith("/query"):
        return endpoint
    return endpoint + "/query"


def _validate_where(where: str) -> str:
    normalized = str(where).strip()
    if not normalized:
        raise ValueError("where must be non-empty")
    return normalized


def build_spatial_query_url(
    *,
    layer_endpoint: str,
    bbox: Sequence[float],
    out_fields: Iterable[str],
    where: str = "1=1",
    return_geometry: bool = True,
    output_format: str = "geojson",
) -> str:
    """Build one bounded WGS84 feature query.

    This does not by itself prove completeness when the provider has a record
    limit. Use ``build_spatial_ids_query_url`` plus object-ID chunks when the
    result can exceed ``maxRecordCount``.
    """

    min_lon, min_lat, max_lon, max_lat = normalize_bbox(bbox)
    fields = _normalize_out_fields(out_fields)
    if output_format not in {"json", "geojson"}:
        raise ValueError("output_format must be json or geojson")

    params = {
        "where": _validate_where(where),
        "geometry": f"{min_lon},{min_lat},{max_lon},{max_lat}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": ",".join(fields),
        "returnGeometry": "true" if return_geometry else "false",
        "outSR": "4326",
        "f": output_format,
    }
    return _query_endpoint(layer_endpoint) + "?" + urlencode(params)


def build_spatial_ids_query_url(
    *,
    layer_endpoint: str,
    bbox: Sequence[float],
    where: str = "1=1",
) -> str:
    """Build a bounded ``returnIdsOnly`` query used to prove completeness."""

    min_lon, min_lat, max_lon, max_lat = normalize_bbox(bbox)
    params = {
        "where": _validate_where(where),
        "geometry": f"{min_lon},{min_lat},{max_lon},{max_lat}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "returnIdsOnly": "true",
        "f": "json",
    }
    return _query_endpoint(layer_endpoint) + "?" + urlencode(params)


def build_numeric_in_where(field: str, values: Iterable[int]) -> str:
    """Build one deterministic numeric IN predicate without string injection."""

    normalized_field = _normalize_out_fields((field,))[0]
    normalized_values = tuple(sorted({int(value) for value in values}))
    if not normalized_values:
        raise ValueError("numeric IN predicate requires at least one value")
    return f"{normalized_field} IN ({','.join(str(value) for value in normalized_values)})"


def build_table_query_url(
    *,
    table_endpoint: str,
    out_fields: Iterable[str],
    where: str,
    output_format: str = "json",
) -> str:
    """Build a read-only ArcGIS table query URL."""

    fields = _normalize_out_fields(out_fields)
    if output_format != "json":
        raise ValueError("table output_format must be json")
    params = {
        "where": _validate_where(where),
        "outFields": ",".join(fields),
        "returnGeometry": "false",
        "f": output_format,
    }
    return _query_endpoint(table_endpoint) + "?" + urlencode(params)


def build_table_ids_query_url(*, table_endpoint: str, where: str) -> str:
    """Build a table ``returnIdsOnly`` query used before chunk retrieval."""

    params = {
        "where": _validate_where(where),
        "returnIdsOnly": "true",
        "f": "json",
    }
    return _query_endpoint(table_endpoint) + "?" + urlencode(params)


def normalize_object_ids(object_ids: Iterable[int]) -> tuple[int, ...]:
    normalized = tuple(sorted({int(value) for value in object_ids}))
    if not normalized:
        raise ValueError("object_ids must contain at least one id")
    if any(value < 0 for value in normalized):
        raise ValueError("object_ids must be non-negative")
    return normalized


def chunk_object_ids(
    object_ids: Iterable[int], *, chunk_size: int = 1000
) -> tuple[tuple[int, ...], ...]:
    """Return deterministic object-ID chunks smaller than provider row caps."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    normalized = normalize_object_ids(object_ids)
    return tuple(
        normalized[index : index + chunk_size]
        for index in range(0, len(normalized), chunk_size)
    )


def build_object_ids_query_url(
    *,
    layer_endpoint: str,
    object_ids: Iterable[int],
    out_fields: Iterable[str],
    return_geometry: bool,
    output_format: str,
) -> str:
    """Build one deterministic feature/table retrieval for explicit IDs."""

    ids = normalize_object_ids(object_ids)
    fields = _normalize_out_fields(out_fields)
    if output_format not in {"json", "geojson"}:
        raise ValueError("output_format must be json or geojson")
    if output_format == "geojson" and not return_geometry:
        # A geometry-free table response has clearer ArcGIS JSON semantics.
        raise ValueError("geometry-free object-id query must use json format")

    params = {
        "objectIds": ",".join(str(value) for value in ids),
        "outFields": ",".join(fields),
        "returnGeometry": "true" if return_geometry else "false",
        "f": output_format,
    }
    if return_geometry:
        params["outSR"] = "4326"
    return _query_endpoint(layer_endpoint) + "?" + urlencode(params)


def extract_object_ids(payload: bytes) -> tuple[int, ...]:
    """Parse one ArcGIS ``returnIdsOnly`` response fail-closed."""

    try:
        document = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("ArcGIS ID response is not valid JSON") from exc
    if not isinstance(document, dict) or "error" in document:
        raise ValueError("ArcGIS ID response is not a successful object")
    values = document.get("objectIds")
    if not isinstance(values, list):
        raise ValueError("ArcGIS ID response has no objectIds list")
    return normalize_object_ids(int(value) for value in values)


def acquire_public_bytes(
    *,
    source_id: str,
    source_family: str,
    url: str,
    output_path: Path,
    record_path: Path,
    request_parameters: dict[str, object],
    timeout_seconds: float = 60.0,
    monetary_cost: float | None = 0.0,
    source_crs: str | None = "EPSG:4326",
    notes: str = "",
) -> AcquisitionRecord:
    """Acquire exact public bytes and write a replayable measurement record."""

    if not url.startswith("https://"):
        raise ValueError("public acquisition URL must use https")
    request = Request(
        url,
        headers={
            "Accept": "application/json,application/geo+json,*/*",
            "User-Agent": DEFAULT_USER_AGENT,
        },
        method="GET",
    )
    started = time.perf_counter()
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
        payload = response.read()
    elapsed = time.perf_counter() - started

    # Reject ArcGIS HTML/error pages and malformed JSON before recording them as
    # successful context. GeoJSON is JSON, so one parser covers both cases.
    try:
        document = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("ArcGIS acquisition did not return JSON/GeoJSON") from exc
    if isinstance(document, dict) and "error" in document:
        raise ValueError(f"ArcGIS acquisition returned error: {document['error']!r}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(payload)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    record = build_offline_record(
        source_id=source_id,
        source_family=source_family,
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
        request_parameters=request_parameters,
        source_crs=source_crs,
        notes=notes,
    )
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(
        json.dumps(record.to_json_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return record
