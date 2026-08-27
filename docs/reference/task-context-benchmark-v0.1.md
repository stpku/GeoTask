# GeoTask Task Context Benchmark v0.1

**Status:** benchmark design candidate  
**Date:** 2026-08-18  
**Purpose:** evaluate whether task-adaptive spatiotemporal context reduces preparation cost without hiding conditions that materially affect a physical-world task.

## 1. Benchmark question

The benchmark does not ask whether GeoTask builds a complete world model.

It asks:

> **Can GeoTask construct a smaller and cheaper task context while preserving the physical-world information that matters to the task outcome?**

The benchmark must make it possible to falsify the Task Context Engine hypothesis.

## 2. Baselines

At least two baselines should be compared where data allows:

### B0 — Full-context baseline

Load all candidate context made available to the benchmark case, using the strongest declared resolution.

This baseline is intentionally expensive and is used as a reference, not as a recommended production strategy.

### B1 — Manual/task-template baseline

Use a fixed human-authored checklist or domain template that selects context without task-adaptive refinement.

This approximates many current operational workflows.

### G — GeoTask context

Use the TaskFrame / ContextRequirement / ContextCandidate process and any declared GeoTask selection/refinement policy being evaluated.

The v0.1 Core slice supports contract assessment only. A later benchmark implementation may add a selection policy, but the policy must be named and versioned.

## 3. Required benchmark fixture

Each case should contain:

- one bounded physical-world task;
- candidate context items with source/scope/resolution/cost metadata;
- a reference set of **critical context items or conditions** established independently of the system under test;
- a reference downstream task result or result range when available;
- acquisition/computation cost estimates;
- optional perturbations that change one local condition, scale, or source.

Synthetic cases may be used for deterministic unit tests, but their results must not be presented as real-world decision accuracy.

## 4. Primary metrics

### 4.1 Critical Context Miss Rate (CCMR)

Fraction of reference-critical context conditions not represented adequately in the selected context.

```text
CCMR = missed critical context conditions / reference critical conditions
```

This is the main fail-safety metric. A context reduction strategy that lowers cost by omitting critical conditions is not successful.

### 4.2 Context Preparation Cost (CPC)

Declared cost required to obtain and prepare the selected task context.

Cost may contain separately reported components:

- human preparation time;
- provider/API/data cost;
- latency;
- compute cost;
- storage/transfer volume.

Do not collapse heterogeneous cost components into one number unless the conversion method is declared.

### 4.3 Context Reduction Ratio (CRR)

How much candidate context is omitted relative to the full-context baseline.

Possible units include item count, bytes, tokens, spatial cells, temporal samples, or compute volume. The unit must be explicit.

```text
CRR = 1 - selected context size / full context size
```

CRR is never interpreted alone; it must be paired with CCMR and outcome metrics.

## 5. Resolution metric

### Resolution Efficiency (RE)

Measures cost saved by avoiding unnecessary highest-resolution processing.

A benchmark case should identify where coarse context is sufficient and where local refinement is actually required.

Report:

- area/time/object fraction processed at each resolution;
- cost versus full-resolution baseline;
- whether any critical task outcome changed because of under-resolution.

The benchmark should reward **coarsest sufficient resolution**, not maximum resolution.

## 6. Outcome metric

### Task Outcome Regret (TOR)

When a trusted downstream reference result exists, compare the result produced with GeoTask context against the stronger reference context.

The exact regret function is domain-specific and must be declared before evaluation.

Examples:

- route cost increase;
- candidate ranking change;
- missed feasible option;
- false feasible option;
- planning-score degradation;
- additional manual rework.

A generic benchmark must not invent a universal decision-regret formula across domains.

## 7. Counter-metrics

Every cost-reduction metric needs a counter-metric.

| Optimization pressure | Required counter-metric |
|---|---|
| reduce context item count | Critical Context Miss Rate |
| reduce spatial resolution | under-resolution outcome error |
| reduce provider/API calls | missing critical source/condition rate |
| reduce latency | Task Outcome Regret / rework |
| maximize automatic selection | human override / correction rate |

## 8. Minimum success pattern

A Task Context Engine experiment is promising only when it shows the following pattern against an appropriate baseline:

```text
Context Preparation Cost ↓
Context size / high-resolution processing ↓
Critical Context Miss Rate does not materially increase
Task Outcome Regret remains within declared tolerance
```

No single fixed numerical threshold is defined in v0.1 because acceptable error/cost trade-offs are domain-specific.

## 9. Reference scenario perturbations

For the fictional low-altitude mission scenario, deterministic benchmark perturbations can include:

1. **irrelevant POI expansion** — add many non-critical POIs; selected critical context should not grow;
2. **coarse obstacle grid** — 100 m obstacle context where 10 m is explicitly required; refinement should be requested;
3. **wrong corridor weather** — fresh data for another corridor; applicability must fail;
4. **wrong time-window restriction** — valid rule outside the task window; applicability must fail when the temporal binding is explicit;
5. **expensive premium source** — context can be informationally sufficient yet over budget;
6. **critical source missing** — context must remain insufficient;
7. **non-critical source missing** — context may remain usable with a declared gap.

These perturbations test contracts, not flight-safety accuracy.

## 10. Research hypothesis

The longer-term GeoTask hypothesis can be stated as:

> For physical-world Agent tasks with heterogeneous multi-scale information, task-adaptive spatiotemporal context selection can reduce information-preparation cost while keeping critical-context omission and task-outcome regret within explicit bounds.

A future benchmark should reject this hypothesis if GeoTask cannot outperform simpler full-context or fixed-template baselines on the cost/error trade-off.

## 11. Reporting discipline

Every reported result must identify:

- task/domain;
- dataset/source fixture;
- candidate-context universe;
- reference critical-context definition;
- selection/refinement policy version;
- cost units;
- downstream result method;
- baseline;
- limitations.

Do not report a synthetic deterministic benchmark as evidence that GeoTask makes real-world decisions correct or safe.
