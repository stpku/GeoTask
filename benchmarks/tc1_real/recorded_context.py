"""Normalize recorded TC1-Real evidence into GeoTask ContextCandidates.

This adapter intentionally lives outside ``geotask_core``.  It proves whether
existing task-context contracts can consume real provider evidence before new
Core abstractions are proposed.

The same evidence can be projected onto different *single* cost dimensions for
Core assessment.  The full real measurement vector stays in candidate metadata;
no projection is claimed to be a universal utility function.
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


NETWORK_BYTES = "network_byte"
CARRIED_BYTES = "carried_byte"
SUPPORTED_COST_PROJECTIONS = {NETWORK_BYTES, CARRIED_BYTES}
RECORDED_WINDOW = "recorded-experiment-window"
RECORDED_HRRR_VALID_TIME = "2026-08-18T10:00:00Z"


@dataclass(frozen=True)
class RecordedContextAssessment:
    policy: str
    cost_projection: str
    context: TaskContext
    candidate_ids: tuple[str, ...]


@dataclass(frozen=True)
class RecordedContextComparison:
    cost_projection: str
    rg: RecordedContextAssessment
    r0: RecordedContextAssessment
    reduction_ratio: float


def _load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"recorded fixture must be a JSON object: {path}")
    return value


def _require_projection(cost_projection: str) -> None:
    if cost_projection not in SUPPORTED_COST_PROJECTIONS:
        raise ValueError(
            "cost_projection must be network_byte or carried_byte"
        )


def _measurement_metadata(**values: object) -> Mapping[str, object]:
    return {key: value for key, value in values.items()}


def _accepted_requirements() -> tuple[ContextRequirement, ...]:
    case = get_tc1_real_case("M1-controlled-airspace-context")
    return tuple(
        item.requirement
        for item in case.reference_requirements
        if item.grading_state == "accepted"
    )


def _task_for_projection(cost_projection: str) -> TaskFrame:
    _require_projection(cost_projection)
    case = get_tc1_real_case("M1-controlled-airspace-context")
    # No budget is introduced here. The projection is used only to measure and
    # compare burden; it must not change information sufficiency.
    return TaskFrame(
        task_id=f"{case.task.task_id}:{cost_projection}",
        goal=case.task.goal,
        subject_refs=case.task.subject_refs,
        spatial_scope=case.task.spatial_scope,
        temporal_scope=case.task.temporal_scope,
        outputs=case.task.outputs,
    )


def _cost(network_bytes: int, carried_bytes: int, projection: str) -> float:
    _require_projection(projection)
    return float(network_bytes if projection == NETWORK_BYTES else carried_bytes)


def _normalize_rg_candidates(
    fixture_root: Path,
    cost_projection: str,
) -> tuple[ContextCandidate, ...]:
    _require_projection(cost_projection)

    uasfm_dir = fixture_root / "uasfm_phx_20260818"
    ddof_dir = fixture_root / "ddof_phx_20260818"
    hrrr_dir = fixture_root / "hrrr_phx_20260818"

    uasfm_summary = _load(uasfm_dir / "summary.json")
    uasfm_record = _load(uasfm_dir / "uasfm-phx.record.json")
    ddof_acquisition = _load(ddof_dir / "acquisition.record.json")
    ddof_selection = _load(ddof_dir / "selection-summary.json")
    hrrr_record = _load(hrrr_dir / "hrrr-task.record.json")

    uasfm_network = int(uasfm_summary["payload_bytes"])
    ddof_network = int(
        (ddof_acquisition["measurement"])["bytes_transferred"]  # type: ignore[index]
    )
    ddof_carried = int(ddof_selection["selected_serialized_bytes"])
    hrrr_network = int(
        (hrrr_record["measurement"])["bytes_transferred"]  # type: ignore[index]
    )

    hrrr_provenance = hrrr_record["provenance"]
    if not isinstance(hrrr_provenance, Mapping):
        raise ValueError("recorded HRRR provenance must be a mapping")
    if hrrr_provenance.get("valid_from") != RECORDED_HRRR_VALID_TIME:
        raise ValueError("recorded HRRR valid time does not match experiment window")

    uasfm_provenance = uasfm_record["provenance"]
    ddof_provenance = ddof_acquisition["provenance"]
    if not isinstance(uasfm_provenance, Mapping) or not isinstance(ddof_provenance, Mapping):
        raise ValueError("recorded UASFM/DDOF provenance must be mappings")

    cost_unit = cost_projection
    return (
        ContextCandidate(
            candidate_id="rg-uasfm-airspace",
            source="faa-uasfm",
            requirement_ids=("airspace_guidance",),
            spatial_scope=EXPERIMENT_SPATIAL_SCOPE,
            acquisition_cost=_cost(uasfm_network, uasfm_network, cost_projection),
            cost_unit=cost_unit,
            metadata=_measurement_metadata(
                source_hash=uasfm_provenance.get("content_sha256"),
                feature_count=uasfm_summary.get("feature_count"),
                network_bytes=uasfm_network,
                carried_bytes=uasfm_network,
                authorization=False,
            ),
        ),
        ContextCandidate(
            candidate_id="rg-ddof-obstacles",
            source="faa-ddof",
            requirement_ids=("obstacle_context",),
            spatial_scope=EXPERIMENT_SPATIAL_SCOPE,
            acquisition_cost=_cost(ddof_network, ddof_carried, cost_projection),
            cost_unit=cost_unit,
            metadata=_measurement_metadata(
                source_hash=ddof_selection.get("source_csv_sha256"),
                network_bytes=ddof_network,
                carried_bytes=ddof_carried,
                selected_rows=ddof_selection.get("selected_row_count"),
                verification_status_counts=ddof_selection.get(
                    "verification_status_counts"
                ),
                source_not_exhaustive=True,
            ),
        ),
        ContextCandidate(
            candidate_id="rg-hrrr-weather",
            source="noaa-hrrr",
            requirement_ids=("weather_wind", "weather_visibility"),
            spatial_scope=EXPERIMENT_SPATIAL_SCOPE,
            temporal_scope=RECORDED_WINDOW,
            spatial_resolution=3000.0,
            spatial_resolution_unit="meter",
            temporal_resolution_seconds=3600.0,
            acquisition_cost=_cost(hrrr_network, hrrr_network, cost_projection),
            cost_unit=cost_unit,
            metadata=_measurement_metadata(
                source_hash=hrrr_provenance.get("content_sha256"),
                run_time=hrrr_provenance.get("source_effective_at"),
                valid_time=hrrr_provenance.get("valid_from"),
                network_bytes=hrrr_network,
                carried_bytes=hrrr_network,
            ),
        ),
    )


def _normalize_r0_candidates(
    fixture_root: Path,
    cost_projection: str,
) -> tuple[ContextCandidate, ...]:
    """Normalize broad-source R0 evidence after explicit coverage checks.

    The current Core only compares opaque exact scope ids.  This benchmark
    adapter therefore performs/records provider-specific containment before
    normalizing a broader source response to the task scope.  That is evidence
    that richer geometry applicability remains outside Core v0.1.
    """

    _require_projection(cost_projection)

    uasfm_task = _load(fixture_root / "uasfm_phx_20260818" / "summary.json")
    uasfm_r0 = _load(
        fixture_root / "uasfm_phx_r0_regional_20260818" / "summary.json"
    )
    ddof_acquisition = _load(
        fixture_root / "ddof_phx_20260818" / "acquisition.record.json"
    )
    ddof_summary = _load(fixture_root / "ddof_phx_20260818" / "summary.json")
    hrrr_r0_record = _load(
        fixture_root / "hrrr_phx_20260818" / "hrrr-r0-regional.record.json"
    )

    def bbox(value: object) -> tuple[float, float, float, float]:
        if not isinstance(value, list) or len(value) != 4:
            raise ValueError("recorded bbox must contain four values")
        return tuple(float(item) for item in value)  # type: ignore[return-value]

    task_bbox = bbox(uasfm_task["bbox"])
    r0_bbox = bbox(uasfm_r0["bbox"])
    if not (
        r0_bbox[0] <= task_bbox[0]
        and r0_bbox[1] <= task_bbox[1]
        and r0_bbox[2] >= task_bbox[2]
        and r0_bbox[3] >= task_bbox[3]
    ):
        raise ValueError("recorded UASFM R0 bbox does not contain task bbox")

    hrrr_provenance = hrrr_r0_record["provenance"]
    if not isinstance(hrrr_provenance, Mapping):
        raise ValueError("recorded HRRR R0 provenance must be a mapping")
    if hrrr_provenance.get("valid_from") != RECORDED_HRRR_VALID_TIME:
        raise ValueError("recorded HRRR R0 valid time does not match experiment window")

    uasfm_network = int(uasfm_r0["payload_bytes"])
    ddof_network = int(
        (ddof_acquisition["measurement"])["bytes_transferred"]  # type: ignore[index]
    )
    ddof_carried = int(ddof_summary["csv_bytes"])
    hrrr_network = int(
        (hrrr_r0_record["measurement"])["bytes_transferred"]  # type: ignore[index]
    )
    cost_unit = cost_projection

    return (
        ContextCandidate(
            candidate_id="r0-uasfm-airspace",
            source="faa-uasfm",
            requirement_ids=("airspace_guidance",),
            spatial_scope=EXPERIMENT_SPATIAL_SCOPE,
            acquisition_cost=_cost(uasfm_network, uasfm_network, cost_projection),
            cost_unit=cost_unit,
            metadata=_measurement_metadata(
                normalized_from_broader_scope=True,
                network_bytes=uasfm_network,
                carried_bytes=uasfm_network,
            ),
        ),
        ContextCandidate(
            candidate_id="r0-ddof-obstacles",
            source="faa-ddof",
            requirement_ids=("obstacle_context",),
            spatial_scope=EXPERIMENT_SPATIAL_SCOPE,
            acquisition_cost=_cost(ddof_network, ddof_carried, cost_projection),
            cost_unit=cost_unit,
            metadata=_measurement_metadata(
                normalized_from_broad_provider=True,
                network_bytes=ddof_network,
                carried_bytes=ddof_carried,
                source_not_exhaustive=True,
            ),
        ),
        ContextCandidate(
            candidate_id="r0-hrrr-weather",
            source="noaa-hrrr",
            requirement_ids=("weather_wind", "weather_visibility"),
            spatial_scope=EXPERIMENT_SPATIAL_SCOPE,
            temporal_scope=RECORDED_WINDOW,
            spatial_resolution=3000.0,
            spatial_resolution_unit="meter",
            temporal_resolution_seconds=3600.0,
            acquisition_cost=_cost(hrrr_network, hrrr_network, cost_projection),
            cost_unit=cost_unit,
            metadata=_measurement_metadata(
                normalized_from_broader_scope=True,
                run_time=hrrr_provenance.get("source_effective_at"),
                valid_time=hrrr_provenance.get("valid_from"),
                network_bytes=hrrr_network,
                carried_bytes=hrrr_network,
            ),
        ),
    )


def assess_recorded_m1(
    fixture_root: Path,
    *,
    cost_projection: str,
) -> RecordedContextComparison:
    """Assess the same M1 evidence under one explicit burden projection."""

    task = _task_for_projection(cost_projection)
    requirements = _accepted_requirements()
    rg_candidates = _normalize_rg_candidates(fixture_root, cost_projection)
    r0_candidates = _normalize_r0_candidates(fixture_root, cost_projection)

    rg_context = assess_task_context(task, requirements, rg_candidates)
    r0_context = assess_task_context(task, requirements, r0_candidates)
    rg = RecordedContextAssessment(
        policy="RG/task-bounded",
        cost_projection=cost_projection,
        context=rg_context,
        candidate_ids=tuple(candidate.candidate_id for candidate in rg_candidates),
    )
    r0 = RecordedContextAssessment(
        policy="R0/broad-data-upper-bound",
        cost_projection=cost_projection,
        context=r0_context,
        candidate_ids=tuple(candidate.candidate_id for candidate in r0_candidates),
    )

    if not rg_context.sufficient or not r0_context.sufficient:
        raise ValueError("recorded M1 RG/R0 must cover the frozen critical requirements")
    if r0_context.total_acquisition_cost <= 0:
        raise ValueError("recorded M1 R0 burden must be > 0")

    return RecordedContextComparison(
        cost_projection=cost_projection,
        rg=rg,
        r0=r0,
        reduction_ratio=(
            1.0
            - (rg_context.total_acquisition_cost / r0_context.total_acquisition_cost)
        ),
    )
