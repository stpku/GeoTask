# Warehouse Robot Picking — Independent Task Context Example

This public example shows how GeoTask can build and maintain task context for a warehouse robot picking task using three independent provider types:

```text
Indoor GIS / topology
Inventory API
Aisle-clearance sensor
        ↓
TaskFrame
        ↓
ContextRequirement[]
        ↓
ContextCandidate[]
        ↓
Relevance / Applicability / Resolution Adequacy
        ↓
ContextAssessment[]
        ↓
SufficiencyAssessment
        ↓
TaskContext
        ↓
Minimum Sufficient TaskContext
        ↓
Sensor change
        ↓
Bounded Temporal Reassessment / Refresh
        ↓
Re-proved Minimum Context
```

The example is intentionally outside `src/geotask_core`. Warehouse-specific thresholds, provider adapters, and policies remain consumer-owned.

## Providers

- `WarehouseGISProvider` supplies indoor route geometry and an optional zone annotation.
- `WarehouseInventoryAPIProvider` supplies current target-bin inventory.
- `WarehouseAisleSensorProvider` supplies current measured aisle clearance.

Each provider returns `ContextCandidate` objects only. Provider output does not automatically imply relevance, applicability, adequate resolution, requirement satisfaction, or task sufficiency.

## Important semantic boundary

One scenario uses a robot width of `0.90 m` and a measured aisle clearance of `0.80 m`.

GeoTask can still conclude that the **context is sufficient** when the measurement is relevant, applicable, fresh, and resolution-adequate. It does **not** conclude that the robot may traverse the aisle.

```text
Context Sufficient ≠ Domain Decision
Context Sufficient ≠ Action Authorization
```

A downstream warehouse-control or motion-safety system remains responsible for the action decision.

## Minimum context

The healthy example initially carries four values:

- route geometry;
- bin inventory;
- aisle clearance;
- optional zone annotation.

The explicit minimality method removes only the optional annotation and builds a new target context with its own explicit sufficiency proof.

## Temporal continuity

The example changes only the aisle-clearance sensor state. GeoTask maps the change to the affected requirement, reuses unaffected carried context, refreshes the changed requirement, produces a new explicit sufficiency assessment, and re-proves minimum context.

The change adapter emits the provider-neutral delta wire expected by the current temporal reassessment contract; no external runtime is required for this deterministic example.

## Run

```bash
python - <<'PY'
from examples.independent_consumers.warehouse_robot_picking.consumer import (
    WarehouseProviderSnapshot,
    build_warehouse_pick_context,
    refresh_after_sensor_change,
)

initial = build_warehouse_pick_context()
print(initial.construction.sufficiency.status)
print(len(initial.construction.context.values), len(initial.minimum.context.values))

temporal = refresh_after_sensor_change(
    initial,
    WarehouseProviderSnapshot(sensor_clearance_m=0.80, revision="r2"),
)
print(temporal.continuity.status)
print(temporal.refresh.sufficiency.status)
PY
```

Expected high-level result:

```text
sufficient
4 3
bounded_refresh_required
sufficient
```

This is a deterministic reference example, not a live warehouse integration or robot-safety certification.
