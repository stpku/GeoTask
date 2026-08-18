"""Selective temporal refinement policy for the cross-domain proof.

This is benchmark-layer method evidence, not a promoted GeoTask Core algorithm.
It uses hourly wind/precipitation values as a pinned fine reference and derives
conservative temporal envelopes locally.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

from benchmarks.temporal_refinement.experiment_spec import (
    TASK_ACTION_AVAILABLE,
    TASK_ACTION_REFINE,
    TASK_ACTION_UNAVAILABLE,
)


BLOCK_AVAILABLE = "AVAILABLE"
BLOCK_UNAVAILABLE = "UNAVAILABLE"
BLOCK_AMBIGUOUS = "AMBIGUOUS"


@dataclass(frozen=True)
class HourlyWeather:
    wind_kmh: float
    precip_probability_percent: float

    def __post_init__(self) -> None:
        if not isfinite(self.wind_kmh) or self.wind_kmh < 0:
            raise ValueError("wind_kmh must be finite and >= 0")
        if (
            not isfinite(self.precip_probability_percent)
            or self.precip_probability_percent < 0
            or self.precip_probability_percent > 100
        ):
            raise ValueError("precip_probability_percent must be within [0, 100]")


@dataclass(frozen=True)
class TemporalBlockEnvelope:
    start_hour: int
    end_hour: int
    wind_min_kmh: float
    wind_max_kmh: float
    precip_min_percent: float
    precip_max_percent: float

    @property
    def duration_hours(self) -> int:
        return self.end_hour - self.start_hour


@dataclass(frozen=True)
class TemporalBlockAssessment:
    envelope: TemporalBlockEnvelope
    status: str


@dataclass(frozen=True)
class TemporalRefinementStep:
    resolution_hours: int
    newly_evaluated_block_count: int
    ambiguous_block_count: int
    unavailable_block_count: int
    available_block_count: int
    cumulative_payload_float_count: int
    action: str


@dataclass(frozen=True)
class TemporalRefinementTrace:
    wind_threshold_kmh: float
    precip_threshold_percent: float
    final_action: str
    final_resolution_hours: int
    refined: bool
    evaluated_block_count: int
    payload_float_count: int
    always_hourly_payload_float_count: int
    steps: tuple[TemporalRefinementStep, ...]


def _envelope(
    hourly: Sequence[HourlyWeather], start_hour: int, end_hour: int
) -> TemporalBlockEnvelope:
    if start_hour < 0 or end_hour <= start_hour or end_hour > len(hourly):
        raise ValueError("invalid temporal block bounds")
    values = hourly[start_hour:end_hour]
    winds = [item.wind_kmh for item in values]
    precip = [item.precip_probability_percent for item in values]
    return TemporalBlockEnvelope(
        start_hour=start_hour,
        end_hour=end_hour,
        wind_min_kmh=min(winds),
        wind_max_kmh=max(winds),
        precip_min_percent=min(precip),
        precip_max_percent=max(precip),
    )


def classify_block(
    envelope: TemporalBlockEnvelope,
    *,
    wind_threshold_kmh: float,
    precip_threshold_percent: float,
) -> TemporalBlockAssessment:
    """Classify a block conservatively for one-hour-slot availability.

    AVAILABLE means every hour represented by this block satisfies both frozen
    criteria, so at least one usable hour is proven to exist.

    UNAVAILABLE means one criterion alone proves every represented hour unusable.

    Otherwise the block remains ambiguous because extrema do not preserve the
    hour-by-hour correlation between wind and precipitation; refinement is
    required before the task can use the block to prove availability/unavailability.
    """

    if wind_threshold_kmh < 0:
        raise ValueError("wind_threshold_kmh must be >= 0")
    if not 0 <= precip_threshold_percent <= 100:
        raise ValueError("precip_threshold_percent must be within [0, 100]")

    if (
        envelope.wind_max_kmh <= wind_threshold_kmh
        and envelope.precip_max_percent <= precip_threshold_percent
    ):
        status = BLOCK_AVAILABLE
    elif (
        envelope.wind_min_kmh > wind_threshold_kmh
        or envelope.precip_min_percent > precip_threshold_percent
    ):
        status = BLOCK_UNAVAILABLE
    else:
        status = BLOCK_AMBIGUOUS
    return TemporalBlockAssessment(envelope=envelope, status=status)


def _payload_floats(envelope: TemporalBlockEnvelope) -> int:
    # Fine one-hour context needs exact wind + precipitation (2 floats). Coarse
    # context carries min/max for both criteria (4 floats).
    return 2 if envelope.duration_hours == 1 else 4


def evaluate_temporal_refinement(
    hourly: Sequence[HourlyWeather],
    *,
    wind_threshold_kmh: float,
    precip_threshold_percent: float,
    ladder_hours: Sequence[int],
) -> TemporalRefinementTrace:
    """Refine only ambiguous time blocks until the window action is provable."""

    if not hourly:
        raise ValueError("hourly reference must not be empty")
    ladder = tuple(int(value) for value in ladder_hours)
    if not ladder or ladder[-1] != 1:
        raise ValueError("temporal ladder must end at one-hour fine reference")
    if ladder[0] != len(hourly):
        raise ValueError("temporal ladder must begin at the full task-window length")
    if any(value <= 0 for value in ladder):
        raise ValueError("temporal ladder values must be > 0")
    if any(ladder[index] <= ladder[index + 1] for index in range(len(ladder) - 1)):
        raise ValueError("temporal ladder must be strictly coarse-to-fine")
    if any(ladder[index] % ladder[index + 1] != 0 for index in range(len(ladder) - 1)):
        raise ValueError("each temporal level must divide its parent block exactly")

    # Leaves contain the current disjoint partition. Only ambiguous leaves are
    # split; proven-unavailable leaves remain summarized. The first available
    # leaf is enough to prove that the task window contains a usable one-hour slot.
    leaves: list[TemporalBlockAssessment] = []
    steps: list[TemporalRefinementStep] = []
    evaluated_blocks = 0
    payload_floats = 0

    for level_index, resolution in enumerate(ladder):
        if level_index == 0:
            blocks = [(0, len(hourly))]
            retained: list[TemporalBlockAssessment] = []
        else:
            parent_resolution = ladder[level_index - 1]
            retained = [item for item in leaves if item.status != BLOCK_AMBIGUOUS]
            blocks = []
            for item in leaves:
                if item.status != BLOCK_AMBIGUOUS:
                    continue
                start = item.envelope.start_hour
                end = item.envelope.end_hour
                if end - start != parent_resolution:
                    raise ValueError("ambiguous parent duration does not match ladder")
                blocks.extend(
                    (child_start, child_start + resolution)
                    for child_start in range(start, end, resolution)
                )

        new_assessments = [
            classify_block(
                _envelope(hourly, start, end),
                wind_threshold_kmh=wind_threshold_kmh,
                precip_threshold_percent=precip_threshold_percent,
            )
            for start, end in blocks
        ]
        evaluated_blocks += len(new_assessments)
        payload_floats += sum(_payload_floats(item.envelope) for item in new_assessments)
        leaves = retained + new_assessments

        available_count = sum(item.status == BLOCK_AVAILABLE for item in leaves)
        unavailable_count = sum(item.status == BLOCK_UNAVAILABLE for item in leaves)
        ambiguous_count = sum(item.status == BLOCK_AMBIGUOUS for item in leaves)

        if available_count:
            action = TASK_ACTION_AVAILABLE
        elif ambiguous_count == 0:
            action = TASK_ACTION_UNAVAILABLE
        else:
            action = TASK_ACTION_REFINE

        steps.append(
            TemporalRefinementStep(
                resolution_hours=resolution,
                newly_evaluated_block_count=len(new_assessments),
                ambiguous_block_count=ambiguous_count,
                unavailable_block_count=unavailable_count,
                available_block_count=available_count,
                cumulative_payload_float_count=payload_floats,
                action=action,
            )
        )
        if action != TASK_ACTION_REFINE:
            return TemporalRefinementTrace(
                wind_threshold_kmh=float(wind_threshold_kmh),
                precip_threshold_percent=float(precip_threshold_percent),
                final_action=action,
                final_resolution_hours=resolution,
                refined=len(steps) > 1,
                evaluated_block_count=evaluated_blocks,
                payload_float_count=payload_floats,
                always_hourly_payload_float_count=len(hourly) * 2,
                steps=tuple(steps),
            )

    raise ValueError("one-hour reference failed to resolve temporal task action")
