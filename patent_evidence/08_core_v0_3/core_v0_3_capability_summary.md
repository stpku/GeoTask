# GeoTask Core Normalizer / Verifier v0.3 — Capability Summary

## New Operators (v0.3 adds 4)

| Operator | v0.1/v0.2 | v0.3 Core | Description |
|----------|-----------|-----------|-------------|
| `distance_2d` | ✅ Core | ✅ Core | 2D Euclidean distance |
| `line_intersects_rect` | ✅ Core | ✅ Core | Line-rectangle intersection |
| `point_to_line_distance_2d` | Benchmark only | ✅ **Core** | Point-to-line-segment distance |
| `rect_contains_point` | Benchmark only | ✅ **Core** | Rectangle containment |
| `time_overlap` | Benchmark only | ✅ **Core** | Time interval overlap |
| `altitude_overlap` | Benchmark only | ✅ **Core** | Altitude range overlap |

## New Statuses (v0.3 unified hierarchy)

| Status | Priority | When |
|--------|----------|------|
| `invalid_operator` | Highest | Non-existent operator referenced (e.g., "haversine") |
| `invalid_reference` | High | Object referenced that doesn't exist in geotask_data |
| `contradicted` | Medium | Model output contradicts local deterministic result |
| `need_review` | Low | Missing values, missing operators, unclear references |
| `need_data` | Lowest | Requires external data not available locally |
| `verified` | Baseline | All checks pass |

## New Review Reasons

| Reason | Trigger |
|--------|---------|
| `operator_reference_missing` | Values extracted but operator not mentioned |
| `value_not_found` | No numeric value extracted for expected measurement |
| `object_reference_missing` | Object references unclear in output |
| `invalid_operator` | Non-existent operator name detected |
| `invalid_reference` | Object name not in geotask_data |
| `unit_mismatch` | km used where meter expected |
| `unsupported_operator` | Operator known but not supported in Core |
| `ambiguous_negation` | Chinese negation ambiguous in context |

## Chinese Negation Support

| Boolean Type | Negation Pattern | Correct Detection |
|-------------|-----------------|-------------------|
| Intersection | 不相交, 不存在相交 | ✅ False |
| Contains | 不包含, 不含, 不在矩形内 | ✅ False |
| Time overlap | 时间不重叠 | ✅ False |
| Altitude overlap | 高度不重叠 | ✅ False |

## Error Type Coverage

| Error Type | Detection Mechanism | Status |
|-----------|-------------------|--------|
| Wrong numeric value | Tolerance comparison (>0.05) | contradicted |
| Wrong boolean | Exact match fail | contradicted |
| Missing operator | Operator reference detection | need_review |
| Missing value | Value extraction fail | need_review |
| Unit mismatch | km detection in text | need_review |
| Invalid operator | Operator name validation | invalid_operator |
| Invalid reference | Object name validation | invalid_reference |
| Chinese negation | Negation-first pattern matching | verified/contradicted |

---

*Evidence artifact: `patent_evidence/08_core_v0_3/core_v0_3_capability_summary.md`*
