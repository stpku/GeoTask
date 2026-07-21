# GeoTask Core Operator Registry

The Core operator registry is the public-safe catalog of deterministic
operators available to GeoTask Core. It is intentionally limited to general
spatial, time, and altitude primitives and does not contain domain-specific
approval rules, regulatory thresholds, or patent-sensitive workflows.

## Inspect From CLI

```bash
python -m geotask_core.cli inspect operators
python -m geotask_core.cli inspect operators distance_2d
```

The CLI prints the same metadata exposed by
`geotask_core.operator_registry`.

## Registry Summary

| Operator | Output | Supported Input | Notes |
|----------|--------|-----------------|-------|
| `distance_2d` | `float` | point + point | Euclidean distance in local 2D coordinates. |
| `line_intersects_rect` | `bool` | line + rect | Boundary contact counts as intersection. |
| `point_to_line_distance_2d` | `float` | point + line | Shortest distance to a line segment. |
| `rect_contains_point` | `bool` | rect + point | Boundary contact counts as containment. |
| `time_overlap` | `bool` | time interval + time interval | Boundary contact counts as overlap. |
| `altitude_overlap` | `bool` | altitude range + altitude range | Boundary contact counts as overlap. |

## Metadata Fields

Each registry entry includes:

- `name`: stable operator identifier.
- `input_shape`: expected public-safe input shape.
- `output_type`: result type, currently `float` or `bool`.
- `deterministic`: always `true` for Core operators.
- `supported_geometry`: compatible object or interval categories.
- `error_codes`: stable diagnostic categories that callers can surface.
- `examples`: compact input/output examples for CLI inspection and docs.

## Boundary

The registry describes only deterministic Core primitives. It does not define
domain-pack policy, operational approval, flight authorization, model routing,
cost optimization, or human-review workflows. Domain packs may reference Core
operators, but they should not mutate this registry or override Core semantics.

