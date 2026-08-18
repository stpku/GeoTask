"""Offline comparison for the first recorded TC1-Real UASFM acquisitions.

The comparison is intentionally narrow. It compares a task-bounded request with
a broader regional request only when source identity, format, and requested
fields are the same and the task bbox is contained by the R0 bbox.

Single-run wall-clock observations are reported but are not treated as stable
latency-performance claims.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from geotask_core.spatial_scope import rect_contains_rect


@dataclass(frozen=True)
class UASFMRealComparison:
    task_feature_count: int
    r0_feature_count: int
    task_payload_bytes: int
    r0_payload_bytes: int
    task_wall_clock_seconds: float
    r0_wall_clock_seconds: float
    feature_reduction_ratio: float
    byte_reduction_ratio: float
    observed_wall_clock_reduction_ratio: float
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


def _positive_int(value: object, name: str) -> int:
    result = int(value)
    if result <= 0:
        raise ValueError(f"{name} must be > 0")
    return result


def _positive_float(value: object, name: str) -> float:
    result = float(value)
    if result <= 0:
        raise ValueError(f"{name} must be > 0")
    return result


def compare_recorded_uasfm(
    *,
    task_summary: Mapping[str, object],
    task_record: Mapping[str, object],
    r0_summary: Mapping[str, object],
    r0_record: Mapping[str, object],
) -> UASFMRealComparison:
    """Compare two recorded UASFM acquisitions after comparability checks."""

    task_provenance = task_record["provenance"]
    r0_provenance = r0_record["provenance"]
    if not isinstance(task_provenance, Mapping) or not isinstance(r0_provenance, Mapping):
        raise ValueError("both records must contain provenance mappings")

    for field in ("source_id", "source_family", "source_crs"):
        if task_provenance.get(field) != r0_provenance.get(field):
            raise ValueError(f"UASFM acquisitions differ in {field}")

    task_params = task_provenance.get("request_parameters")
    r0_params = r0_provenance.get("request_parameters")
    if not isinstance(task_params, Mapping) or not isinstance(r0_params, Mapping):
        raise ValueError("both records must contain request_parameters")

    for field in ("format", "out_fields"):
        if task_params.get(field) != r0_params.get(field):
            raise ValueError(f"UASFM acquisitions differ in request {field}")

    task_bbox = _bbox(task_summary["bbox"], "task bbox")  # type: ignore[arg-type]
    r0_bbox = _bbox(r0_summary["bbox"], "R0 bbox")  # type: ignore[arg-type]
    if not rect_contains_rect(r0_bbox, task_bbox):
        raise ValueError("R0 bbox must contain the task bbox")

    task_features = _positive_int(task_summary["feature_count"], "task feature_count")
    r0_features = _positive_int(r0_summary["feature_count"], "R0 feature_count")
    task_bytes = _positive_int(task_summary["payload_bytes"], "task payload_bytes")
    r0_bytes = _positive_int(r0_summary["payload_bytes"], "R0 payload_bytes")
    task_wall = _positive_float(
        task_summary["wall_clock_seconds"], "task wall_clock_seconds"
    )
    r0_wall = _positive_float(
        r0_summary["wall_clock_seconds"], "R0 wall_clock_seconds"
    )

    if task_features > r0_features:
        raise ValueError("task feature_count cannot exceed containing R0 feature_count")
    if task_bytes > r0_bytes:
        raise ValueError("task payload_bytes cannot exceed containing R0 payload_bytes")

    return UASFMRealComparison(
        task_feature_count=task_features,
        r0_feature_count=r0_features,
        task_payload_bytes=task_bytes,
        r0_payload_bytes=r0_bytes,
        task_wall_clock_seconds=task_wall,
        r0_wall_clock_seconds=r0_wall,
        feature_reduction_ratio=1.0 - (task_features / r0_features),
        byte_reduction_ratio=1.0 - (task_bytes / r0_bytes),
        observed_wall_clock_reduction_ratio=1.0 - (task_wall / r0_wall),
        task_bbox=task_bbox,
        r0_bbox=r0_bbox,
    )
