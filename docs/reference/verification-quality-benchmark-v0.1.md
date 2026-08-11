# GeoTask Verification Quality Benchmark v0.1

**Status:** P2 Product Track benchmark  
**Date:** 2026-08-07  
**Executable:** `geotask benchmark quality` (installed Core); source/teaching wrapper: `examples/reference_agent/facility_assessment_update/quality_benchmark.py`
**Scope:** fixed fictional Reference Agent v0.1 scenarios only

## 1. Purpose

`geotask benchmark core` answers whether the public Core operators and contracts remain conformant, deterministic and locally performant. The Verification Quality Benchmark answers a different product question:

> When the current Reference Agent is given a declared good state or a known evidence/state defect, does the end-to-end verification workflow detect the defect, avoid unnecessary blocking, correct only declared state, preserve unrelated results and keep production side effects outside GeoTask?

This benchmark is therefore a **Product Track quality gate**, not a replacement for the Core Benchmark and not a new GT capability number.

## 2. Fixed scenario set

The benchmark reuses the public Reference Agent scenarios without maintaining a second verifier:

| Class | Scenario | Expected behavior |
|---|---|---|
| clean | `success` | satisfied; report refresh eligible; no production action |
| known error | `missing_evidence` | unverifiable; blocked; Evidence Request |
| known error | `conflicting_evidence` | conflicted; blocked; no implicit precedence |
| known error | `stale_evidence` | unverifiable; blocked |
| known error | `contradicted` | contradicted; bounded successor permitted; report blocked |

The two scenarios with accepted deterministic observations (`success` and `contradicted`) are also used to evaluate bounded correction and impact scope.

## 3. Metrics

### Error detection rate

Known defect cases that end in one of:

- `unverifiable`;
- `conflicted`;
- `contradicted`;

and keep `report_update_eligible=false`.

```text
error_detection_rate = detected_known_errors / known_error_cases
```

### Missed error rate

```text
missed_error_rate = undetected_known_errors / known_error_cases
```

### False blocking rate

The clean success case is falsely blocked if it does not reach `satisfied` with `report_update_eligible=true`.

```text
false_blocking_rate = falsely_blocked_clean_cases / clean_cases
```

### Correction success rate

For accepted deterministic evidence, correction succeeds only when all of the following hold:

- baseline remains immutable;
- successor revision is materialized;
- successor distance equals the deterministic `distance_2d` result;
- successor clearance state equals the declared threshold comparison;
- no production write/report publication/action execution is claimed.

### Impact scope precision and recall

The Reference Agent v0.1 has a deliberately declared golden impact scope:

```text
/objects/mapped-obstacle-01/attributes/position_xy/value
obstacle_distance_m
assessment-FAC-001.obstacle_clearance_pass
report-v4.safety.obstacle_clearance
review:FAC-001:obstacle-clearance
```

Unrelated reusable results are also fixed:

```text
assessment-FAC-001.accessibility_score
assessment-FAC-001.service_capability_score
report-v4.operator_summary
```

Precision and recall compare the **declared bounded impact output** with this fixed golden scope. They do not measure automatic dependency discovery because GeoTask does not claim that capability here.

### Side-effect boundary pass rate

Every scenario must preserve:

```text
production_write_performed = false
production_report_refreshed = false
action_authorized = false
action_executed = false
```

## 4. Run

The installed Core exposes the benchmark as a first-class Product-Track CLI:

```bash
geotask benchmark quality --format text
```

Machine-readable report:

```bash
geotask benchmark quality --format json
```

Write a report file:

```bash
geotask benchmark quality \
  --format json \
  --output /tmp/geotask-verification-quality.json
```

The Reference Agent teaching bundle retains a standalone wrapper for source-checkout
and materialized-workspace use:

```bash
python3 examples/reference_agent/facility_assessment_update/quality_benchmark.py
```

Both entrypoints execute the same installed `geotask_core` benchmark implementation;
the example no longer maintains a second metric implementation. The benchmark
returns a non-zero exit status if its fixed acceptance metrics fail.

## 5. v0.1 acceptance values

For the shipped five-scenario fixture, the release gate is intentionally exact:

```text
error_detection_rate_pct = 100.0
missed_error_rate_pct = 0.0
false_blocking_rate_pct = 0.0
correction_success_rate_pct = 100.0
impact_scope_precision_pct = 100.0
impact_scope_recall_pct = 100.0
side_effect_boundary_pass_rate_pct = 100.0
```

These values are expected because this is a deterministic conformance-style product benchmark over fixed synthetic cases, not a statistical estimate of real-world model accuracy.

## 6. Critical interpretation boundary

A `100%` value in this benchmark **must not** be described as:

- 100% error detection on real low-altitude data;
- 100% safety assurance;
- 100% impact-discovery accuracy in arbitrary systems;
- proof of cross-domain generalization;
- proof that an LLM, Provider or external data source is truthful;
- proof that Lowa-GT production decisions are correct.

The report explicitly records:

```text
fictional_data_only = true
network_used = false
model_called = false
production_system_accessed = false
production_write_performed = false
automatic_dependency_discovery = false
automatic_global_recompute = false
cross_domain_generalization_claimed = false
```

## 7. Relationship to future benchmarks

This v0.1 closes the first Product Track quality gap: the public Reference Agent now has reproducible error-detection, false-blocking, correction and bounded-impact measures.

Later benchmarks may add larger synthetic perturbation sets and real shadow-mode Lowa-GT samples, but those results must be reported separately. A Lowa-GT 50-site shadow study, for example, measures industry-state coverage and human-review usefulness; it must not silently replace this deterministic fixture or be generalized to other domains.
