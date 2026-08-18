from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
_ROOT = str(ROOT)
sys.path.insert(0, _ROOT)
try:
    from examples.task_context.refinement_consumer import run_refinement_cycle
finally:
    sys.path.remove(_ROOT)

from geotask_core.task_context import (
    ContextCandidate,
    ContextRequirement,
    TaskFrame,
    assess_task_context,
)


def _task() -> TaskFrame:
    return TaskFrame(
        task_id="delivery-a-b-1500",
        goal="Prepare context for a fictional low-altitude delivery mission",
        subject_refs=("uav-logistics-small",),
        spatial_scope="corridor-a-b",
        temporal_scope="2026-08-19T15:00/16:00",
        outputs=("route_risk_input",),
        context_budget=12.0,
        context_budget_unit="credits",
    )


def _requirements() -> tuple[ContextRequirement, ...]:
    return (
        ContextRequirement(
            requirement_id="weather",
            what="wind and precipitation for the mission corridor",
            reason="weather can change route feasibility",
            spatial_scope="corridor-a-b",
            temporal_scope="2026-08-19T15:00/16:00",
            max_spatial_resolution=1000.0,
            spatial_resolution_unit="meter",
            max_temporal_resolution_seconds=1800.0,
        ),
        ContextRequirement(
            requirement_id="airspace",
            what="applicable temporary airspace restrictions",
            reason="the route must avoid restrictions applicable to this corridor and window",
            spatial_scope="corridor-a-b",
            temporal_scope="2026-08-19T15:00/16:00",
        ),
        ContextRequirement(
            requirement_id="obstacles",
            what="local obstacle context near the candidate corridor",
            reason="local clearance checking requires finer spatial detail",
            spatial_scope="corridor-a-b",
            max_spatial_resolution=10.0,
            spatial_resolution_unit="meter",
        ),
        ContextRequirement(
            requirement_id="poi_labels",
            what="nearby POI labels",
            reason="useful for human explanation but not required for route-risk input",
            critical=False,
            spatial_scope="corridor-a-b",
        ),
    )


def _initial_candidates(*, include_airspace: bool = True) -> tuple[ContextCandidate, ...]:
    candidates = [
        ContextCandidate(
            candidate_id="weather-forecast-500m",
            source="fictional-weather-provider",
            requirement_ids=("weather",),
            spatial_scope="corridor-a-b",
            temporal_scope="2026-08-19T15:00/16:00",
            spatial_resolution=500.0,
            spatial_resolution_unit="meter",
            temporal_resolution_seconds=900.0,
            acquisition_cost=2.0,
            cost_unit="credits",
        ),
        ContextCandidate(
            candidate_id="regional-obstacle-grid-100m",
            source="fictional-map-provider",
            requirement_ids=("obstacles",),
            spatial_scope="corridor-a-b",
            spatial_resolution=100.0,
            spatial_resolution_unit="meter",
            acquisition_cost=1.0,
            cost_unit="credits",
        ),
    ]
    if include_airspace:
        candidates.append(
            ContextCandidate(
                candidate_id="airspace-notice",
                source="fictional-airspace-provider",
                requirement_ids=("airspace",),
                spatial_scope="corridor-a-b",
                temporal_scope="2026-08-19T15:00/16:00",
                acquisition_cost=1.0,
                cost_unit="credits",
            )
        )
    return tuple(candidates)


@dataclass
class ObstacleProvider:
    resolution_meters: float
    calls: list[str] = field(default_factory=list)

    def acquire_refinement(
        self,
        task: TaskFrame,
        requirement: ContextRequirement,
    ) -> tuple[ContextCandidate, ...]:
        self.calls.append(requirement.requirement_id)
        assert task.task_id == "delivery-a-b-1500"
        assert requirement.requirement_id == "obstacles"
        assert requirement.spatial_scope == "corridor-a-b"
        assert requirement.max_spatial_resolution == 10.0
        assert requirement.spatial_resolution_unit == "meter"
        return (
            ContextCandidate(
                candidate_id=f"local-obstacle-grid-{self.resolution_meters:g}m",
                source="fictional-obstacle-refinement-provider",
                requirement_ids=(requirement.requirement_id,),
                spatial_scope=requirement.spatial_scope,
                spatial_resolution=self.resolution_meters,
                spatial_resolution_unit=requirement.spatial_resolution_unit,
                acquisition_cost=2.0,
                cost_unit="credits",
            ),
        )


