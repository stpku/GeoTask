import pytest

from geotask_core.task_context import (
    ContextCandidate,
    ContextRequirement,
    TaskFrame,
    assess_task_context,
    evaluate_context_candidate,
)


def _task(*, budget=10.0):
    return TaskFrame(
        task_id="mission-001",
        goal="Prepare a bounded low-altitude mission context",
        subject_refs=("uav-001",),
        spatial_scope="corridor-a-b",
        temporal_scope="window-1500-1600",
        outputs=("mission_context",),
        context_budget=budget,
    )


def test_complete_context_is_sufficient():
    requirements = [
        ContextRequirement(
            requirement_id="weather",
            what="weather along the corridor",
            reason="wind can change mission feasibility",
            spatial_scope="corridor-a-b",
            temporal_scope="window-1500-1600",
            max_spatial_resolution=1000.0,
            max_temporal_resolution_seconds=1800.0,
        ),
        ContextRequirement(
            requirement_id="airspace",
            what="temporary airspace restrictions",
            reason="the route must avoid applicable restrictions",
            spatial_scope="corridor-a-b",
            temporal_scope="window-1500-1600",
        ),
    ]
    candidates = [
        ContextCandidate(
            candidate_id="weather-grid",
            source="weather-provider",
            requirement_ids=("weather",),
            spatial_scope="corridor-a-b",
            temporal_scope="window-1500-1600",
            spatial_resolution=500.0,
            temporal_resolution_seconds=900.0,
            acquisition_cost=2.0,
        ),
        ContextCandidate(
            candidate_id="airspace-notice",
            source="airspace-provider",
            requirement_ids=("airspace",),
            spatial_scope="corridor-a-b",
            temporal_scope="window-1500-1600",
            acquisition_cost=1.0,
        ),
    ]

    result = assess_task_context(_task(), requirements, candidates)

    assert result.status == "sufficient"
    assert result.sufficient is True
    assert result.within_budget is True
    assert result.ready is True
    assert result.gap_requirement_ids == ()
    assert result.refinement_requirement_ids == ()
    assert result.total_acquisition_cost == 3.0
    assert result.budget_exceeded is False


def test_missing_critical_requirement_is_insufficient():
    requirements = [
        ContextRequirement(
            requirement_id="weather",
            what="weather",
            reason="required for the mission",
        ),
        ContextRequirement(
            requirement_id="airspace",
            what="airspace",
            reason="required for the mission",
        ),
    ]
    candidates = [
        ContextCandidate(
            candidate_id="weather-grid",
            source="weather-provider",
            requirement_ids=("weather",),
        )
    ]

    result = assess_task_context(_task(), requirements, candidates)

    assert result.status == "insufficient"
    assert result.sufficient is False
    assert result.ready is False
    assert result.gap_requirement_ids == ("airspace",)


def test_too_coarse_candidate_requests_refinement():
    requirement = ContextRequirement(
        requirement_id="obstacles",
        what="obstacle context",
        reason="corridor clearance requires local detail",
        spatial_scope="corridor-a-b",
        max_spatial_resolution=10.0,
    )
    candidate = ContextCandidate(
        candidate_id="coarse-obstacles",
        source="regional-map",
        requirement_ids=("obstacles",),
        spatial_scope="corridor-a-b",
        spatial_resolution=100.0,
    )

    assessment = evaluate_context_candidate(_task(), requirement, candidate)
    result = assess_task_context(_task(), [requirement], [candidate])

    assert assessment.relevant is True
    assert assessment.applicable is True
    assert assessment.resolution_sufficient is False
    assert assessment.usable is False
    assert "spatial_resolution_too_coarse" in assessment.reasons
    assert result.status == "insufficient"
    assert result.refinement_requirement_ids == ("obstacles",)


def test_scope_mismatch_is_not_silently_inferred():
    requirement = ContextRequirement(
        requirement_id="weather",
        what="weather",
        reason="task-specific weather is required",
        spatial_scope="corridor-a-b",
    )
    candidate = ContextCandidate(
        candidate_id="other-corridor-weather",
        source="weather-provider",
        requirement_ids=("weather",),
        spatial_scope="corridor-c-d",
    )

    assessment = evaluate_context_candidate(_task(), requirement, candidate)

    assert assessment.relevant is True
    assert assessment.applicable is False
    assert assessment.usable is False
    assert "spatial_scope_mismatch" in assessment.reasons


def test_noncritical_gap_keeps_context_usable():
    requirements = [
        ContextRequirement(
            requirement_id="weather",
            what="weather",
            reason="critical mission context",
        ),
        ContextRequirement(
            requirement_id="poi_labels",
            what="nearby POI labels",
            reason="useful for explanation only",
            critical=False,
        ),
    ]
    candidates = [
        ContextCandidate(
            candidate_id="weather-grid",
            source="weather-provider",
            requirement_ids=("weather",),
        )
    ]

    result = assess_task_context(_task(), requirements, candidates)

    assert result.status == "sufficient_with_gaps"
    assert result.sufficient is True
    assert result.ready is True
    assert result.gap_requirement_ids == ("poi_labels",)


def test_budget_is_separate_from_information_sufficiency():
    requirement = ContextRequirement(
        requirement_id="weather",
        what="weather",
        reason="critical mission context",
    )
    candidate = ContextCandidate(
        candidate_id="premium-weather",
        source="weather-provider",
        requirement_ids=("weather",),
        acquisition_cost=8.0,
    )

    result = assess_task_context(_task(budget=5.0), [requirement], [candidate])

    assert result.status == "over_budget"
    assert result.sufficient is True
    assert result.within_budget is False
    assert result.ready is False
    assert result.gap_requirement_ids == ()
    assert result.budget_exceeded is True


def test_unknown_requirement_reference_fails_closed():
    candidate = ContextCandidate(
        candidate_id="candidate-x",
        source="provider-x",
        requirement_ids=("unknown",),
    )

    with pytest.raises(ValueError, match="unknown requirement ids"):
        assess_task_context(_task(), [], [candidate])


def test_negative_cost_or_resolution_is_rejected():
    with pytest.raises(ValueError, match="acquisition_cost"):
        ContextCandidate(
            candidate_id="bad-cost",
            source="provider",
            requirement_ids=("weather",),
            acquisition_cost=-1.0,
        )

    with pytest.raises(ValueError, match="max_spatial_resolution"):
        ContextRequirement(
            requirement_id="bad-resolution",
            what="bad",
            reason="bad",
            max_spatial_resolution=-1.0,
        )
