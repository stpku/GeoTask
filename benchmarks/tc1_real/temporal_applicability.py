"""TC1-Real M3 temporal applicability over recorded HRRR evidence.

This module deliberately remains in the benchmark layer.  GeoTask Core v0.1
compares opaque temporal-scope references exactly; it does not interpret UTC
instants or intervals.  The adapter therefore performs the real timestamp
check first and only normalizes an applicable provider artifact to the task's
opaque scope reference.

The design is intentionally fail-closed: malformed or missing validity fields
raise rather than being treated as current context.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Mapping

from geotask_core.task_context import (
    CandidateContextAssessment,
    ContextCandidate,
    ContextRequirement,
    TaskContext,
    TaskFrame,
    assess_task_context,
    evaluate_context_candidate,
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


M3_WINDOW_START = "2026-08-18T10:00:00Z"
M3_WINDOW_END = "2026-08-18T11:00:00Z"
M3_CONTROL_VALID_TIME = "2026-08-18T10:00:00Z"
M3_MISMATCH_VALID_TIME = "2026-08-18T08:00:00Z"


@dataclass(frozen=True)
class TemporalWindow:
    start: str
    end: str

    def __post_init__(self) -> None:
        if _parse_utc(self.start) >= _parse_utc(self.end):
            raise ValueError("temporal window start must be before end")

    def contains_instant(self, value: str) -> bool:
        instant = _parse_utc(value)
        return _parse_utc(self.start) <= instant < _parse_utc(self.end)


@dataclass(frozen=True)
class TemporalApplicability:
    valid_from: str
    valid_until: str
    applicable: bool
    reason: str
    task_window_start: str
    task_window_end: str


@dataclass(frozen=True)
class M3TemporalAssessment:
    policy: str
    context: TaskContext
    weather_candidate: ContextCandidate
    applicability: TemporalApplicability
    weather_assessments: tuple[CandidateContextAssessment, ...]


@dataclass(frozen=True)
class M3TemporalComparison:
    cost_projection: str
    control: M3TemporalAssessment
    mismatch: M3TemporalAssessment


def _parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("UTC timestamp must be a non-empty string")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"invalid ISO-8601 timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise ValueError("UTC timestamp must include timezone information")
    return parsed.astimezone(timezone.utc)


def _load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"recorded fixture must be a JSON object: {path}")
    return value


def _require_projection(cost_projection: str) -> None:
    if cost_projection not in SUPPORTED_COST_PROJECTIONS:
        raise ValueError("unsupported TC1-Real cost projection")


def evaluate_temporal_applicability(
    record: Mapping[str, object],
    *,
    window: TemporalWindow,
) -> TemporalApplicability:
    provenance = record.get("provenance")
    if not isinstance(provenance, Mapping):
        raise ValueError("recorded provenance must be a mapping")

    valid_from = provenance.get("valid_from")
    valid_until = provenance.get("valid_until")
    if not isinstance(valid_from, str) or not isinstance(valid_until, str):
        raise ValueError("recorded validity must include valid_from and valid_until")

    start = _parse_utc(valid_from)
    end = _parse_utc(valid_until)
    if end < start:
        raise ValueError("recorded valid_until must not precede valid_from")

    task_start = _parse_utc(window.start)
    task_end = _parse_utc(window.end)
    if start == end:
        applicable = window.contains_instant(valid_from)
    else:
        # Source validity is treated as a closed interval while the benchmark
        # task window is [start, end).  Any overlap is sufficient for this M3
        # applicability check; stronger coverage semantics are not inferred.
        applicable = start < task_end and end >= task_start

    if applicable:
        reason = "validity_overlaps_task_window"
    elif end < task_start:
        reason = "validity_before_task_window"
    else:
        reason = "validity_after_task_window"

    return TemporalApplicability(
        valid_from=valid_from,
        valid_until=valid_until,
        applicable=applicable,
        reason=reason,
        task_window_start=window.start,
        task_window_end=window.end,
    )


def normalize_hrrr_temporal_candidate(
    record: Mapping[str, object],
    *,
    candidate_id: str,
    required_temporal_scope: str,
    window: TemporalWindow,
    cost_projection: str,
) -> tuple[ContextCandidate, TemporalApplicability]:
    _require_projection(cost_projection)
    provenance = record.get("provenance")
    measurement = record.get("measurement")
    if not isinstance(provenance, Mapping) or not isinstance(measurement, Mapping):
        raise ValueError("recorded HRRR record must include provenance and measurement")
    if provenance.get("source_id") != "noaa-hrrr":
        raise ValueError("M3 temporal candidate must come from noaa-hrrr")

    params = provenance.get("request_parameters")
    if not isinstance(params, Mapping):
        raise ValueError("recorded HRRR request_parameters must be a mapping")
    expected_bbox = [-112.1, 33.4, -112.0, 33.5]
    if params.get("bbox") != expected_bbox:
        raise ValueError("M3 HRRR fixture bbox does not match frozen task bbox")
    if params.get("variables") != ["UGRD", "VGRD", "VIS"]:
        raise ValueError("M3 HRRR fixture variables do not match frozen requirements")
    if params.get("levels") != ["10_m_above_ground", "surface"]:
        raise ValueError("M3 HRRR fixture levels do not match frozen requirements")

    bytes_transferred = measurement.get("bytes_transferred")
    if not isinstance(bytes_transferred, int) or bytes_transferred <= 0:
        raise ValueError("recorded HRRR bytes_transferred must be a positive integer")

    applicability = evaluate_temporal_applicability(record, window=window)
    temporal_scope = (
        required_temporal_scope
        if applicability.applicable
        else f"outside-task-window:{applicability.valid_from}"
    )

    candidate = ContextCandidate(
        candidate_id=candidate_id,
        source="noaa-hrrr",
        requirement_ids=("weather_wind", "weather_visibility"),
        spatial_scope=EXPERIMENT_SPATIAL_SCOPE,
        temporal_scope=temporal_scope,
        spatial_resolution=3000.0,
        spatial_resolution_unit="meter",
        temporal_resolution_seconds=3600.0,
        acquisition_cost=float(bytes_transferred),
        cost_unit=cost_projection,
        metadata={
            "source_hash": provenance.get("content_sha256"),
            "run_time": provenance.get("source_effective_at"),
            "valid_from": applicability.valid_from,
            "valid_until": applicability.valid_until,
            "task_window_start": applicability.task_window_start,
            "task_window_end": applicability.task_window_end,
            "temporal_applicable": applicability.applicable,
            "temporal_applicability_reason": applicability.reason,
            "network_bytes": bytes_transferred,
            "carried_bytes": bytes_transferred,
        },
    )
    return candidate, applicability


def _accepted_requirements() -> tuple[ContextRequirement, ...]:
    case = get_tc1_real_case("M3-weather-temporal-mismatch")
    return tuple(
        item.requirement
        for item in case.reference_requirements
        if item.grading_state == "accepted"
    )


def _m3_task(cost_projection: str) -> TaskFrame:
    _require_projection(cost_projection)
    case = get_tc1_real_case("M3-weather-temporal-mismatch")
    return TaskFrame(
        task_id=f"{case.task.task_id}:{cost_projection}",
        goal=case.task.goal,
        subject_refs=case.task.subject_refs,
        spatial_scope=case.task.spatial_scope,
        temporal_scope=RECORDED_WINDOW,
        outputs=case.task.outputs,
    )


def _weather_assessments(
    task: TaskFrame,
    requirements: tuple[ContextRequirement, ...],
    candidate: ContextCandidate,
) -> tuple[CandidateContextAssessment, ...]:
    return tuple(
        evaluate_context_candidate(task, requirement, candidate)
        for requirement in requirements
        if requirement.requirement_id in {"weather_wind", "weather_visibility"}
    )


def assess_recorded_m3(
    fixture_root: Path,
    *,
    cost_projection: str = CARRIED_BYTES,
) -> M3TemporalComparison:
    """Compare real in-window and real wrong-valid-time HRRR evidence.

    Non-weather context is held fixed using the recorded M1 RG candidates.  The
    two HRRR artifacts share source/run/bbox/variables/levels; their forecast
    hour and therefore valid time differ.  M3 succeeds only if the accepted
    10Z artifact yields full sufficiency while the real 08Z artifact leaves the
    two critical weather requirements as gaps.
    """

    _require_projection(cost_projection)
    task = _m3_task(cost_projection)
    requirements = _accepted_requirements()
    window = TemporalWindow(M3_WINDOW_START, M3_WINDOW_END)

    base_candidates = _normalize_rg_candidates(fixture_root, cost_projection)
    non_weather = tuple(
        candidate for candidate in base_candidates if candidate.source != "noaa-hrrr"
    )
    if len(non_weather) != 2:
        raise ValueError("M3 expects exactly two fixed non-weather M1 RG candidates")

    control_record = _load(
        fixture_root / "hrrr_phx_20260818" / "hrrr-task.record.json"
    )
    mismatch_record = _load(
        fixture_root
        / "hrrr_phx_m3_wrong_time_20260818"
        / "hrrr-m3-wrong-time.record.json"
    )

    control_candidate, control_applicability = normalize_hrrr_temporal_candidate(
        control_record,
        candidate_id="m3-hrrr-control-10z",
        required_temporal_scope=RECORDED_WINDOW,
        window=window,
        cost_projection=cost_projection,
    )
    mismatch_candidate, mismatch_applicability = normalize_hrrr_temporal_candidate(
        mismatch_record,
        candidate_id="m3-hrrr-mismatch-08z",
        required_temporal_scope=RECORDED_WINDOW,
        window=window,
        cost_projection=cost_projection,
    )

    control_context = assess_task_context(
        task,
        requirements,
        (*non_weather, control_candidate),
    )
    mismatch_context = assess_task_context(
        task,
        requirements,
        (*non_weather, mismatch_candidate),
    )

    control = M3TemporalAssessment(
        policy="M3/control-valid-10z",
        context=control_context,
        weather_candidate=control_candidate,
        applicability=control_applicability,
        weather_assessments=_weather_assessments(
            task, requirements, control_candidate
        ),
    )
    mismatch = M3TemporalAssessment(
        policy="M3/real-wrong-valid-time-08z",
        context=mismatch_context,
        weather_candidate=mismatch_candidate,
        applicability=mismatch_applicability,
        weather_assessments=_weather_assessments(
            task, requirements, mismatch_candidate
        ),
    )

    expected_weather_gaps = {"weather_wind", "weather_visibility"}
    if not control.context.sufficient:
        raise ValueError("M3 control context must remain sufficient")
    if set(control.context.gap_requirement_ids):
        raise ValueError("M3 control context must have no gaps")
    if mismatch.context.status != "insufficient":
        raise ValueError("M3 wrong-valid-time context must be insufficient")
    if set(mismatch.context.gap_requirement_ids) != expected_weather_gaps:
        raise ValueError("M3 mismatch must gap exactly the two weather requirements")
    if control.applicability.valid_from != M3_CONTROL_VALID_TIME:
        raise ValueError("M3 control valid time changed")
    if mismatch.applicability.valid_from != M3_MISMATCH_VALID_TIME:
        raise ValueError("M3 mismatch valid time changed")
    if not control.applicability.applicable or mismatch.applicability.applicable:
        raise ValueError("M3 temporal applicability verdicts do not match the frozen case")

    for assessment in mismatch.weather_assessments:
        if assessment.reasons != ("temporal_scope_mismatch",):
            raise ValueError("M3 mismatch must fail at the temporal scope boundary only")

    return M3TemporalComparison(
        cost_projection=cost_projection,
        control=control,
        mismatch=mismatch,
    )


__all__ = [
    "CARRIED_BYTES",
    "M3_CONTROL_VALID_TIME",
    "M3_MISMATCH_VALID_TIME",
    "M3_WINDOW_END",
    "M3_WINDOW_START",
    "M3TemporalAssessment",
    "M3TemporalComparison",
    "NETWORK_BYTES",
    "TemporalApplicability",
    "TemporalWindow",
    "assess_recorded_m3",
    "evaluate_temporal_applicability",
    "normalize_hrrr_temporal_candidate",
]
