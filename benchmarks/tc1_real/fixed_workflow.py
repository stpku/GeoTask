"""Recorded TC1-Real R1 fixed-regional preprocessing baseline.

R1 is intentionally stronger than the synthetic fixed-template baseline.  It
covers every frozen critical requirement and does not rely on a missing item to
look worse than GeoTask.

Policy:
- UASFM: always use the recorded 0.3 x 0.3 degree regional response;
- DDOF: broad provider download remains unavoidable, then use the same local
  task-bbox selection as RG;
- HRRR: always use the recorded 0.3 x 0.3 degree regional subset with the same
  run/forecast/variables/levels as RG.

R1 is a reproducible engineering baseline, not a claim about expert practice.
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
    RECORDED_HRRR_VALID_TIME,
    RECORDED_WINDOW,
    SUPPORTED_COST_PROJECTIONS,
    assess_recorded_m1,
)


@dataclass(frozen=True)
class FixedR1Comparison:
    cost_projection: str
    rg_context: TaskContext
    r1_context: TaskContext
    reduction_ratio: float


def _load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"recorded fixture must be a JSON object: {path}")
    return value


def _task(cost_projection: str) -> TaskFrame:
    if cost_projection not in SUPPORTED_COST_PROJECTIONS:
        raise ValueError("unsupported R1 cost projection")
    case = get_tc1_real_case("M1-controlled-airspace-context")
    return TaskFrame(
        task_id=f"{case.task.task_id}:R1:{cost_projection}",
        goal=case.task.goal,
        subject_refs=case.task.subject_refs,
        spatial_scope=case.task.spatial_scope,
        temporal_scope=case.task.temporal_scope,
        outputs=case.task.outputs,
    )


def _requirements() -> tuple[ContextRequirement, ...]:
    case = get_tc1_real_case("M1-controlled-airspace-context")
    return tuple(
        item.requirement
        for item in case.reference_requirements
        if item.grading_state == "accepted"
    )


def _cost(network_bytes: int, carried_bytes: int, projection: str) -> float:
    return float(network_bytes if projection == NETWORK_BYTES else carried_bytes)


def _bbox_contains(outer: object, inner: object) -> bool:
    if not isinstance(outer, list) or not isinstance(inner, list):
        raise ValueError("recorded bbox must be a list")
    if len(outer) != 4 or len(inner) != 4:
        raise ValueError("recorded bbox must contain four values")
    o = tuple(float(item) for item in outer)
    i = tuple(float(item) for item in inner)
    return o[0] <= i[0] and o[1] <= i[1] and o[2] >= i[2] and o[3] >= i[3]


def build_r1_candidates(
    fixture_root: Path,
    *,
    cost_projection: str,
) -> tuple[ContextCandidate, ...]:
    if cost_projection not in SUPPORTED_COST_PROJECTIONS:
        raise ValueError("unsupported R1 cost projection")

    uasfm_task = _load(fixture_root / "uasfm_phx_20260818" / "summary.json")
    uasfm_r0 = _load(
        fixture_root / "uasfm_phx_r0_regional_20260818" / "summary.json"
    )
    ddof_acquisition = _load(
        fixture_root / "ddof_phx_20260818" / "acquisition.record.json"
    )
    ddof_selection = _load(
        fixture_root / "ddof_phx_20260818" / "selection-summary.json"
    )
    hrrr_task = _load(
        fixture_root / "hrrr_phx_20260818" / "hrrr-task.record.json"
    )
    hrrr_r0 = _load(
        fixture_root / "hrrr_phx_20260818" / "hrrr-r0-regional.record.json"
    )

    if not _bbox_contains(uasfm_r0["bbox"], uasfm_task["bbox"]):
        raise ValueError("recorded R1 UASFM region does not contain task bbox")

    hrrr_task_provenance = hrrr_task["provenance"]
    hrrr_r0_provenance = hrrr_r0["provenance"]
    if not isinstance(hrrr_task_provenance, Mapping) or not isinstance(
        hrrr_r0_provenance, Mapping
    ):
        raise ValueError("recorded HRRR provenance must be mappings")
    for field in ("source_effective_at", "valid_from", "valid_until"):
        if hrrr_task_provenance.get(field) != hrrr_r0_provenance.get(field):
            raise ValueError(f"recorded R1 HRRR differs from task in {field}")
    if hrrr_r0_provenance.get("valid_from") != RECORDED_HRRR_VALID_TIME:
        raise ValueError("recorded R1 HRRR valid time does not match experiment")

    task_params = hrrr_task_provenance.get("request_parameters")
    r0_params = hrrr_r0_provenance.get("request_parameters")
    if not isinstance(task_params, Mapping) or not isinstance(r0_params, Mapping):
        raise ValueError("recorded HRRR request parameters must be mappings")
    for field in ("date", "cycle_utc", "forecast_hour", "variables", "levels"):
        if task_params.get(field) != r0_params.get(field):
            raise ValueError(f"recorded R1 HRRR differs from task in {field}")
    if not _bbox_contains(r0_params["bbox"], task_params["bbox"]):
        raise ValueError("recorded R1 HRRR region does not contain task bbox")

    ddof_measurement = ddof_acquisition["measurement"]
    hrrr_measurement = hrrr_r0["measurement"]
    if not isinstance(ddof_measurement, Mapping) or not isinstance(
        hrrr_measurement, Mapping
    ):
        raise ValueError("recorded measurement fields must be mappings")

    uasfm_bytes = int(uasfm_r0["payload_bytes"])
    ddof_network = int(ddof_measurement["bytes_transferred"])
    ddof_carried = int(ddof_selection["selected_serialized_bytes"])
    hrrr_bytes = int(hrrr_measurement["bytes_transferred"])

    return (
        ContextCandidate(
            candidate_id="r1-uasfm-regional",
            source="faa-uasfm",
            requirement_ids=("airspace_guidance",),
            spatial_scope=EXPERIMENT_SPATIAL_SCOPE,
            acquisition_cost=_cost(uasfm_bytes, uasfm_bytes, cost_projection),
            cost_unit=cost_projection,
            metadata={
                "fixed_regional_preprocessing": True,
                "network_bytes": uasfm_bytes,
                "carried_bytes": uasfm_bytes,
            },
        ),
        ContextCandidate(
            candidate_id="r1-ddof-local",
            source="faa-ddof",
            requirement_ids=("obstacle_context",),
            spatial_scope=EXPERIMENT_SPATIAL_SCOPE,
            acquisition_cost=_cost(ddof_network, ddof_carried, cost_projection),
            cost_unit=cost_projection,
            metadata={
                "broad_acquisition": True,
                "local_task_filter": True,
                "network_bytes": ddof_network,
                "carried_bytes": ddof_carried,
                "source_not_exhaustive": True,
            },
        ),
        ContextCandidate(
            candidate_id="r1-hrrr-regional",
            source="noaa-hrrr",
            requirement_ids=("weather_wind", "weather_visibility"),
            spatial_scope=EXPERIMENT_SPATIAL_SCOPE,
            temporal_scope=RECORDED_WINDOW,
            spatial_resolution=3000.0,
            spatial_resolution_unit="meter",
            temporal_resolution_seconds=3600.0,
            acquisition_cost=_cost(hrrr_bytes, hrrr_bytes, cost_projection),
            cost_unit=cost_projection,
            metadata={
                "fixed_regional_preprocessing": True,
                "run_time": hrrr_r0_provenance.get("source_effective_at"),
                "valid_time": hrrr_r0_provenance.get("valid_from"),
                "network_bytes": hrrr_bytes,
                "carried_bytes": hrrr_bytes,
            },
        ),
    )


def compare_rg_to_r1(
    fixture_root: Path,
    *,
    cost_projection: str,
) -> FixedR1Comparison:
    task = _task(cost_projection)
    requirements = _requirements()
    r1_candidates = build_r1_candidates(
        fixture_root,
        cost_projection=cost_projection,
    )
    r1_context = assess_task_context(task, requirements, r1_candidates)
    rg_context = assess_recorded_m1(
        fixture_root,
        cost_projection=cost_projection,
    ).rg.context

    if not r1_context.sufficient or not rg_context.sufficient:
        raise ValueError("RG and R1 must both cover frozen critical requirements")
    if r1_context.total_acquisition_cost <= 0:
        raise ValueError("R1 burden must be > 0")

    return FixedR1Comparison(
        cost_projection=cost_projection,
        rg_context=rg_context,
        r1_context=r1_context,
        reduction_ratio=(
            1.0
            - (rg_context.total_acquisition_cost / r1_context.total_acquisition_cost)
        ),
    )
