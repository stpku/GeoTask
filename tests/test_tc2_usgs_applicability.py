from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "benchmarks" / "tc2_usgs" / "fixtures" / "ridgecrest_history_201907"

_ROOT = str(ROOT)
sys.path.insert(0, _ROOT)
try:
    from benchmarks.tc2_usgs.applicability import (
        ApplicabilityDecision,
        SpatialBBox,
        TC2_CONTROL_EVENT_ID,
        TC2_SPATIAL_MISMATCH_EVENT_ID,
        TC2_TASK_BBOX,
        TC2_TEMPORAL_MISMATCH_EVENT_ID,
        TC2_WINDOW_END,
        TC2_WINDOW_START,
        TemporalWindow,
        assess_recorded_event,
        candidate_from_event,
        load_recorded_events,
        resolve_event_applicability,
        tc2_requirement,
        tc2_task,
    )
    from geotask_core.task_context import assess_task_context
finally:
    sys.path.remove(_ROOT)


def _fixture_events():
    return load_recorded_events(FIXTURE_ROOT / "events.geojson")


def test_tc2_recorded_usgs_fixture_is_exact_and_nonempty():
    payload = (FIXTURE_ROOT / "events.geojson").read_bytes()
    summary = json.loads((FIXTURE_ROOT / "summary.json").read_text(encoding="utf-8"))

    assert len(payload) == summary["payload_bytes"] == 24_177
    assert hashlib.sha256(payload).hexdigest() == summary["sha256"]
    assert summary["event_count"] == 30
    assert summary["provider"] == "USGS FDSN Event Web Service"
    assert summary["query_parameters"] == {
        "format": "geojson",
        "starttime": "2019-07-04T00:00:00Z",
        "endtime": "2019-07-08T00:00:00Z",
        "minlatitude": 33.0,
        "maxlatitude": 37.0,
        "minlongitude": -120.0,
        "maxlongitude": -115.0,
        "minmagnitude": 4.5,
        "orderby": "time-asc",
    }


def test_tc2_three_real_events_are_orthogonal_controls():
    events = _fixture_events()
    assert len(events) == 30

    control = events[TC2_CONTROL_EVENT_ID]
    temporal = events[TC2_TEMPORAL_MISMATCH_EVENT_ID]
    spatial = events[TC2_SPATIAL_MISMATCH_EVENT_ID]

    assert control["geometry"]["coordinates"][:2] == [-117.5993333, 35.7695]
    assert control["properties"]["mag"] == 7.1
    assert control["properties"]["time"] == 1_562_383_193_040

    assert temporal["geometry"]["coordinates"][:2] == [-117.5038333, 35.7053333]
    assert temporal["properties"]["mag"] == 6.4
    assert temporal["properties"]["time"] == 1_562_261_629_000

    assert spatial["geometry"]["coordinates"][:2] == [-117.7495, 35.9011667]
    assert spatial["properties"]["mag"] == 5.5
    assert spatial["properties"]["time"] == 1_562_384_873_420


def test_tc2_real_control_is_applicable_and_normalized():
    events = _fixture_events()
    assessment = assess_recorded_event(events[TC2_CONTROL_EVENT_ID])

    assert assessment.decision.status == "applicable"
    assert assessment.decision.spatial_relation == "candidate_within_task"
    assert assessment.decision.temporal_relation == "candidate_in_task_window"
    assert assessment.decision.reasons == ()
    assert assessment.decision.normalized_spatial_scope == tc2_task().spatial_scope
    assert assessment.decision.normalized_temporal_scope == tc2_task().temporal_scope
    assert assessment.context.status == "sufficient"
    assert assessment.context.gap_requirement_ids == ()


def test_tc2_real_spatial_mismatch_isolated_from_time():
    events = _fixture_events()
    assessment = assess_recorded_event(events[TC2_SPATIAL_MISMATCH_EVENT_ID])

    assert assessment.decision.status == "inapplicable"
    assert assessment.decision.spatial_relation == "candidate_outside_task"
    assert assessment.decision.temporal_relation == "candidate_in_task_window"
    assert assessment.decision.reasons == ("event_point_outside_task_region",)
    assert assessment.decision.normalized_spatial_scope is None
    assert assessment.decision.normalized_temporal_scope is None
    assert assessment.context.status == "insufficient"
    assert assessment.context.gap_requirement_ids == ("seismic_event_context",)
    assert assessment.context.assessments[0].reasons == ("spatial_scope_mismatch", "temporal_scope_mismatch")


def test_tc2_real_temporal_mismatch_isolated_from_space():
    events = _fixture_events()
    assessment = assess_recorded_event(events[TC2_TEMPORAL_MISMATCH_EVENT_ID])

    assert assessment.decision.status == "inapplicable"
    assert assessment.decision.spatial_relation == "candidate_within_task"
    assert assessment.decision.temporal_relation == "candidate_before_task_window"
    assert assessment.decision.reasons == ("event_time_before_task_window",)
    assert assessment.decision.normalized_spatial_scope is None
    assert assessment.decision.normalized_temporal_scope is None
    assert assessment.context.status == "insufficient"
    assert assessment.context.gap_requirement_ids == ("seismic_event_context",)


def test_tc2_unknown_is_not_false_and_never_normalizes():
    events = _fixture_events()
    malformed = deepcopy(events[TC2_CONTROL_EVENT_ID])
    malformed["geometry"] = None
    malformed["properties"]["time"] = None

    bbox = SpatialBBox(*TC2_TASK_BBOX)
    window = TemporalWindow(TC2_WINDOW_START, TC2_WINDOW_END)
    decision = resolve_event_applicability(malformed, bbox=bbox, window=window)

    assert decision.status == "unknown"
    assert decision.spatial_relation == "unknown"
    assert decision.temporal_relation == "unknown"
    assert decision.reasons == (
        "missing_or_invalid_event_point",
        "missing_or_invalid_event_time",
    )
    assert decision.normalized_spatial_scope is None
    assert decision.normalized_temporal_scope is None

    candidate = candidate_from_event(malformed, decision)
    context = assess_task_context(tc2_task(), (tc2_requirement(),), (candidate,))
    assert context.status == "insufficient"
    assert context.gap_requirement_ids == ("seismic_event_context",)


def test_tc2_nonapplicable_decision_cannot_smuggle_normalized_scope():
    with pytest.raises(ValueError, match="must not normalize"):
        ApplicabilityDecision(
            status="inapplicable",
            spatial_relation="candidate_outside_task",
            temporal_relation="candidate_in_task_window",
            reasons=("event_point_outside_task_region",),
            method_id="point-event-task-applicability",
            method_version="0.1",
            evidence_ref="usgs-event:test",
            normalized_spatial_scope="forbidden-normalized-scope",
        )


def test_tc2_task_window_and_bbox_are_explicit_benchmark_contracts():
    bbox = SpatialBBox(*TC2_TASK_BBOX)
    window = TemporalWindow(TC2_WINDOW_START, TC2_WINDOW_END)

    assert bbox.contains_point(-117.5993333, 35.7695) is True
    assert bbox.contains_point(-117.5038333, 35.7053333) is True
    assert bbox.contains_point(-117.7495, 35.9011667) is False

    # The benchmark window is half-open [start, end).
    from datetime import datetime, timezone

    assert window.contains(datetime(2019, 7, 6, 3, 0, tzinfo=timezone.utc)) is True
    assert window.contains(datetime(2019, 7, 6, 3, 59, 59, tzinfo=timezone.utc)) is True
    assert window.contains(datetime(2019, 7, 6, 4, 0, tzinfo=timezone.utc)) is False
