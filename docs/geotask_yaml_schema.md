# GeoTask YAML Schema

This document describes the public-safe Core YAML structure accepted by the
current parser. It covers general task, object, operator, and interval fields
only. Domain-specific extensions should be documented in separate domain-pack
materials and must not change Core operator semantics.

## Minimal Structure

```yaml
geotask:
  version: "0.2"
  name: "Example"
  goal: "Run deterministic checks."

space:
  crs: "local_xy_m"
  unit: "meter"
  axes:
    x: "east"
    y: "north"

objects: {}
ops: {}
task:
  questions: []
```

Required top-level keys:

- `geotask`
- `space`
- `objects`
- `ops`
- `task`

Optional reserved top-level keys:

- `assertions`
- `expected_results`

The deprecated top-level `stir` key is still accepted for backward
compatibility when `geotask` is absent.

## Optional Validation Sections

### Assertions

`assertions` is an optional list of declarative validation checks.

```yaml
assertions:
  - id: "distance_check"
    operator: "distance_2d"
    object_refs: ["takeoff", "school"]
```

Each assertion currently requires:

- `id`
- `operator`
- `object_refs`

The operator must be a registered Core operator, and every `object_refs` entry
must refer to a known object id from `objects`.

### Expected Results

`expected_results` is an optional list of expected output fixtures.

```yaml
expected_results:
  - name: "takeoff_to_school_distance"
    value: 144.22
    unit: "meter"
```

Each expected result currently requires:

- `name`
- `value`

`unit` is optional.

## Object Types

### Point

```yaml
point_a:
  type: "point"
  xy: [0, 0]
```

`xy` must be a two-item coordinate list.

### Line

```yaml
route:
  type: "line"
  points:
    - [0, 0]
    - [10, 0]
```

`points` must contain at least two two-item coordinate lists.

### Rect

```yaml
zone:
  type: "rect"
  bbox: [0, 0, 10, 10]
```

`bbox` must be `[min_x, min_y, max_x, max_y]`.

### Time

```yaml
window_a:
  type: "time"
  interval: ["08:00", "10:00"]
```

`interval` must be a two-item `HH:MM` list with start less than or equal to end.

### Altitude

```yaml
band_a:
  type: "altitude"
  range: [100, 200]
```

`range` must be a numeric `[min, max]` list with min less than or equal to max.

## Operators

The `ops` mapping requests deterministic Core operators. Supported public-safe
operators are listed in `docs/operator_registry.md` and can be inspected with:

```bash
python -m geotask_core.cli inspect operators
```

## Diagnostics

New callers should use `validate_geotask_diagnostics()` for structured
diagnostics. Each diagnostic contains:

- `path`: document path, such as `objects.window_a.interval`.
- `code`: stable diagnostic code.
- `message`: human-readable explanation.
- `suggested_fix`: concise repair guidance.

The legacy `validate_geotask()` API still returns a list of strings for
backward compatibility. Those strings are rendered from the same structured
diagnostics.

Stable diagnostic codes include:

- `missing_field`
- `invalid_type`
- `unknown_object_type`
- `invalid_coordinates`
- `invalid_interval`
- `unknown_field`
- `invalid_operator`

`invalid_interval` is used for invalid time intervals and altitude ranges. For
example:

```yaml
- path: objects.window_a.interval
  code: invalid_interval
  message: "objects.window_a.interval: invalid_interval: must be ['HH:MM', 'HH:MM'] with start <= end."
  suggested_fix: "Use a valid two-item HH:MM interval with start <= end."
- path: objects.band_a.range
  code: invalid_interval
  message: "objects.band_a.range: invalid_interval: must be [min, max] with min <= max."
  suggested_fix: "Use a numeric two-item range with min <= max."
```

Unknown fields and unsupported operators also surface structured diagnostics.
Examples:

```yaml
- path: mystery
  code: unknown_field
  message: "Unexpected top-level field 'mystery'."
  suggested_fix: "Remove 'mystery' or move it under a supported section."
- path: ops.geo_distance
  code: invalid_operator
  message: "Unsupported operator 'geo_distance' in ops."
  suggested_fix: "Use one of: distance_2d, line_intersects_rect, point_to_line_distance_2d, rect_contains_point, time_overlap, altitude_overlap."
```

## Examples

Public-safe Core examples:

- `examples/core/minimal_valid.yaml`
- `examples/core/time_altitude_overlap.yaml`
- `examples/core/assertions_expected_results.yaml`
- `examples/geotask_core_lite.yaml`

List examples from the CLI:

```bash
python -m geotask_core.cli inspect examples
```

## Boundary

The schema describes general Core data only. It does not define approval
statuses, regulatory thresholds, model routing, cost optimization, or
domain-specific review workflows.