class NeverCallProvider:
    def acquire_refinement(self, task, requirement):  # pragma: no cover - failure path
        raise AssertionError("provider must not be called when no refinement is requested")


def test_external_consumer_closes_refinable_critical_gap_without_new_core_schema() -> None:
    task = _task()
    requirements = _requirements()
    initial_candidates = _initial_candidates()
    provider = ObstacleProvider(resolution_meters=5.0)

    cycle = run_refinement_cycle(task, requirements, initial_candidates, provider)

    assert cycle.initial_context.status == "insufficient"
    assert cycle.initial_context.gap_requirement_ids == ("obstacles", "poi_labels")
    assert cycle.initial_context.refinement_requirement_ids == ("obstacles",)

    assert cycle.provider_call_requirement_ids == ("obstacles",)
    assert cycle.provider_call_count == 1
    assert provider.calls == ["obstacles"]
    assert cycle.skipped_non_refinement_gap_ids == ("poi_labels",)
    assert cycle.acquired_candidate_ids == ("local-obstacle-grid-5m",)

    assert cycle.final_context.status == "sufficient_with_gaps"
    assert cycle.final_context.gap_requirement_ids == ("poi_labels",)
    assert cycle.final_context.refinement_requirement_ids == ()
    assert cycle.closed_refinement_requirement_ids == ("obstacles",)
    assert cycle.final_context.total_acquisition_cost == 6.0
    assert not cycle.final_context.budget_exceeded

    direct = assess_task_context(
        task,
        requirements,
        initial_candidates
        + (
            ContextCandidate(
                candidate_id="local-obstacle-grid-5m",
                source="fictional-obstacle-refinement-provider",
                requirement_ids=("obstacles",),
                spatial_scope="corridor-a-b",
                spatial_resolution=5.0,
                spatial_resolution_unit="meter",
                acquisition_cost=2.0,
                cost_unit="credits",
            ),
        ),
    )
    assert cycle.final_context == direct


def test_provider_that_remains_too_coarse_cannot_fake_gap_closure() -> None:
    provider = ObstacleProvider(resolution_meters=50.0)

    cycle = run_refinement_cycle(
        _task(),
        _requirements(),
        _initial_candidates(),
        provider,
    )

    assert provider.calls == ["obstacles"]
    assert cycle.final_context.status == "insufficient"
    assert cycle.final_context.gap_requirement_ids == ("obstacles", "poi_labels")
    assert cycle.final_context.refinement_requirement_ids == ("obstacles",)
    assert cycle.closed_refinement_requirement_ids == ()


def test_missing_non_refinement_critical_gap_does_not_trigger_false_acquisition() -> None:
    provider = ObstacleProvider(resolution_meters=5.0)

    cycle = run_refinement_cycle(
        _task(),
        _requirements(),
        _initial_candidates(include_airspace=False),
        provider,
    )

    assert cycle.initial_context.gap_requirement_ids == (
        "airspace",
        "obstacles",
        "poi_labels",
    )
    assert cycle.initial_context.refinement_requirement_ids == ("obstacles",)
    assert cycle.provider_call_requirement_ids == ("obstacles",)
    assert cycle.skipped_non_refinement_gap_ids == ("airspace", "poi_labels")
    assert provider.calls == ["obstacles"]

    # Obstacle refinement succeeds, but the unrelated missing critical airspace
    # evidence remains a real gap and keeps the context insufficient.
    assert cycle.final_context.status == "insufficient"
    assert cycle.final_context.gap_requirement_ids == ("airspace", "poi_labels")
    assert cycle.final_context.refinement_requirement_ids == ()


def test_no_refinement_signal_means_no_provider_call() -> None:
    task = _task()
    requirements = _requirements()
    candidates = _initial_candidates() + (
        ContextCandidate(
            candidate_id="local-obstacle-grid-5m",
            source="fictional-obstacle-refinement-provider",
            requirement_ids=("obstacles",),
            spatial_scope="corridor-a-b",
            spatial_resolution=5.0,
            spatial_resolution_unit="meter",
            acquisition_cost=2.0,
            cost_unit="credits",
        ),
    )

    cycle = run_refinement_cycle(task, requirements, candidates, NeverCallProvider())

    assert cycle.initial_context.status == "sufficient_with_gaps"
    assert cycle.initial_context.refinement_requirement_ids == ()
    assert cycle.provider_call_count == 0
    assert cycle.acquired_candidate_ids == ()
    assert cycle.final_context == cycle.initial_context
