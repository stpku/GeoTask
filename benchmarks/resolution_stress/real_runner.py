"""Offline real-fixture runner for the Resolution Stress Test.

The runner uses only the pinned normalized 1 m grid committed by the one-shot
USGS acquisition. All coarse contexts are derived locally and deterministically.
It evaluates every frozen corridor/threshold pair; no case is selected after
observing the fine reference.
"""

from __future__ import annotations

from array import array
from collections import Counter
from dataclasses import asdict, dataclass
import gzip
import hashlib
import json
from pathlib import Path
import sys
from typing import Mapping

from benchmarks.resolution_stress.envelope_policy import (
    REFINE,
    ResolutionAssessment,
    assess_envelopes,
    aggregate_minmax,
)
from benchmarks.resolution_stress.experiment_spec import (
    CORRIDORS,
    ELEVATION_THRESHOLDS_METERS,
    FINE_GRID_HEIGHT,
    FINE_GRID_WIDTH,
    FINE_PIXEL_SIZE_METERS,
    RESOLUTION_LADDER_METERS,
)


@dataclass(frozen=True)
class RealResolutionCaseResult:
    corridor_id: str
    threshold_meters: float
    fine_reference_action: str
    first_action: str
    final_action: str
    final_resolution_meters: int
    refined: bool
    unsafe_stop: bool
    cells_evaluated: int
    always_finest_cells: int
    steps: tuple[ResolutionAssessment, ...]


@dataclass(frozen=True)
class RealResolutionSummary:
    total_cases: int
    coarse_stop_case_count: int
    refinement_case_count: int
    unsafe_stop_count: int
    unnecessary_refinement_count: int
    final_resolution_counts: Mapping[str, int]
    adaptive_cells_evaluated: int
    always_finest_cells_evaluated: int
    cell_evaluation_reduction_ratio: float
    mandatory_stop_control_present: bool
    mandatory_refine_control_present: bool
    promotion_stress_gate_pass: bool
    cases: tuple[RealResolutionCaseResult, ...]


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def load_pinned_fine_grid(
    fixture_root: Path,
) -> tuple[tuple[float, ...], ...]:
    record_path = fixture_root / "record.json"
    grid_path = fixture_root / "fine-grid.f32.gz"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise ValueError("fine fixture record must be a mapping")
    if record.get("stage") != "FINE_REFERENCE_ACQUIRED":
        raise ValueError("fine fixture is not in acquired state")
    if record.get("width") != FINE_GRID_WIDTH or record.get("height") != FINE_GRID_HEIGHT:
        raise ValueError("fine fixture dimensions differ from frozen experiment")
    if record.get("masked_cell_count") != 0:
        raise ValueError("fine fixture contains masked/NoData cells")

    with gzip.open(grid_path, "rb") as handle:
        payload = handle.read()
    expected_bytes = FINE_GRID_WIDTH * FINE_GRID_HEIGHT * 4
    if len(payload) != expected_bytes:
        raise ValueError("fine grid byte length differs from frozen float32 shape")
    if _sha256(payload) != record.get("grid_sha256"):
        raise ValueError("fine grid hash differs from acquisition record")

    values = array("f")
    values.frombytes(payload)
    if sys.byteorder != "little":
        values.byteswap()
    if len(values) != FINE_GRID_WIDTH * FINE_GRID_HEIGHT:
        raise ValueError("fine grid float count differs from frozen shape")

    rows = tuple(
        tuple(float(value) for value in values[offset : offset + FINE_GRID_WIDTH])
        for offset in range(0, len(values), FINE_GRID_WIDTH)
    )
    return rows


