# GeoTask Core Normalizer / Verifier v0.3

## Purpose

v0.3 is the **production Core backfill** — it takes the stable multi-operator, multi-error-type capabilities demonstrated by Benchmark v0.2 and integrates them into `src/geotask_core/`:

- **Normalizer** (`normalizer.py`) — enhanced with invalid operator/reference detection, unit mismatch, unified status hierarchy.
- **Verifier** (`verifier.py`) — enhanced with unified status priority, operator/reference validation.
- **Runner** (`runner.py`) — enhanced with generic type-based auto-detection for 6 operators.
- **Result Schema** (`result_schema.py`) — new statuses (invalid_operator, invalid_reference) and review reason constants.
- **Ops** (`ops.py`) — already had 4 new operators from v0.2; now with comprehensive tests.

## Relationship to Benchmark v0.2

```
v0.2 used a benchmark local verifier for broad structural coverage.
v0.3 backfills stable v0.2 capabilities into production GeoTask Core
Normalizer and Verifier.
```

中文：

```
v0.2 使用 benchmark 本地验证器扩大结构化覆盖；
v0.3 将 v0.2 中稳定的能力回灌到生产级 GeoTask Core Normalizer 和 Verifier。
```

## New Supported Operators

| # | Operator | Input Types | Output | Since |
|---|----------|-------------|--------|-------|
| 1 | `distance_2d` | point, point | float | v0.1 |
| 2 | `line_intersects_rect` | line, rect | bool | v0.1 |
| 3 | `point_to_line_distance_2d` | point, line | float | **v0.3** |
| 4 | `rect_contains_point` | rect, point | bool | **v0.3** |
| 5 | `time_overlap` | time, time | bool | **v0.3** |
| 6 | `altitude_overlap` | altitude, altitude | bool | **v0.3** |

## New Supported Statuses and Review Reasons

### Statuses (priority order)

| Priority | Status | Meaning |
|----------|--------|---------|
| 1 (highest) | `invalid_operator` | Non-existent operator referenced |
| 2 | `invalid_reference` | Object reference not in geotask_data |
| 3 | `contradicted` | Model output contradicts deterministic result |
| 4 | `need_review` | Missing values, operators, or unclear references |
| 5 | `need_data` | External data required |
| 6 (lowest) | `verified` | All checks pass |

### Review Reasons

| Reason | Trigger |
|--------|---------|
| `operator_reference_missing` | Values extracted, operator not referenced |
| `value_not_found` | No numeric value for expected measurement |
| `object_reference_missing` | Object references unclear |
| `invalid_operator` | Non-existent operator name detected |
| `invalid_reference` | Object name not in geotask_data |
| `unit_mismatch` | km used where meter expected |

## End-to-End Verification Flow

```
LLM Output Text
    ↓
Normalizer (normalize_model_output)
    ├─ Extract distance value
    ├─ Extract intersection boolean  
    ├─ Detect operator references
    ├─ Detect invalid operators (haversine, etc.)
    ├─ Detect invalid references (airport, etc.)
    ├─ Detect unit mismatch (km vs m)
    └─ Build structured measurements
    ↓
Verifier (verify_normalized_result)
    ├─ Run local deterministic ops (runner)
    ├─ Compare extracted values vs computed values
    ├─ Assign status per measurement
    └─ Compute overall status with priority
    ↓
Unified GeoTask Result
    ├─ measurements: [{name, value, unit, status, ...}]
    ├─ conclusion: {summary, overall_status, review_reasons}
    └─ verified_by: [{operation, result, status}]
```

## Examples

```bash
# Run a GeoTask document through local ops
python -m geotask_core.cli run examples/geotask_core_lite.yaml

# Normalize LLM output
python -m geotask_core.cli normalize examples/deepseek_output_sample.txt

# Normalize + verify against GeoTask ground truth
python -m geotask_core.cli normalize examples/deepseek_output_sample.txt \
    --geotask examples/geotask_core_lite.yaml
```

## Evidence Mapping

| Evidence | Version | File |
|----------|---------|------|
| Core ops tests | v0.3 | `tests/test_ops_v0_3.py` |
| Production end-to-end | v0.3 | `tests/test_core_normalizer_verifier_v0_3.py` |
| Evidence integrity | v0.3 | `tests/test_core_v0_3_evidence.py` |
| Evidence package | v0.3 | `patent_evidence/08_core_v0_3/` |
| Full test suite | — | `pytest` (363+ tests) |

## Limitations

- Deterministic tests only — no real LLM inference
- Regex-based extraction — limited generalization
- Tolerance-based numeric comparison (0.05)
- Time format: HH:MM only
- No polygon, 3D, or real map data support

## How v0.3 Closes the v0.2 Local-Verifier Boundary

In Benchmark v0.2, the 4 new operators were verified only through `benchmarks/encoding_v0_2/local_verifier.py` — a benchmark-layer utility, not the production GeoTask Core Normalizer or Verifier. This created an evidence boundary:

- v0.1.1: 2 operators in production Core ✅
- v0.2: 6 operators in benchmark, but only 2 in production Core ⚠️
- v0.3: 6 operators in production Core ✅ (boundary closed)

v0.3 backfills stable v0.2 capabilities into production `src/geotask_core/normalizer.py` and `verifier.py`, making the multi-operator evidence directly traceable to the claimed production system.

> v0.3 将 v0.2 中稳定的多算子能力回灌到 production Core，使多算子证据可直接追溯到所主张的生产系统，关闭了 benchmark local verifier 的证据边界。

## Next Steps

1. **v0.4**: Real LLM API benchmark using 24-case structure from v0.2
2. **v0.4**: Statistical significance analysis
3. **v0.5**: Domain-specific test cases (UAV, site selection, route optimization)

---

*Document: `docs/core_normalizer_verifier_v0_3.md`*
*Version: v0.3 | Date: 2026-06-18*
