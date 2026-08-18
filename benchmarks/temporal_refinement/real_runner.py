"""Offline runner for the real temporal Sufficiency-Guided Refinement proof."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Mapping

from benchmarks.temporal_refinement.envelope_policy import (
    HourlyWeather,
    TemporalRefinementTrace,
    evaluate_temporal_refinement,
)
from benchmarks.temporal_refinement.experiment_spec import (
    FINE_PERIOD_COUNT,
    PRECIP_PROBABILITY_THRESHOLDS_PERCENT,
    TASK_ACTION_AVAILABLE,
    TASK_WINDOW_COUNT,
    TASK_WINDOW_HOURS,
    TEMPORAL_LADDER_HOURS,
    WIND_THRESHOLDS_KMH,
)


FLOAT32_BYTES = 4


@dataclass(frozen=True)
class TemporalCaseResult:
    window_index: int
    wind_threshold_kmh: float
    precip_threshold_percent: float
    fine_reference_action: str
    final_action: str
    final_resolution_hours: int
    refined: bool
    unsafe_stop: bool
    payload_float_count: int
    always_hourly_payload_float_count: int
    trace: TemporalRefinementTrace


@dataclass(frozen=True)
class TemporalRealSummary:
    total_cases: int
    coarse_stop_case_count: int
    refinement_case_count: int
    unsafe_stop_count: int
    unnecessary_refinement_count: int
    final_resolution_counts: Mapping[str, int]
    adaptive_payload_float_count: int
    always_hourly_payload_float_count: int
    adaptive_context_payload_bytes: int
    always_hourly_context_payload_bytes: int
    context_payload_reduction_ratio: float
    mandatory_stop_control_present: bool
    mandatory_refine_control_present: bool
    cross_domain_stress_gate_pass: bool
    cases: tuple[TemporalCaseResult, ...]


def load_pinned_hourly_fixture(path: Path) -> tuple[HourlyWeather, ...]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("temporal fixture must be a mapping")
    if document.get("stage") != "HOURLY_REFERENCE_ACQUIRED":
        raise ValueError("temporal fixture is not in acquired state")
    periods = document.get("periods")
    if not isinstance(periods, list) or len(periods) != FINE_PERIOD_COUNT:
        raise ValueError("temporal fixture does not contain the frozen 24 hours")

    result: list[HourlyWeather] = []
    for index, item in enumerate(periods):
        if not isinstance(item, dict):
            raise ValueError(f"temporal fixture period {index} is not a mapping")
        result.append(
            HourlyWeather(
                wind_kmh=float(item["wind_kmh"]),
                precip_probability_percent=float(item["precip_probability_percent"]),
            )
        )
    return tuple(result)


def _fine_action(
    hourly: tuple[HourlyWeather, ...],
    *,
    wind_threshold_kmh: float,
    precip_threshold_percent: float,
) -> str:
    return (
        TASK_ACTION_AVAILABLE
        if any(
            item.wind_kmh <= wind_threshold_kmh
            and item.precip_probability_percent <= precip_threshold_percent
            for item in hourly
        )
        else "STOP_UNAVAILABLE"
    )


def run_temporal_real_stress(fixture_path: Path) -> TemporalRealSummary:
    fine = load_pinned_hourly_fixture(fixture_path)
    if len(fine) != TASK_WINDOW_COUNT * TASK_WINDOW_HOURS:
        raise ValueError("frozen hourly reference does not match task-window layout")

    cases: list[TemporalCaseResult] = []
    for window_index in range(TASK_WINDOW_COUNT):
        start = window_index * TASK_WINDOW_HOURS
        window = fine[start : start + TASK_WINDOW_HOURS]
        for wind_threshold in WIND_THRESHOLDS_KMH:
            for precip_threshold in PRECIP_PROBABILITY_THRESHOLDS_PERCENT:
                trace = evaluate_temporal_refinement(
                    window,
                    wind_threshold_kmh=wind_threshold,
                    precip_threshold_percent=precip_threshold,
                    ladder_hours=TEMPORAL_LADDER_HOURS,
                )
                reference_action = _fine_action(
                    window,
                    wind_threshold_kmh=wind_threshold,
                    precip_threshold_percent=precip_threshold,
                )
                cases.append(
                    TemporalCaseResult(
                        window_index=window_index,
                        wind_threshold_kmh=wind_threshold,
                        precip_threshold_percent=precip_threshold,
                        fine_reference_action=reference_action,
                        final_action=trace.final_action,
                        final_resolution_hours=trace.final_resolution_hours,
                        refined=trace.refined,
                        unsafe_stop=trace.final_action != reference_action,
                        payload_float_count=trace.payload_float_count,
                        always_hourly_payload_float_count=trace.always_hourly_payload_float_count,
                        trace=trace,
                    )
                )

    frozen = tuple(cases)
    coarse_stop = sum(not case.refined for case in frozen)
    refined = sum(case.refined for case in frozen)
    unsafe = sum(case.unsafe_stop for case in frozen)
    unnecessary = sum(
        case.refined and case.trace.steps[0].action != "REFINE" for case in frozen
    )
    final_counts = Counter(str(case.final_resolution_hours) for case in frozen)
    adaptive_floats = sum(case.payload_float_count for case in frozen)
    hourly_floats = sum(case.always_hourly_payload_float_count for case in frozen)
    adaptive_bytes = adaptive_floats * FLOAT32_BYTES
    hourly_bytes = hourly_floats * FLOAT32_BYTES
    reduction = 0.0 if hourly_bytes == 0 else 1.0 - adaptive_bytes / hourly_bytes
    stop_present = coarse_stop > 0
    refine_present = refined > 0

    return TemporalRealSummary(
        total_cases=len(frozen),
        coarse_stop_case_count=coarse_stop,
        refinement_case_count=refined,
        unsafe_stop_count=unsafe,
        unnecessary_refinement_count=unnecessary,
        final_resolution_counts=dict(
            sorted(final_counts.items(), key=lambda item: int(item[0]), reverse=True)
        ),
        adaptive_payload_float_count=adaptive_floats,
        always_hourly_payload_float_count=hourly_floats,
        adaptive_context_payload_bytes=adaptive_bytes,
        always_hourly_context_payload_bytes=hourly_bytes,
        context_payload_reduction_ratio=reduction,
        mandatory_stop_control_present=stop_present,
        mandatory_refine_control_present=refine_present,
        cross_domain_stress_gate_pass=(
            stop_present and refine_present and unsafe == 0 and unnecessary == 0
        ),
        cases=frozen,
    )


def summary_to_jsonable(summary: TemporalRealSummary) -> dict[str, object]:
    return asdict(summary)