def _evaluate_case(
    envelopes_by_resolution: Mapping[int, tuple[tuple[object, ...], ...]],
    *,
    corridor,
    threshold_meters: float,
) -> RealResolutionCaseResult:
    steps: list[ResolutionAssessment] = []
    for resolution in RESOLUTION_LADDER_METERS:
        envelopes = envelopes_by_resolution[resolution]
        assessment = assess_envelopes(
            envelopes,  # type: ignore[arg-type]
            resolution_meters=resolution,
            corridor=corridor,
            threshold_meters=threshold_meters,
        )
        steps.append(assessment)
        if assessment.action != REFINE:
            break

    if steps[-1].action == REFINE:
        raise ValueError("1 m fine reference failed to resolve a frozen real case")

    fine_assessment = assess_envelopes(
        envelopes_by_resolution[FINE_PIXEL_SIZE_METERS],  # type: ignore[arg-type]
        resolution_meters=FINE_PIXEL_SIZE_METERS,
        corridor=corridor,
        threshold_meters=threshold_meters,
    )
    if fine_assessment.action == REFINE:
        raise ValueError("fine reference action is unexpectedly ambiguous")

    final = steps[-1]
    unsafe_stop = final.action != fine_assessment.action
    return RealResolutionCaseResult(
        corridor_id=corridor.corridor_id,
        threshold_meters=float(threshold_meters),
        fine_reference_action=fine_assessment.action,
        first_action=steps[0].action,
        final_action=final.action,
        final_resolution_meters=final.resolution_meters,
        refined=len(steps) > 1,
        unsafe_stop=unsafe_stop,
        cells_evaluated=sum(step.intersecting_cell_count for step in steps),
        always_finest_cells=fine_assessment.intersecting_cell_count,
        steps=tuple(steps),
    )


def run_real_resolution_stress(fixture_root: Path) -> RealResolutionSummary:
    fine_grid = load_pinned_fine_grid(fixture_root)
    envelopes_by_resolution = {
        resolution: aggregate_minmax(
            fine_grid,
            resolution_meters=resolution,
            fine_pixel_size_meters=FINE_PIXEL_SIZE_METERS,
        )
        for resolution in RESOLUTION_LADDER_METERS
    }

    cases = tuple(
        _evaluate_case(
            envelopes_by_resolution,
            corridor=corridor,
            threshold_meters=threshold,
        )
        for corridor in CORRIDORS
        for threshold in ELEVATION_THRESHOLDS_METERS
    )

    coarse_stop = sum(case.first_action != REFINE for case in cases)
    refined = sum(case.refined for case in cases)
    unsafe = sum(case.unsafe_stop for case in cases)
    # Under the frozen proof rule, refinement is unnecessary only if the policy
    # refines despite having a provable non-REFINE first action. This should be
    # structurally impossible; retain it as a countermetric rather than assuming.
    unnecessary = sum(case.refined and case.first_action != REFINE for case in cases)
    final_counts = Counter(str(case.final_resolution_meters) for case in cases)
    adaptive_cells = sum(case.cells_evaluated for case in cases)
    finest_cells = sum(case.always_finest_cells for case in cases)
    reduction = 0.0 if finest_cells == 0 else 1.0 - adaptive_cells / finest_cells

    stop_present = coarse_stop > 0
    refine_present = refined > 0
    return RealResolutionSummary(
        total_cases=len(cases),
        coarse_stop_case_count=coarse_stop,
        refinement_case_count=refined,
        unsafe_stop_count=unsafe,
        unnecessary_refinement_count=unnecessary,
        final_resolution_counts=dict(sorted(final_counts.items(), key=lambda item: int(item[0]), reverse=True)),
        adaptive_cells_evaluated=adaptive_cells,
        always_finest_cells_evaluated=finest_cells,
        cell_evaluation_reduction_ratio=reduction,
        mandatory_stop_control_present=stop_present,
        mandatory_refine_control_present=refine_present,
        promotion_stress_gate_pass=(stop_present and refine_present and unsafe == 0 and unnecessary == 0),
        cases=cases,
    )


def summary_to_jsonable(summary: RealResolutionSummary) -> dict[str, object]:
    return asdict(summary)
