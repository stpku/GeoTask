# GeoTask Core Format Specification v0.1-lite

> **Migration note**: The old top-level field `stir:` is still accepted for
> backward compatibility but is deprecated. New documents should use `geotask:`.

## Top-Level Structure

A GeoTask Core document has five top-level sections:

```yaml
geotask:     # Metadata about this GeoTask document
space:       # Coordinate system and unit declaration
objects:     # Spatial objects referenced in the task
ops:         # Operations available (formula strings)
task:        # Questions to answer
```

### `geotask`

| Field     | Type   | Required | Description                  |
|-----------|--------|----------|------------------------------|
| version   | string | Yes      | Format version (e.g. "0.1-lite") |
| name      | string | Yes      | Human-readable document name |
| goal      | string | Yes      | Purpose of this GeoTask document |

### `space`

| Field | Type   | Required | Description                  |
|-------|--------|----------|------------------------------|
| crs   | string | Yes      | Coordinate reference system  |
| unit  | string | Yes      | Unit of measurement          |
| axes  | dict   | No       | Axis labels (e.g. x: "east") |

### `objects`

A mapping from object name to object definition. See Object Types below.

### `ops`

A mapping from operation name to a human-readable formula/description string.
The Core runtime uses its own deterministic implementation -- these strings
are for LLM context only.

### `task`

| Field      | Type   | Required | Description                    |
|------------|--------|----------|--------------------------------|
| questions  | list   | Yes      | Natural language questions     |

---

## Object Types

### `point`

```yaml
object_name:
  type: "point"
  xy: [x, y]       # required, exactly 2 floats
```

### `line`

```yaml
object_name:
  type: "line"
  points:           # required, at least 2 points
    - [x1, y1]
    - [x2, y2]
    - [...]         # additional points allowed but unused in v0.1-lite
```

**Note**: In v0.1-lite, only the first two points are used to form the
line segment. Additional points are preserved but ignored by operators.

### `rect`

```yaml
object_name:
  type: "rect"
  bbox: [min_x, min_y, max_x, max_y]  # required, exactly 4 floats
```

---

## Operations

### `distance_2d`

**Signature**: `distance_2d(a: [x1,y1], b: [x2,y2]) -> float`

2D Euclidean distance: `sqrt((x1 - x2)^2 + (y1 - y2)^2)`

### `line_intersects_rect`

**Signature**: `line_intersects_rect(line_points: [[x,y],...], bbox: [min_x,min_y,max_x,max_y]) -> bool`

Returns `true` if any part of the line segment crosses or touches the
axis-aligned rectangle. Boundary contact counts as intersection.

Only the first two points of `line_points` are used as the segment.

---

## Backward Compatibility

The deprecated `stir` top-level field is still accepted:

```yaml
# Deprecated - use 'geotask' instead
stir:
  version: "0.1-lite"
```

When the old `stir` field is detected, validation passes but a deprecation
warning is emitted. New documents should always use `geotask`.

---

## Current Limitations (v0.1-lite)

1. **2D only**. No Z/elevation coordinate.
2. **Two-point segments only**. Multi-segment polylines are stored but not
   processed by operators.
3. **Axis-aligned rectangles only**. No rotated bounding boxes.
4. **Only three object types**: point, line (segment), rect.
5. **Only two operators**: distance_2d, line_intersects_rect.
6. **No task chaining**. Each GeoTask document is self-contained.
7. **No CRS transforms**. All coordinates are assumed to be in a local
   Cartesian system.
8. **No unit conversion**. All distances are in the declared space unit.

---

## Extensions

The GeoTask specification supports extension through:

- **Domain-specific rule packs**: Additional object types and operators
  defined outside Core (e.g., GeoTask UAV rule pack).
- **Custom task fields**: The `task` section may include additional fields
  (e.g., `constraints`, `priority_policy`) ignored by the Core runner.
- **Audit scaffolding**: Provenance and source references can be layered on
  top of Core by external systems (e.g., GeoTask Audit).

Extensions must not break Core parser compatibility.
