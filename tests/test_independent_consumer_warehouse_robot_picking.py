from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from examples.independent_consumers.warehouse_robot_picking.consumer import (
    WarehouseProviderSnapshot,
    build_warehouse_pick_context,
    refresh_after_sensor_change,
    requirement_kind_map,
)


def _by_kind(run, kind: str):
    return next(item for item in run.cognition if item.requirement.kind == kind)


def test_independent_consumer_builds_sufficient_minimum_context() -> None:
    run = build_warehouse_pick_context(task_id="public-warehouse-pick")

    assert run.construction.sufficiency.status == "sufficient"
    assert len(run.construction.context.values) == 4
    assert run.minimum is not None
    assert run.minimum.sufficiency.status == "sufficient"
    assert run.minimum.minimality.status == "minimal"

    kinds = requirement_kind_map(run.minimum.context.requirements)
    assert {kinds[requirement_id] for requirement_id in run.minimum.context.values} == {
        "route-geometry",
        "bin-inventory",
        "aisle-clearance",
    }
    assert {
        kinds[requirement_id]
        for requirement_id in run.minimum.minimality.removed_requirement_ids
    } == {"zone-annotation"}


def test_relevance_applicability_and_resolution_remain_separate() -> None:
    wrong_aisle = build_warehouse_pick_context(
        WarehouseProviderSnapshot(sensor_aisle="aisle-9"),
        task_id="public-wrong-aisle",
    )
    clearance = _by_kind(wrong_aisle, "aisle-clearance")
    assert clearance.relevance.status == "relevant"
    assert clearance.applicability.status == "not_applicable"
    assert clearance.resolution.status == "adequate"
    assert wrong_aisle.construction.sufficiency.status == "insufficient"

    coarse_map = build_warehouse_pick_context(
        WarehouseProviderSnapshot(map_cell_size_m=1.0),
        task_id="public-coarse-map",
    )
    route = _by_kind(coarse_map, "route-geometry")
    assert route.relevance.status == "relevant"
    assert route.applicability.status == "applicable"
    assert route.resolution.status == "inadequate"
    assert coarse_map.construction.sufficiency.status == "insufficient"


def test_context_sufficiency_is_not_robot_action_authorization() -> None:
    run = build_warehouse_pick_context(
        WarehouseProviderSnapshot(sensor_clearance_m=0.80),
        task_id="public-narrow-clearance",
    )
    clearance = _by_kind(run, "aisle-clearance")

    assert run.task.metadata["robot_width_m"] == 0.90
    assert clearance.candidate.payload["clearance_m"] == 0.80
    assert clearance.item.assessment.status == "satisfied"
    assert run.construction.sufficiency.status == "sufficient"

    field_names = set(run.__dataclass_fields__)
    for forbidden in ("decision", "action", "execute", "authorization"):
        assert all(forbidden not in name for name in field_names)


def test_sensor_change_is_bounded_and_reproves_minimum_context() -> None:
    prior = build_warehouse_pick_context(task_id="public-temporal")
    assert prior.minimum is not None

    temporal = refresh_after_sensor_change(
        prior,
        WarehouseProviderSnapshot(sensor_clearance_m=0.80, revision="r2"),
    )
    kinds = requirement_kind_map(prior.minimum.context.requirements)

    assert temporal.continuity.status == "bounded_refresh_required"
    assert {
        kinds[requirement_id]
        for requirement_id in temporal.refresh.reassessed_requirement_ids
    } == {"aisle-clearance"}
    assert {
        kinds[requirement_id]
        for requirement_id in temporal.refresh.reused_carried_requirement_ids
    } == {"route-geometry", "bin-inventory"}
    assert temporal.refresh.sufficiency.status == "sufficient"
    assert temporal.refresh.minimality_reassessment_required is True
    assert temporal.reminimum is not None
    assert temporal.reminimum.sufficiency.status == "sufficient"
    assert temporal.reminimum.minimality.status == "minimal"
