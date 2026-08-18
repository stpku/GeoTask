"""TC1-Real helpers for FAA Daily Digital Obstacle File processing.

DDOF is treated as a broad-download provider. GeoTask cannot claim server-side
spatial acquisition savings where the provider exposes only a whole-file ZIP.
The benchmark therefore measures two different stages:

1. acquisition burden for the exact downloaded ZIP;
2. local selection burden and selected-context size for a task bbox.

No result from this module is a complete obstacle/safety determination. FAA's
DDOF documentation explicitly states that the file does not contain every
possible obstruction and includes both verified and unverified data.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import time
from typing import Iterable, Mapping, Sequence
from urllib.request import Request, urlopen
import zipfile

from benchmarks.tc1_real.measurement import (
    AcquisitionMeasurement,
    AcquisitionRecord,
    build_offline_record,
    sha256_bytes,
)
from benchmarks.tc1_real.source_profiles import FAA_DDOF


@dataclass(frozen=True)
class DDOFSelectionMeasurement:
    input_csv_bytes: int
    input_row_count: int
    selected_row_count: int
    selected_serialized_bytes: int
    wall_clock_seconds: float
    latitude_field: str
    longitude_field: str
    verification_field: str | None
    accepted_verification_values: tuple[str, ...] | None
    bbox: tuple[float, float, float, float]

    @property
    def row_reduction_ratio(self) -> float:
        if self.input_row_count == 0:
            return 0.0
        return 1.0 - (self.selected_row_count / self.input_row_count)

    @property
    def byte_reduction_ratio(self) -> float:
        if self.input_csv_bytes == 0:
            return 0.0
        return 1.0 - (self.selected_serialized_bytes / self.input_csv_bytes)


@dataclass(frozen=True)
class DDOFSelectionResult:
    selected_rows: tuple[Mapping[str, str], ...]
    measurement: DDOFSelectionMeasurement
    source_csv_sha256: str

    def to_json_dict(self) -> dict[str, object]:
        return {
            "source_csv_sha256": self.source_csv_sha256,
            "measurement": {
                "input_csv_bytes": self.measurement.input_csv_bytes,
                "input_row_count": self.measurement.input_row_count,
                "selected_row_count": self.measurement.selected_row_count,
                "selected_serialized_bytes": self.measurement.selected_serialized_bytes,
                "wall_clock_seconds": self.measurement.wall_clock_seconds,
                "latitude_field": self.measurement.latitude_field,
                "longitude_field": self.measurement.longitude_field,
                "verification_field": self.measurement.verification_field,
                "accepted_verification_values": (
                    list(self.measurement.accepted_verification_values)
                    if self.measurement.accepted_verification_values is not None
                    else None
                ),
                "bbox": list(self.measurement.bbox),
                "row_reduction_ratio": self.measurement.row_reduction_ratio,
                "byte_reduction_ratio": self.measurement.byte_reduction_ratio,
            },
            "selected_rows": [dict(row) for row in self.selected_rows],
        }


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


def acquire_ddof_zip(
    *,
    output_path: Path,
    record_path: Path,
    endpoint: str | None = None,
    timeout_seconds: float = 60.0,
    monetary_cost: float | None = None,
) -> AcquisitionRecord:
    """Download the exact broad DDOF ZIP and record acquisition burden."""

    url = endpoint or FAA_DDOF.observed_machine_endpoint
    if not url:
        raise ValueError("DDOF endpoint must be supplied")
    if not url.startswith("https://"):
        raise ValueError("DDOF endpoint must use https")

    request = Request(
        url,
        headers={
            "Accept": "application/zip,application/octet-stream",
            "User-Agent": "GeoTask-TC1-Real/0.1 (+https://github.com/stpku/GeoTask)",
        },
        method="GET",
    )
    started = time.perf_counter()
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
        payload = response.read()
    elapsed = time.perf_counter() - started

    # Fail before recording a non-ZIP response such as an HTML error page.
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        if not archive.namelist():
            raise ValueError("DDOF ZIP contains no members")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(payload)

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    record = build_offline_record(
        source_id=FAA_DDOF.source_id,
        source_family=FAA_DDOF.source_family,
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
        source_crs="WGS84",
        notes=(
            "Broad DDOF ZIP acquisition. Provider does not expose a task-bounded "
            "spatial query in this TC1-Real profile; local filtering is measured "
            "separately."
        ),
    )
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(
        json.dumps(record.to_json_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return record


def extract_single_csv_from_zip(zip_payload: bytes) -> tuple[str, bytes]:
    """Extract exactly one CSV member from a DDOF ZIP payload."""

    with zipfile.ZipFile(io.BytesIO(zip_payload)) as archive:
        csv_members = [
            name
            for name in archive.namelist()
            if not name.endswith("/") and name.lower().endswith(".csv")
        ]
        if len(csv_members) != 1:
            raise ValueError(
                "DDOF ZIP must contain exactly one CSV member for deterministic "
                f"processing; found {len(csv_members)}"
            )
        member = csv_members[0]
        return member, archive.read(member)


def inspect_csv_fields(
    csv_payload: bytes,
    *,
    encoding: str = "cp1252",
) -> tuple[str, ...]:
    """Return exact CSV header names without guessing semantic aliases."""

    text = csv_payload.decode(encoding)
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration as exc:
        raise ValueError("DDOF CSV is empty") from exc
    fields = tuple(item.strip() for item in header)
    if not fields or any(not item for item in fields):
        raise ValueError("DDOF CSV header contains an empty field name")
    if len(fields) != len(set(fields)):
        raise ValueError("DDOF CSV header contains duplicate field names")
    return fields


def _serialize_selected_rows(
    rows: Iterable[Mapping[str, str]],
    fieldnames: Sequence[str],
) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def select_ddof_csv_context(
    csv_payload: bytes,
    *,
    bbox: Sequence[float],
    latitude_field: str,
    longitude_field: str,
    verification_field: str | None = None,
    accepted_verification_values: Sequence[str] | None = None,
    encoding: str = "cp1252",
) -> DDOFSelectionResult:
    """Select task-bounded DDOF rows from an already acquired CSV.

    Field names are explicit inputs. The FAA public page documents decimal
    degree latitude/longitude in the CSV but the benchmark does not guess their
    exact header spelling. A live acquisition must inspect and record the actual
    header first.
    """

    normalized_bbox = _normalize_bbox(bbox)
    min_lon, min_lat, max_lon, max_lat = normalized_bbox
    text = csv_payload.decode(encoding)
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("DDOF CSV must contain a header row")
    fieldnames = tuple(item.strip() for item in reader.fieldnames)
    required_fields = {latitude_field, longitude_field}
    if verification_field is not None:
        required_fields.add(verification_field)
    missing = sorted(required_fields - set(fieldnames))
    if missing:
        raise ValueError(
            "DDOF CSV is missing required fields: " + ", ".join(missing)
        )
    if accepted_verification_values is not None and verification_field is None:
        raise ValueError(
            "verification_field is required when accepted_verification_values "
            "is provided"
        )

    accepted = (
        tuple(str(value) for value in accepted_verification_values)
        if accepted_verification_values is not None
        else None
    )
    accepted_set = set(accepted) if accepted is not None else None

    started = time.perf_counter()
    selected: list[Mapping[str, str]] = []
    input_row_count = 0
    for raw_row in reader:
        input_row_count += 1
        row = {str(key).strip(): value for key, value in raw_row.items() if key is not None}
        try:
            lat = float(row[latitude_field])
            lon = float(row[longitude_field])
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"DDOF row {input_row_count} has invalid decimal coordinates"
            ) from exc
        if not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
            continue
        if accepted_set is not None:
            if row[verification_field] not in accepted_set:  # type: ignore[index]
                continue
        selected.append(row)

    serialized = _serialize_selected_rows(selected, fieldnames)
    elapsed = time.perf_counter() - started
    measurement = DDOFSelectionMeasurement(
        input_csv_bytes=len(csv_payload),
        input_row_count=input_row_count,
        selected_row_count=len(selected),
        selected_serialized_bytes=len(serialized),
        wall_clock_seconds=elapsed,
        latitude_field=latitude_field,
        longitude_field=longitude_field,
        verification_field=verification_field,
        accepted_verification_values=accepted,
        bbox=normalized_bbox,
    )
    return DDOFSelectionResult(
        selected_rows=tuple(selected),
        measurement=measurement,
        source_csv_sha256=sha256_bytes(csv_payload),
    )


def _parse_bbox(value: str) -> tuple[float, float, float, float]:
    parts = value.split(",")
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(
            "bbox must be min_lon,min_lat,max_lon,max_lat"
        )
    try:
        return _normalize_bbox(tuple(float(item) for item in parts))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect/filter an already acquired FAA DDOF CSV fixture."
    )
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--inspect-fields", action="store_true")
    parser.add_argument("--bbox", type=_parse_bbox)
    parser.add_argument("--lat-field")
    parser.add_argument("--lon-field")
    parser.add_argument("--verification-field")
    parser.add_argument("--accept-verification", action="append")
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()

    payload = args.csv.read_bytes()
    if args.inspect_fields:
        for field in inspect_csv_fields(payload):
            print(field)
        return 0

    if args.bbox is None or not args.lat_field or not args.lon_field:
        parser.error(
            "selection requires --bbox, --lat-field, and --lon-field; "
            "use --inspect-fields first for a new live fixture"
        )

    result = select_ddof_csv_context(
        payload,
        bbox=args.bbox,
        latitude_field=args.lat_field,
        longitude_field=args.lon_field,
        verification_field=args.verification_field,
        accepted_verification_values=args.accept_verification,
    )
    output = json.dumps(result.to_json_dict(), indent=2, sort_keys=True) + "\n"
    if args.result:
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
