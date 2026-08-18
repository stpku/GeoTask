"""Offline comparison for the recorded TC1-Real HRRR task/R0 pair.

The result is only comparable when both records use the same source, run,
forecast hour, variables, levels, and valid time, and the broader R0 bbox
contains the task bbox.  Single-request wall-clock values are preserved as
observations but are not treated as stable latency claims.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class HRRRRealComparison:
    task_bytes: int
    r0_bytes: int
    byte_reduction_ratio: float
    task_wall_clock_seconds: float
    r0_wall_clock_seconds: float
    observed_wall_clock_reduction_ratio: float
    run_time: str
    valid_time: str
    variables: tuple[str, ...]
    levels: tuple[str, ...]
    task_bbox: tuple[float, float, float, float]
    r0_bbox: tuple[float, float, float, float]


def _bbox(value: Sequence[object], name: str) -> tuple[float, float, float, float]:
    if len(value) != 4:
        raise ValueError(f"{name} must contain four coordinates")
    result = tuple(float(item) for item in value)
    min_lon, min_lat, max_lon, max_lat = result
    if min_lon >= max_lon or min_lat >= max_lat:
        raise ValueError(f"{name} has invalid bounds")
    return result  # type: ignore[return-value]


def _contains(
    outer: tuple[float, float, float, float],
    inner: tuple[float, float, float, float],
) -> bool:
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and outer[2] >= inner[2]
        and outer[3] >= inner[3]
    )


def compare_recorded_hrrr(
    *,
    task_record: Mapping[str, object],
    r0_record: Mapping[str, object],
) -> HRRRRealComparison:
    task_provenance = task_record.get("provenance")
    r0_provenance = r0_record.get("provenance")
    task_measurement = task_record.get("measurement")
    r0_measurement = r0_record.get("measurement")
    if not isinstance(task_provenance, Mapping) or not isinstance(r0_provenance, Mapping):
        raise ValueError("both HRRR records must contain provenance mappings")
    if not isinstance(task_measurement, Mapping) or not isinstance(r0_measurement, Mapping):
        raise ValueError("both HRRR records must contain measurement mappings")

    for field in ("source_id", "source_family", "source_effective_at", "valid_from", "valid_until"):
        if task_provenance.get(field) != r0_provenance.get(field):
            raise ValueError(f"HRRR acquisitions differ in {field}")

    task_params = task_provenance.get("request_parameters")
    r0_params = r0_provenance.get("request_parameters")
    if not isinstance(task_params, Mapping) or not isinstance(r0_params, Mapping):
        raise ValueError("both HRRR records must contain request_parameters")

    for field in ("date", "cycle_utc", "forecast_hour", "variables", "levels"):
        if task_params.get(field) != r0_params.get(field):
            raise ValueError(f"HRRR acquisitions differ in request {field}")

    task_bbox = _bbox(task_params["bbox"], "task bbox")  # type: ignore[arg-type]
    r0_bbox = _bbox(r0_params["bbox"], "R0 bbox")  # type: ignore[arg-type]
    if not _contains(r0_bbox, task_bbox):
        raise ValueError("HRRR R0 bbox must contain the task bbox")

    task_bytes = int(task_measurement["bytes_transferred"])
    r0_bytes = int(r0_measurement["bytes_transferred"])
    task_wall = float(task_measurement["wall_clock_seconds"])
    r0_wall = float(r0_measurement["wall_clock_seconds"])
    if task_bytes <= 0 or r0_bytes <= 0:
        raise ValueError("HRRR byte measurements must be > 0")
    if task_wall <= 0 or r0_wall <= 0:
        raise ValueError("HRRR wall-clock measurements must be > 0")
    if task_bytes > r0_bytes:
        raise ValueError("task HRRR payload cannot exceed containing R0 payload")

    return HRRRRealComparison(
        task_bytes=task_bytes,
        r0_bytes=r0_bytes,
        byte_reduction_ratio=1.0 - (task_bytes / r0_bytes),
        task_wall_clock_seconds=task_wall,
        r0_wall_clock_seconds=r0_wall,
        observed_wall_clock_reduction_ratio=1.0 - (task_wall / r0_wall),
        run_time=str(task_provenance["source_effective_at"]),
        valid_time=str(task_provenance["valid_from"]),
        variables=tuple(str(item) for item in task_params["variables"]),  # type: ignore[index]
        levels=tuple(str(item) for item in task_params["levels"]),  # type: ignore[index]
        task_bbox=task_bbox,
        r0_bbox=r0_bbox,
    )
