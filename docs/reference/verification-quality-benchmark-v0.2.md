# GeoTask Verification Quality Benchmark v0.2

**Status:** P2 Product Track deterministic synthetic perturbation benchmark
**Date:** 2026-08-11
**Installed CLI:** `geotask benchmark quality --suite perturbation`
**Reference wrapper:** `examples/reference_agent/facility_assessment_update/quality_benchmark_v0_2.py`
**Scope:** 34 contract-valid deterministic synthetic perturbation cases over the fictional Reference Agent v0.1 workflow

## 1. Purpose

Verification Quality Benchmark v0.1 keeps a small, stable five-scenario conformance fixture. v0.2 asks a different product question:

> Does the same installed Reference Agent preserve its verification, control, bounded-correction, impact-scope, replay and side-effect boundaries across a larger deterministic synthetic perturbation matrix?

v0.2 is still a **Product Track benchmark**. It adds no new Core Artifact, Schema, Operator or GT capability, and it does not create a second verifier. Every generated case is replayed through the installed Reference Agent bundle and the existing GeoTask Core path.

## 2. Fixed perturbation matrix

The matrix is deliberately deterministic rather than random so that every failure is replayable and every expected result is inspectable.

| Class | Cases | What changes | Expected property |
|---|---:|---|---|
| threshold boundary | 16 | thresholds 10/25/50/100 m × offsets −0.01/0/+0.01/+20 m | exact threshold semantics; below contradicts, equality and above satisfy |
| control gate | 8 | technically safe evidence with human review false or missing | verification may be `satisfied` while report eligibility remains false |
| freshness | 4 | valid evidence becomes stale before evaluation | result remains `unverifiable`, never inferred safe/false |
| freshness boundary | 2 | `valid_until == evaluation_time` | equality remains valid under the declared `< evaluation_time` stale rule |
| conflict | 2 | two fresh sources disagree | result remains `conflicted`; no implicit precedence or voting |
| consistent multi-source | 2 | two fresh sources agree | agreement does not create a false conflict |
| **Total** | **34** | | |

All generated Observation records remain valid under the existing Observation contract. The benchmark does not weaken the contract merely to manufacture malformed inputs.

## 3. Metrics

v0.2 reports:

```text
outcome_match_rate_pct
error_detection_rate_pct
missed_error_rate_pct
false_blocking_rate_pct
control_gate_block_rate_pct
threshold_boundary_accuracy_pct
correction_success_rate_pct
impact_scope_precision_pct
impact_scope_recall_pct
deterministic_replay_pass_rate_pct
side_effect_boundary_pass_rate_pct
```

The shipped deterministic matrix has the exact acceptance values:

```text
outcome_match_rate_pct = 100.0
error_detection_rate_pct = 100.0
missed_error_rate_pct = 0.0
false_blocking_rate_pct = 0.0
control_gate_block_rate_pct = 100.0
threshold_boundary_accuracy_pct = 100.0
correction_success_rate_pct = 100.0
impact_scope_precision_pct = 100.0
impact_scope_recall_pct = 100.0
deterministic_replay_pass_rate_pct = 100.0
side_effect_boundary_pass_rate_pct = 100.0
```

These are deterministic fixture acceptance values, not statistical confidence estimates.

## 4. Run

Keep the stable five-scenario v0.1 gate:

```bash
geotask benchmark quality
geotask benchmark quality --suite fixed
```

Run the v0.2 perturbation matrix:

```bash
geotask benchmark quality --suite perturbation
```

Machine-readable compact output:

```bash
geotask benchmark quality --suite perturbation --compact
```

The Reference Agent teaching workspace exposes the same installed implementation:

```bash
python3 examples/reference_agent/facility_assessment_update/quality_benchmark_v0_2.py --format json
```

## 5. What the 34 cases establish

For this bounded fictional workflow, the matrix checks that:

- threshold equality and near-threshold changes follow the declared comparison exactly;
- stale evidence remains `unverifiable` rather than being converted to a convenient Boolean;
- fresh disagreement remains `conflicted` without undeclared precedence;
- consistent fresh evidence is not falsely blocked as conflict;
- technical verification can be `satisfied` while missing/negative human review still blocks report eligibility;
- accepted evidence materializes rev2/rev3 deterministically and only declared assessment values change;
- the declared affected and reused scope remains exact;
- every replay preserves `eligible != authorized != executed`;
- no case claims a production write, report publication, authorization or real-world execution.

## 6. Critical interpretation boundary

The v0.2 report explicitly records:

```text
fictional_data_only = true
generated_synthetic_perturbations = true
network_used = false
model_called = false
production_system_accessed = false
production_write_performed = false
automatic_dependency_discovery = false
automatic_global_recompute = false
real_world_accuracy_claimed = false
cross_domain_generalization_claimed = false
```

Therefore a `100%` result in v0.2 must **not** be described as:

- 100% real-world accuracy;
- proof of real-world safety or operational correctness;
- proof that an external Provider or source is truthful;
- proof of automatic dependency discovery in arbitrary systems;
- proof of cross-domain generalization;
- proof that a production write or action was authorized or executed;
- second-system reuse evidence;
- Core Promotion approval.

In particular, this benchmark is **not Core Promotion evidence**. Promotion still requires independent second-system/industry reuse and an explicit Promotion Gate review.

## 7. Relationship to v0.1 and future evidence

v0.1 remains the small stable acceptance fixture and backward-compatible default CLI suite. v0.2 broadens deterministic synthetic coverage without changing the public meaning of v0.1.

Future real shadow-mode studies may measure coverage, review usefulness, false blocking or correction quality against authoritative external state. Those measurements must be reported separately from v0.1/v0.2 and must not silently convert synthetic conformance values into real-world performance claims.
