# GeoTask Core Operator Registry

The Core operator registry is the public-safe catalog of deterministic
operators available to GeoTask Core. It is intentionally limited to general
spatial, time, and altitude primitives and does not contain domain-specific
approval rules, regulatory thresholds, or patent-sensitive workflows.

## Inspect From CLI

```bash
python -m geotask_core.cli inspect operators
python -m geotask_core.cli inspect operators distance_2d
python -m geotask_core.cli inspect operators --format json
python -m geotask_core.cli inspect operators distance_2d --format json
```

The default output remains human-readable. `--format json` exposes the same collection- or item-level Registry metadata as stable structured JSON for developer tooling.

The CLI prints the same metadata exposed by
`geotask_core.operator_registry`. That compact metadata is generated from the
full v1 `OperatorContract` registry, which is the single source of truth for
operator names, arity, input types, outputs, error codes, examples, and
invariants.

## Registry Summary

| Operator | Output | Supported Input | Notes |
|----------|--------|-----------------|-------|
| `distance_2d` | `float` | point + point | Euclidean distance in local 2D coordinates. |
| `line_intersects_rect` | `bool` | polyline + rect | Boundary contact counts as intersection. |
| `multi_polyline_intersects_rect` | `bool` | multi-polyline + rect | True when any member touches or crosses the rectangle. |
| `point_in_polygon` | `bool` | point + polygon | Point-first predicate; one closed exterior ring and boundary contact counts as containment. |
| `polygon_contains_point` | `bool` | polygon + point | Container-first equivalent of `point_in_polygon`; object order is explicit and boundary contact counts. |
| `point_to_line_distance_2d` | `float` | point + polyline | Shortest distance to a polyline. |
| `rect_contains_point` | `bool` | rect + point | Boundary contact counts as containment. |
| `time_overlap` | `bool` | time interval + time interval | Boundary contact counts as overlap. |
| `altitude_overlap` | `bool` | altitude range + altitude range | Boundary contact counts as overlap. |
| `trajectory_duration_seconds` | `float` | trajectory | Elapsed seconds between the first and last explicit samples; no interpolation or prediction. |
| `trajectory_segment_metrics` | `list` | trajectory | Ordered adjacent-sample bindings with duration, planar distance, and average speed in document horizontal units per second. |
| `trajectory_segment_classifications` | `list` | trajectory + explicit thresholds | Classifies each adjacent segment as `stationary_candidate`, `moving_observed`, `observation_gap`, or `unverifiable` without selecting defaults or interpolating gaps. |
| `trajectory_segment_acceleration_estimates` | `list` | trajectory + explicit midpoint/gap parameters | Estimates scalar acceleration between adjacent segment-average speeds; any participating segment beyond the declared maximum gap yields `unverifiable` with null acceleration. |
| `trajectory_identity_candidate` | `dict` | two trajectories + explicit time/distance/class policy | Compares only the first trajectory's final sample with the second trajectory's first sample and returns `same_object_candidate`, `different_object_candidate`, or `unverifiable` without merging identities. |

## Metadata Fields

Each registry entry includes:

- `name`: stable operator identifier.
- `input_shape`: expected public-safe input shape.
- `output_type`: result type, currently `float`, `bool`, or `list`.
- `deterministic`: always `true` for Core operators.
- `supported_geometry`: compatible object or interval categories.
- `error_codes`: stable diagnostic categories that callers can surface.
- `examples`: compact input/output examples for CLI inspection and docs.

## Boundary

The registry describes only deterministic Core primitives. It does not define
domain-pack policy, operational approval, flight authorization, model routing,
cost optimization, or human-review workflows. Domain packs may reference Core
operators, but they should not mutate this registry or override Core semantics.

