"""TC1-Real M4 semantic weather breadth over recorded HRRR evidence.

M4 holds source, model run, valid time, spatial bbox, and frozen critical
requirements constant.  It compares the accepted task-specific HRRR request
against a real request that strictly includes extra variables/levels.

The headline reduction is deliberately provider-local: it is the HRRR payload
byte reduction, not total task-context cost, token count, or decision quality.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Mapping

from geotask_core.task_context import (
    ContextCandidate,
    ContextRequirement,
    TaskContext,
    TaskFrame,
    assess_task_context,
)

from benchmarks.tc1_real.experiment_cases import (
    EXPERIMENT_SPATIAL_SCOPE,
    get_tc1_real_case,
)
from benchmarks.tc1_real.recorded_context import (
    CARRIED_BYTES,
    NETWORK_BYTES,
    RECORDED_WINDOW,
    SUPPORTED_COST_PROJECTIONS,
    _normalize_rg_candidates,
)


@dataclass(frozen=True)
class M4WeatherBreadth:
    candidate_id: str
    payload_bytes: int
    variables: tuple[str, ...]
    levels: tuple[str, ...]
    extra_variables: tuple[str, ...]
    extra_levels: tuple[str, ...]
    context: TaskContext


@dataclass(frozen=True)
class M4SemanticBreadthComparison:
    cost_projection: str
    narrow: M4WeatherBreadth
    broad: M4WeatherBreadth
    weather_payload_reduction_ratio: float


def _load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"recorded fixture must be a JSON object: {path}")
    return value


def _require_projection(cost_projection: str) -> None:
    if cost_projection not in SUPPORTED_COST_PROJECTIONS:
        raise ValueError("unsupported TC1-Real cost projection")


def _accepted_requirements() -> tuple[ContextRequirement, ...]:
    case = get_tc1_real_case("M4-unnecessary-weather-breadth")
    return tuple(
        item.requirement
        for item in case.reference_requirements
        if item.grading_state == "accepted"
    )


def _m4_task(cost_projection: str) -> TaskFrame:
    _require_projection(cost_projection)
    case = get_tc1_real_case("M4-unnecessary-weather-breadth")
    return TaskFrame(
        task_id=f"{case.task.task_id}:{cost_projection}",
        goal=case.task.goal,
        subject_refs=case.task.subject_refs,
        spatial_scope=case.task.spatial_scope,
        temporal_scope=RECORDED_WINDOW,
        outputs=case.task.outputs,
    )


def _record_parts(record: Mapping[str, object]) -> tuple[Mapping[str, object], Mapping[str, object], Mapping[str, object]]:
    provenance = record.get("provenance")
    measurement = record.get("measurement")
    if not isinstance(provenance, Mapping) or not isinstance(measurement, Mapping):
        raise ValueError("recorded HRRR record must include provenance and measurement")
    params = provenance.get("request_parameters")
    if not isinstance(params, Mapping):
        raise ValueError("recorded HRRR request_parameters must be a mapping")
    if provenance.get("source_id") != "noaa-hrrr":
        raise ValueError("M4 weather records must come from noaa-hrrr")
    return provenance, measurement, params


def _sequence(params: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = params.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"recorded HRRR {key} must be a string list")
    return tuple(value)


def _payload_bytes(measurement: Mapping[str, object]) -> int:
    value = measurement.get("bytes_transferred")
    if not isinstance(value, int) or value <= 0:
        raise ValueError("recorded HRRR bytes_transferred must be a positive integer")
    return value


def _verify_comparable_records(
    narrow_record: Mapping[str, object],
    broad_record: Mapping[str, object],
) -> tuple[
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    int,
    int,
]:
    narrow_prov, narrow_measurement, narrow_params = _record_parts(narrow_record)
    broad_prov, broad_measurement, broad_params = _record_parts(broad_record)

    for key in ("date", "cycle_utc", "forecast_hour", "bbox"):
        if narrow_params.get(key) != broad_params.get(key):
            raise ValueError(f"M4 HRRR {key} changed between narrow and broad records")
    for key in ("source_effective_at", "valid_from", "valid_until"):
        if narrow_prov.get(key) != broad_prov.get(key):
            raise ValueError(f"M4 HRRR {key} changed between narrow and broad records")

    narrow_vars = _sequence(narrow_params, "variables")
    broad_vars = _sequence(broad_params, "variables")
    narrow_levels = _sequence(narrow_params, "levels")
    broad_levels = _sequence(broad_params, "levels")

    narrow_var_set = set(narrow_vars)
    broad_var_set = set(broad_vars)
    narrow_level_set = set(narrow_levels)
    broad_level_set = set(broad_levels)
    if not narrow_var_set < broad_var_set:
        raise ValueError("M4 broad variables must strictly contain the narrow variables")
    if not narrow_level_set < broad_level_set:
        raise ValueError("M4 broad levels must strictly contain the narrow levels")

    expected_vars = {"UGRD", "VGRD", "VIS"}
    expected_levels = {"10_m_above_ground", "surface"}
    if narrow_var_set != expected_vars:
        raise ValueError("M4 narrow variables changed from the frozen requirement set")
    if narrow_level_set != expected_levels:
        raise ValueError("M4 narrow levels changed from the frozen requirement set")

    return (
        narrow_vars,
        narrow_levels,
        tuple(sorted(broad_var_set - narrow_var_set)),
        tuple(sorted(broad_level_set - narrow_level_set)),
        _payload_bytes(narrow_measurement),
        _payload_bytes(broad_measurement),
    )


def _broad_candidate(
    record: Mapping[str, object],
    *,
    payload_bytes: int,
    cost_projection: str,
    extra_variables: tuple[str, ...],
    extra_levels: tuple[str, ...],
) -> ContextCandidate:
    provenance, _, _ = _record_parts(record)
    return ContextCandidate(
        candidate_id="m4-hrrr-broad-weather",
        source="noaa-hrrr",
        requirement_ids=("weather_wind", "weather_visibility"),
        spatial_scope=EXPERIMENT_SPATIAL_SCOPE,
        temporal_scope=RECORDED_WINDOW,
        spatial_resolution=3000.0,
        spatial_resolution_unit="meter",
        temporal_resolution_seconds=3600.0,
        acquisition_cost=float(payload_bytes),
        cost_unit=cost_projection,
        metadata={
            "source_hash": provenance.get("content_sha256"),
            "run_time": provenance.get("source_effective_at"),
            "valid_time": provenance.get("valid_from"),
            "network_bytes": payload_bytes,
            "carried_bytes": payload_bytes,
            "extra_variables": extra_variables,
            "extra_levels": extra_levels,
            "extra_content_is_not_extra_requirement_coverage": True,
        },
    )


def assess_recorded_m4(
    fixture_root: Path,
    *,
    cost_projection: str = CARRIED_BYTES,
) -> M4SemanticBreadthComparison:
    """Compare real narrow and semantically broader HRRR payloads.

    UASFM/DDOF context is held fixed.  Both contexts must cover the same frozen
    critical requirements.  The headline ratio compares only the two HRRR
    payloads; full-context totals are intentionally not used as an M4 headline.
    """

    _require_projection(cost_projection)
    task = _m4_task(cost_projection)
    requirements = _accepted_requirements()

    base_candidates = _normalize_rg_candidates(fixture_root, cost_projection)
    non_weather = tuple(
        candidate for candidate in base_candidates if candidate.source != "noaa-hrrr"
    )
    narrow_weather = tuple(
        candidate for candidate in base_candidates if candidate.source == "noaa-hrrr"
    )
    if len(non_weather) != 2 or len(narrow_weather) != 1:
        raise ValueError("M4 expects the recorded M1 RG provider composition")
    narrow_candidate = narrow_weather[0]

    narrow_record = _load(
        fixture_root / "hrrr_phx_20260818" / "hrrr-task.record.json"
    )
    broad_record = _load(
        fixture_root
        / "hrrr_phx_m4_broad_20260818"
        / "hrrr-m4-broad-weather.record.json"
    )
    (
        narrow_vars,
        narrow_levels,
        extra_vars,
        extra_levels,
        narrow_bytes,
        broad_bytes,
    ) = _verify_comparable_records(narrow_record, broad_record)

    if int(narrow_candidate.acquisition_cost) != narrow_bytes:
        raise ValueError("M4 narrow candidate burden is not bound to recorded bytes")
    if broad_bytes <= narrow_bytes:
        raise ValueError("M4 broad HRRR payload must be larger than the narrow payload")

    broad_candidate = _broad_candidate(
        broad_record,
        payload_bytes=broad_bytes,
        cost_projection=cost_projection,
        extra_variables=extra_vars,
        extra_levels=extra_levels,
    )

    narrow_context = assess_task_context(
        task,
        requirements,
        (*non_weather, narrow_candidate),
    )
    broad_context = assess_task_context(
        task,
        requirements,
        (*non_weather, broad_candidate),
    )
    if not narrow_context.sufficient or not broad_context.sufficient:
        raise ValueError("M4 narrow and broad contexts must both remain sufficient")
    if narrow_context.gap_requirement_ids or broad_context.gap_requirement_ids:
        raise ValueError("M4 comparison must not change frozen requirement coverage")

    narrow_coverage = {
        item.requirement_id: bool(item.candidate_ids)
        for item in narrow_context.coverage
    }
    broad_coverage = {
        item.requirement_id: bool(item.candidate_ids)
        for item in broad_context.coverage
    }
    if narrow_coverage != broad_coverage:
        raise ValueError("M4 semantic breadth must not change requirement coverage")

    broad_params = _record_parts(broad_record)[2]
    broad_vars = _sequence(broad_params, "variables")
    broad_levels = _sequence(broad_params, "levels")

    return M4SemanticBreadthComparison(
        cost_projection=cost_projection,
        narrow=M4WeatherBreadth(
            candidate_id=narrow_candidate.candidate_id,
            payload_bytes=narrow_bytes,
            variables=narrow_vars,
            levels=narrow_levels,
            extra_variables=(),
            extra_levels=(),
            context=narrow_context,
        ),
        broad=M4WeatherBreadth(
            candidate_id=broad_candidate.candidate_id,
            payload_bytes=broad_bytes,
            variables=broad_vars,
            levels=broad_levels,
            extra_variables=extra_vars,
            extra_levels=extra_levels,
            context=broad_context,
        ),
        weather_payload_reduction_ratio=1.0 - (narrow_bytes / broad_bytes),
    )


__all__ = [
    "CARRIED_BYTES",
    "M4SemanticBreadthComparison",
    "M4WeatherBreadth",
    "NETWORK_BYTES",
    "assess_recorded_m4",
]
