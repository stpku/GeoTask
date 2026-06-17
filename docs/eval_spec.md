# GeoTask Eval Lite v0.1 Specification

## What Is GeoTask Eval Lite

GeoTask Eval Lite is a **validation layer** that compares deterministic GeoTask Core
results with normalized LLM outputs. It answers the question:

> "Did the LLM get the right answer?"

It does **not** extend the GeoTask Core format. It is a consumer of Core output.

> **GeoTask Eval is a validation layer, not part of the GeoTask Core format itself.**

> GeoTask Eval 是验证层，不属于 GeoTask Core 格式本体。

---

## Inputs

GeoTask Eval takes two inputs:

1. **Core result** (`dict`): Output from `runner.run_geotask()` -- the deterministic
   ground truth computed by local operators.

2. **Normalized output** (`dict`): Output from `normalizer.normalize_model_output()` --
   the LLM's answer extracted and structured into the measurement format.

Both inputs share a common measurement schema (name, value, unit, verified_by).

---

## Output

GeoTask Eval produces a machine-readable score dict:

```yaml
score:
  total: <0-100>
  distance_match: <bool>
  intersection_match: <bool>
  operator_match: <bool>
  external_data_used_match: <bool>

details:
  expected_distance: <float | null>
  actual_distance: <float | null>
  expected_intersection: <bool | null>
  actual_intersection: <bool | null>
  expected_operations: [<str>, ...]
  actual_operations: [<str>, ...]

warnings: [<str>, ...]
errors: [<str>, ...]
```

---

## Scoring Rubric

Total possible: **100 points**.

| Check                    | Points | Field                  | Error Code                      |
|--------------------------|--------|------------------------|---------------------------------|
| Distance match           | 40     | `distance_match`       | `distance_value_missing` / `distance_value_mismatch` |
| Intersection match       | 40     | `intersection_match`   | `intersection_value_missing` / `intersection_value_mismatch` |
| Operator match           | 15     | `operator_match`       | `operator_missing`              |
| External data match      | 5      | `external_data_used_match` | `external_data_used_mismatch` |

### Distance Comparison

- Expected value from `core_result.measurements["takeoff_to_school_distance"].value`
- Actual value from `normalized_output.measurements["takeoff_to_school_distance"].value`
- Match if `abs(expected - actual) <= tolerance` (default 0.01)

### Intersection Comparison

- Expected value from `core_result.measurements["route_intersects_zone"].value`
- Actual value from `normalized_output.measurements["route_intersects_zone"].value`
- Match if both evaluate to the same boolean (handles string "true"/"false" coercion)

### Operator Comparison

- Expected operations from `core_result.verified_by[].operation`
- Actual operations from `normalized_output.verified_by[].operation`
- Match if **all** expected operations are present in actual (normalized by
  lowercasing and replacing whitespace/hyphens with underscores)

### External Data Comparison

- Expected: `core_result.conclusion.external_data_used`
- Actual: `normalized_output.conclusion.external_data_used`
- If missing from normalized output -> warning (`external_data_used_missing_assumed_false`),
  assumed `false`, no point deduction
- If present but different -> error, -5 points

---

## Warning Codes

| Code                                   | Meaning                                      |
|----------------------------------------|----------------------------------------------|
| `external_data_used_missing_assumed_false` | Normalized output missing external_data_used; assumed false |

## Error Codes

| Code                          | Meaning                                      |
|-------------------------------|----------------------------------------------|
| `distance_value_missing`      | takeoff_to_school_distance not found in model output |
| `distance_value_mismatch`     | Distance value differs beyond tolerance      |
| `intersection_value_missing`  | route_intersects_zone not found in model output |
| `intersection_value_mismatch` | Intersection boolean does not match          |
| `operator_missing`            | One or more expected operators not in actual  |
| `external_data_used_mismatch` | external_data_used flag differs              |

---

## Current Limitations (v0.1)

1. **Fixed measurement names only**. The evaluator hardcodes `takeoff_to_school_distance`
   and `route_intersects_zone`. It does not evaluate arbitrary named measurements.

2. **Two operators only**. Only `distance_2d` and `line_intersects_rect` are checked.

3. **No partial credit within a check**. Distance is either right (40 pts) or wrong (0 pts).

4. **No configurable measurement mapping**. The evaluator does not support
   custom name-to-operation bindings.

5. **No multi-measurement aggregation**. If a task has 10 distances, each one
   is not independently scored.

These limitations are intentional for v0.1. Future versions may add:
- Dynamic measurement name matching
- Configurable scoring weights
- Per-measurement partial credit
- User-defined measurement-to-operation bindings

---

## Example

```bash
$ geotask eval examples/geotask_core_lite.yaml examples/deepseek_output_sample.txt
```

```yaml
score:
  total: 100
  distance_match: true
  intersection_match: true
  operator_match: true
  external_data_used_match: true

details:
  expected_distance: 144.22
  actual_distance: 144.22
  expected_intersection: true
  actual_intersection: true
  expected_operations:
  - distance_2d
  - line_intersects_rect
  actual_operations:
  - distance_2d
  - line_intersects_rect

warnings: []
errors: []
```

---

## Why Eval Is Not Part of Core Format

- **Core** defines *what* a spatial task is (format, objects, ops).
- **Eval** measures *how well* an LLM answered it.

Separating them means:
1. The format can evolve independently of scoring rules.
2. Different evaluators (human review, automated, weighted) can be built
   without changing Core.
3. Core stays minimal -- no scoring logic, no rubric engine, no aggregation.
