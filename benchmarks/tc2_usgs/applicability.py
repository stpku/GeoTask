"""TC2 cross-domain applicability proof using recorded USGS events.

The module intentionally lives under ``benchmarks/``.  It tests whether a
small, domain-neutral *decision shape* can mediate richer physical relations
before GeoTask Core consumes opaque task-scope references.

It does not infer earthquake damage, inspection priority, safety, or action
authorization.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Mapping

from geotask_core.task_context import (
    ContextCandidate,
    ContextRequirement,
    TaskContext,
    TaskFrame,
    assess_task_context,
)


TC2_METHOD_ID = "point-event-task-applicability"
TC2_METHOD_VERSION = "0.1"
TC2_SPATIAL_SCOPE = "tc2-usgs-inspection-region"
TC2_TEMPORAL_SCOPE = "tc2-usgs-event-window"
TC2_REQUIREMENT_ID = "seismic_event_context"
TC2_TASK_BBOX = (-117.65, 35.68, -117.49, 35.82)
TC2_WINDOW_START = "2019-07-06T03:00:00Z"
TC2_WINDOW_END = "2019-07-06T04:00:00Z"

TC2_CONTROL_EVENT_ID = "ci38457511"
TC2_TEMPORAL_MISMATCH_EVENT_ID = "ci38443183"
TC2_SPATIAL_MISMATCH_EVENT_ID = "ci38457687"


@dataclass(frozen=True)
class SpatialBBox:
    min_longitude: float
    min_latitude: float
    max_longitude: float
    max_latitude: float

    def __post_init__(self) -> None:
        values = (
            self.min_longitude,
            self.min_latitude,
            self.max_longitude,
            self.max_latitude,
        )
        if any(not math.isfinite(value) for value in values):
            raise ValueError("bbox coordinates must be finite")
        if self.min_longitude >= self.max_longitude:
            raise ValueError("bbox min_longitude must be less than max_longitude")
        if self.min_latitude >= self.max_latitude:
            raise ValueError("bbox min_latitude must be less than max_latitude")

    def contains_point(self, longitude: float, latitude: float) -> bool:
        return (
            self.min_longitude <= longitude <= self.max_longitude
            and self.min_latitude <= latitude <= self.max_latitude
        )


@dataclass(frozen=True)
class TemporalWindow:
    start: str
    end: str

    def __post_init__(self) -> None:
        if _parse_utc(self.start) >= _parse_utc(self.end):
            raise ValueError("temporal window start must be before end")

    def contains(self, instant: datetime) -> bool:
        return _parse_utc(self.start) <= instant < _parse_utc(self.end)


@dataclass(frozen=True)
class ApplicabilityDecision:
    """Preview decision shape; not a frozen Core API.

    Relationship strings are explicit and directional.  Resolution is per
    axis: a spatial relation may be safely normalized even when the temporal
    relation makes the overall candidate inapplicable, and vice versa.  A
    failed/unknown axis can never carry a normalized task scope.
    """

    status: str
    spatial_relation: str
    temporal_relation: str
    reasons: tuple[str, ...]
    method_id: str
    method_version: str
    evidence_ref: str | None
    normalized_spatial_scope: str | None = None
    normalized_temporal_scope: str | None = None

    def __post_init__(self) -> None:
        if self.status not in {"applicable", "inapplicable", "unknown"}:
            raise ValueError("unsupported applicability status")

        spatial_satisfied = self.spatial_relation == "candidate_within_task"
        temporal_satisfied = self.temporal_relation == "candidate_in_task_window"

        if spatial_satisfied != (self.normalized_spatial_scope is not None):
            raise ValueError(
                "normalized spatial scope must exist exactly when spatial relation is satisfied"
            )
        if temporal_satisfied != (self.normalized_temporal_scope is not None):
            raise ValueError(
                "normalized temporal scope must exist exactly when temporal relation is satisfied"
            )

        expected_status = (
            "unknown"
            if self.spatial_relation == "unknown" or self.temporal_relation == "unknown"
            else "applicable"
            if spatial_satisfied and temporal_satisfied
            else "inapplicable"
        )
        if self.status != expected_status:
            raise ValueError("overall applicability status disagrees with per-axis relations")


@dataclass(frozen=True)
class EventContextAssessment:
    event_id: str
    decision: ApplicabilityDecision
    candidate: ContextCandidate
    context: TaskContext


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


def _event_id(feature: Mapping[str, object]) -> str | None:
    value = feature.get("id")
    return value if isinstance(value, str) and value.strip() else None


def _event_point(feature: Mapping[str, object]) -> tuple[float, float] | None:
    geometry = feature.get("geometry")
    if not isinstance(geometry, Mapping) or geometry.get("type") != "Point":
        return None
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) < 2:
        return None
    longitude, latitude = coordinates[:2]
    if not isinstance(longitude, (int, float)) or isinstance(longitude, bool):
        return None
    if not isinstance(latitude, (int, float)) or isinstance(latitude, bool):
        return None
    longitude = float(longitude)
    latitude = float(latitude)
    if not math.isfinite(longitude) or not math.isfinite(latitude):
        return None
    return longitude, latitude


def _event_time(feature: Mapping[str, object]) -> datetime | None:
    properties = feature.get("properties")
    if not isinstance(properties, Mapping):
        return None
    value = properties.get("time")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    seconds = float(value) / 1000.0
    if not math.isfinite(seconds):
        return None
    try:
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def resolve_event_applicability(
    feature: Mapping[str, object],
    *,
    bbox: SpatialBBox,
    window: TemporalWindow,
    normalized_spatial_scope: str = TC2_SPATIAL_SCOPE,
    normalized_temporal_scope: str = TC2_TEMPORAL_SCOPE,
) -> ApplicabilityDecision:
    event_id = _event_id(feature)
    point = _event_point(feature)
    event_time = _event_time(feature)

    reasons: list[str] = []
    if point is None:
        spatial_relation = "unknown"
        reasons.append("missing_or_invalid_event_point")
    elif bbox.contains_point(*point):
        spatial_relation = "candidate_within_task"
    else:
        spatial_relation = "candidate_outside_task"
        reasons.append("event_point_outside_task_region")

    if event_time is None:
        temporal_relation = "unknown"
        reasons.append("missing_or_invalid_event_time")
    elif window.contains(event_time):
        temporal_relation = "candidate_in_task_window"
    elif event_time < _parse_utc(window.start):
        temporal_relation = "candidate_before_task_window"
        reasons.append("event_time_before_task_window")
    else:
        temporal_relation = "candidate_after_task_window"
        reasons.append("event_time_after_task_window")

    if spatial_relation == "unknown" or temporal_relation == "unknown":
        status = "unknown"
    elif (
        spatial_relation == "candidate_within_task"
        and temporal_relation == "candidate_in_task_window"
    ):
        status = "applicable"
    else:
        status = "inapplicable"

    evidence_ref = f"usgs-event:{event_id}" if event_id is not None else None
    return ApplicabilityDecision(
        status=status,
        spatial_relation=spatial_relation,
        temporal_relation=temporal_relation,
        reasons=tuple(reasons),
        method_id=TC2_METHOD_ID,
        method_version=TC2_METHOD_VERSION,
        evidence_ref=evidence_ref,
        normalized_spatial_scope=(
            normalized_spatial_scope
            if spatial_relation == "candidate_within_task"
            else None
        ),
        normalized_temporal_scope=(
            normalized_temporal_scope
            if temporal_relation == "candidate_in_task_window"
            else None
        ),
    )


def load_recorded_events(path: Path) -> dict[str, Mapping[str, object]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping) or document.get("type") != "FeatureCollection":
        raise ValueError("recorded USGS fixture must be a GeoJSON FeatureCollection")
    features = document.get("features")
    if not isinstance(features, list):
        raise ValueError("recorded USGS fixture must contain a features list")

    result: dict[str, Mapping[str, object]] = {}
    for feature in features:
        if not isinstance(feature, Mapping):
            raise ValueError("recorded USGS features must be mappings")
        event_id = _event_id(feature)
        if event_id is None:
            raise ValueError("recorded USGS event is missing an id")
        if event_id in result:
            raise ValueError(f"duplicate recorded USGS event id: {event_id}")
        result[event_id] = feature
    return result


def tc2_task() -> TaskFrame:
    return TaskFrame(
        task_id="tc2-usgs-post-earthquake-inspection-context",
        goal=(
            "Prepare recent seismic-event context for a hypothetical "
            "post-earthquake infrastructure field-inspection planning task."
        ),
        subject_refs=("hypothetical-infrastructure-inspection-area",),
        spatial_scope=TC2_SPATIAL_SCOPE,
        temporal_scope=TC2_TEMPORAL_SCOPE,
        outputs=("inspection_context",),
    )


def tc2_requirement() -> ContextRequirement:
    return ContextRequirement(
        requirement_id=TC2_REQUIREMENT_ID,
        what="A recorded earthquake event applicable to the declared inspection region and time window.",
        reason=(
            "The benchmark needs one explicit event-context requirement to test "
            "cross-domain spatiotemporal applicability."
        ),
        critical=True,
        spatial_scope=TC2_SPATIAL_SCOPE,
        temporal_scope=TC2_TEMPORAL_SCOPE,
        metadata={
            "domain": "earthquake-context-preparation",
            "does_not_imply_damage": True,
        },
    )


def candidate_from_event(
    feature: Mapping[str, object],
    decision: ApplicabilityDecision,
) -> ContextCandidate:
    event_id = _event_id(feature) or "unknown-event"
    serialized = json.dumps(
        feature,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    spatial_scope = (
        decision.normalized_spatial_scope
        if decision.normalized_spatial_scope is not None
        else f"tc2-unresolved-spatial:{event_id}"
    )
    temporal_scope = (
        decision.normalized_temporal_scope
        if decision.normalized_temporal_scope is not None
        else f"tc2-unresolved-temporal:{event_id}"
    )

    properties = feature.get("properties")
    magnitude = properties.get("mag") if isinstance(properties, Mapping) else None
    return ContextCandidate(
        candidate_id=f"usgs-event-{event_id}",
        source="usgs-fdsn-event",
        requirement_ids=(TC2_REQUIREMENT_ID,),
        spatial_scope=spatial_scope,
        temporal_scope=temporal_scope,
        acquisition_cost=float(len(serialized)),
        cost_unit="serialized_event_byte",
        metadata={
            "event_id": event_id,
            "magnitude": magnitude,
            "applicability_status": decision.status,
            "spatial_relation": decision.spatial_relation,
            "temporal_relation": decision.temporal_relation,
            "applicability_reasons": decision.reasons,
            "applicability_method_id": decision.method_id,
            "applicability_method_version": decision.method_version,
            "evidence_ref": decision.evidence_ref,
            "does_not_imply_damage": True,
        },
    )


def assess_recorded_event(
    feature: Mapping[str, object],
    *,
    bbox: SpatialBBox | None = None,
    window: TemporalWindow | None = None,
) -> EventContextAssessment:
    bbox = bbox or SpatialBBox(*TC2_TASK_BBOX)
    window = window or TemporalWindow(TC2_WINDOW_START, TC2_WINDOW_END)
    decision = resolve_event_applicability(feature, bbox=bbox, window=window)
    candidate = candidate_from_event(feature, decision)
    context = assess_task_context(
        tc2_task(),
        (tc2_requirement(),),
        (candidate,),
    )
    return EventContextAssessment(
        event_id=_event_id(feature) or "unknown-event",
        decision=decision,
        candidate=candidate,
        context=context,
    )


__all__ = [
    "ApplicabilityDecision",
    "EventContextAssessment",
    "SpatialBBox",
    "TC2_CONTROL_EVENT_ID",
    "TC2_METHOD_ID",
    "TC2_METHOD_VERSION",
    "TC2_REQUIREMENT_ID",
    "TC2_SPATIAL_MISMATCH_EVENT_ID",
    "TC2_SPATIAL_SCOPE",
    "TC2_TASK_BBOX",
    "TC2_TEMPORAL_MISMATCH_EVENT_ID",
    "TC2_TEMPORAL_SCOPE",
    "TC2_WINDOW_END",
    "TC2_WINDOW_START",
    "TemporalWindow",
    "assess_recorded_event",
    "candidate_from_event",
    "load_recorded_events",
    "resolve_event_applicability",
    "tc2_requirement",
    "tc2_task",
]
