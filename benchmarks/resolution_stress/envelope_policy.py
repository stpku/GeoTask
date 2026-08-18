"""Conservative benchmark policy for Task Context resolution stress.

This is experiment code, not a promoted GeoTask Core algorithm.  It evaluates a
fixed corridor against min/max envelopes derived from one fine reference grid.
The policy may stop at a coarse scale only when every fine value compatible with
the coarse envelope implies the same threshold-side task action.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

from benchmarks.resolution_stress.experiment_spec import CorridorRect


STOP_CLEAR = "STOP_CLEAR"
STOP_BLOCKED = "STOP_BLOCKED"
REFINE = "REFINE"


@dataclass(frozen=True)
class CellEnvelope:
    minimum: float
    maximum: float

    def __post_init__(self) -> None:
        if not isfinite(self.minimum) or not isfinite(self.maximum):
            raise ValueError("cell envelope values must be finite")
        if self.minimum > self.maximum:
            raise ValueError("cell envelope minimum cannot exceed maximum")


@dataclass(frozen=True)
class ResolutionAssessment:
    resolution_meters: int
    action: str
    intersecting_cell_count: int
    ambiguous_cell_count: int
    definitely_blocked_cell_count: int
    minimum_margin_to_threshold: float


@dataclass(frozen=True)
class ResolutionTrace:
    threshold_meters: float
    corridor_id: str
    steps: tuple[ResolutionAssessment, ...]

    @property
    def final_action(self) -> str:
        if not self.steps:
            raise ValueError("resolution trace must contain at least one step")
        return self.steps[-1].action

    @property
    def final_resolution_meters(self) -> int:
        if not self.steps:
            raise ValueError("resolution trace must contain at least one step")
        return self.steps[-1].resolution_meters

    @property
    def refined(self) -> bool:
        return len(self.steps) > 1


def _validate_fine_grid(fine_grid: Sequence[Sequence[float]]) -> tuple[int, int]:
    if not fine_grid:
        raise ValueError("fine_grid must contain at least one row")
    width = len(fine_grid[0])
    if width == 0:
        raise ValueError("fine_grid rows must not be empty")
    for row in fine_grid:
        if len(row) != width:
            raise ValueError("fine_grid must be rectangular")
        for value in row:
            if not isfinite(float(value)):
                raise ValueError("fine_grid values must be finite")
    return width, len(fine_grid)


def aggregate_minmax(
    fine_grid: Sequence[Sequence[float]],
    *,
    resolution_meters: int,
    fine_pixel_size_meters: int = 1,
) -> tuple[tuple[CellEnvelope, ...], ...]:
    """Aggregate a fine grid into exact block min/max envelopes.

    The benchmark currently requires integer block factors and full blocks at the
    ROI boundary.  This keeps aggregation deterministic and prevents partial-cell
    policy choices from entering the first Resolution experiment.
    """

    width, height = _validate_fine_grid(fine_grid)
    if resolution_meters <= 0 or fine_pixel_size_meters <= 0:
        raise ValueError("resolution values must be > 0")
    if resolution_meters % fine_pixel_size_meters != 0:
        raise ValueError("resolution_meters must be an integer multiple of fine pixel size")
    factor = resolution_meters // fine_pixel_size_meters
    if factor <= 0 or width % factor != 0 or height % factor != 0:
        raise ValueError("fine grid dimensions must be divisible by the aggregation factor")

    rows: list[tuple[CellEnvelope, ...]] = []
    for y0 in range(0, height, factor):
        coarse_row: list[CellEnvelope] = []
        for x0 in range(0, width, factor):
            values = [
                float(fine_grid[y][x])
                for y in range(y0, y0 + factor)
                for x in range(x0, x0 + factor)
            ]
            coarse_row.append(CellEnvelope(minimum=min(values), maximum=max(values)))
        rows.append(tuple(coarse_row))
    return tuple(rows)


def _intersects_half_open(
    *,
    cell_min_x: int,
    cell_min_y: int,
    cell_max_x: int,
    cell_max_y: int,
    corridor: CorridorRect,
) -> bool:
    return (
        cell_min_x < corridor.max_x
        and cell_max_x > corridor.min_x
        and cell_min_y < corridor.max_y
        and cell_max_y > corridor.min_y
    )


def assess_envelopes(
    envelopes: Sequence[Sequence[CellEnvelope]],
    *,
    resolution_meters: int,
    corridor: CorridorRect,
    threshold_meters: float,
) -> ResolutionAssessment:
    """Assess one resolution using conservative threshold-side envelopes.

    Frozen task semantics:

    - terrain ``>= threshold`` anywhere on the represented corridor is BLOCKED;
    - if every value in one intersecting coarse cell is >= threshold, blockage is
      already proven;
    - if every intersecting coarse cell is entirely below threshold, clearance is
      proven for the discrete reference grid;
    - otherwise the coarse context is ambiguous and must refine.
    """

    if resolution_meters <= 0:
        raise ValueError("resolution_meters must be > 0")
    if not isfinite(float(threshold_meters)):
        raise ValueError("threshold_meters must be finite")
    if not envelopes or not envelopes[0]:
        raise ValueError("envelopes must not be empty")

    height = len(envelopes)
    width = len(envelopes[0])
    if any(len(row) != width for row in envelopes):
        raise ValueError("envelopes must be rectangular")

    intersecting = 0
    ambiguous = 0
    definitely_blocked = 0
    margins: list[float] = []

    for row_index, row in enumerate(envelopes):
        for column_index, cell in enumerate(row):
            if not _intersects_half_open(
                cell_min_x=column_index * resolution_meters,
                cell_min_y=row_index * resolution_meters,
                cell_max_x=(column_index + 1) * resolution_meters,
                cell_max_y=(row_index + 1) * resolution_meters,
                corridor=corridor,
            ):
                continue
            intersecting += 1
            if cell.minimum >= threshold_meters:
                definitely_blocked += 1
                margins.append(cell.minimum - threshold_meters)
            elif cell.maximum < threshold_meters:
                margins.append(threshold_meters - cell.maximum)
            else:
                ambiguous += 1
                margins.append(0.0)

    if intersecting == 0:
        raise ValueError("corridor does not intersect the envelope grid")

    if definitely_blocked:
        action = STOP_BLOCKED
    elif ambiguous:
        action = REFINE
    else:
        action = STOP_CLEAR

    return ResolutionAssessment(
        resolution_meters=resolution_meters,
        action=action,
        intersecting_cell_count=intersecting,
        ambiguous_cell_count=ambiguous,
        definitely_blocked_cell_count=definitely_blocked,
        minimum_margin_to_threshold=min(margins),
    )


def evaluate_resolution_ladder(
    fine_grid: Sequence[Sequence[float]],
    *,
    corridor: CorridorRect,
    threshold_meters: float,
    resolution_ladder_meters: Sequence[int],
    fine_pixel_size_meters: int = 1,
) -> ResolutionTrace:
    """Evaluate coarse-to-fine until the frozen action becomes provable."""

    if not resolution_ladder_meters:
        raise ValueError("resolution_ladder_meters must not be empty")
    ladder = tuple(int(value) for value in resolution_ladder_meters)
    if any(value <= 0 for value in ladder):
        raise ValueError("resolution ladder values must be > 0")
    if any(ladder[index] <= ladder[index + 1] for index in range(len(ladder) - 1)):
        raise ValueError("resolution ladder must be strictly coarse-to-fine")
    if ladder[-1] != fine_pixel_size_meters:
        raise ValueError("resolution ladder must end at the fine reference pixel size")

    steps: list[ResolutionAssessment] = []
    for resolution in ladder:
        envelopes = aggregate_minmax(
            fine_grid,
            resolution_meters=resolution,
            fine_pixel_size_meters=fine_pixel_size_meters,
        )
        assessment = assess_envelopes(
            envelopes,
            resolution_meters=resolution,
            corridor=corridor,
            threshold_meters=threshold_meters,
        )
        steps.append(assessment)
        if assessment.action != REFINE:
            break

    if steps[-1].action == REFINE:
        raise ValueError("fine reference failed to resolve the frozen threshold action")

    return ResolutionTrace(
        threshold_meters=float(threshold_meters),
        corridor_id=corridor.corridor_id,
        steps=tuple(steps),
    )
