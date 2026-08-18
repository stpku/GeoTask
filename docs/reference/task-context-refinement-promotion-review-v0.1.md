# Task Context Sufficiency-Guided Refinement Promotion Review v0.1

**Status:** Method Promotion Review / Core Promotion HOLD  
**Date:** 2026-08-18  
**Evidence scope:** TC1 spatial planning + TC2 spatial applicability + real USGS 3DEP Resolution Stress + real NOAA/NWS Temporal Refinement  
**Purpose:** decide what, if anything, has earned promotion from benchmark-specific implementation into GeoTask's reusable Task Context method.

---

## 0. Verdict

The evidence supports promotion of the following **method-level principle**:

> **Sufficiency-Guided Refinement** — evaluate the current task context first; if it is sufficient, stop. If it is insufficient because the current representation cannot determine the task-relevant outcome, refine only the unresolved part and reassess.

The evidence does **not** yet justify promotion of:

- a generic automatic refinement algorithm into Core;
- a new mandatory `RefinementRequest` public contract;
- terrain min/max envelopes as a Core representation;
- weather temporal envelopes as a Core representation;
- a universal resolution optimizer;
- provider-side multiresolution derivation responsibility inside GeoTask.

Therefore:

```text
Method semantics                  PASS
Cross-dimension evidence          PASS with coverage caveat
New Core algorithm                HOLD
New Core schema / public object   HOLD
Benchmark/provider strategies     REMAIN LOCAL
Strategic wording amendment       RECOMMENDED FOR NEXT REVISION
```

---

# 1. Problem

## 1.1 Root problem

The earlier linear framing:

```text
Task
 -> Relevance
 -> Applicability
 -> Resolution
 -> Sufficiency
 -> Task Context
```

implicitly treats resolution as something that must be decided before sufficiency is known.

The real experiments show the opposite pattern:

> Most task cases can stop at a coarse representation. Only a minority become insufficient because the current representation leaves multiple task-relevant outcomes possible.

A mandatory resolution stage therefore creates two failure modes:

1. **Over-refinement** — always acquire or carry finer context even when the coarse representation already proves the task result;
2. **Unsafe coarse stopping** — accept a coarse representation even though it still permits different fine-scale task outcomes.

The root problem is not "what resolution should every task use?"

It is:

> **Given the current task and current context representation, is the context already sufficient to support the next task-level conclusion; if not, what is the smallest unresolved dimension that must be refined?**

---

# 2. Method

## 2.1 Method name

> **Sufficiency-Guided Refinement (SGR)**

## 2.2 Core mechanism

```text
Task
 -> Requirements
 -> Candidate Context
 -> Relevance
 -> Applicability
 -> Sufficiency
      |
      +-- sufficient --> Task Context
      |
      +-- insufficient --> Context Gap
                              |
                              +-- refine unresolved scope
                              +-- refine spatial resolution
                              +-- refine temporal resolution
                              +-- change representation
                              +-- acquire source/evidence
                              +-- refresh stale context
                                      |
                                      +--> reassess Sufficiency
```

Resolution is therefore a **refinement control variable**, not a mandatory peer stage after or before Sufficiency.

## 2.3 Invariant

Let `U_r(T)` be the set of fine-grained physical states still compatible with the current representation `r` for task `T`, and let `D(x)` be the task-relevant next conclusion/action under fine state `x`.

A coarse stop is justified only when:

```text
| { D(x) : x in U_r(T) } | = 1
```

If multiple task-relevant outcomes remain possible, the current representation is insufficient and refinement is permitted.

This is a method invariant, not a requirement that Core explicitly enumerate `U_r(T)`.

## 2.4 Selective refinement

Refinement must be selective:

- already-proven portions remain summarized;
- only ambiguous / insufficient portions are expanded;
- refinement stops as soon as the task-level result is provable;
- "finest available" is not an objective by itself.

## 2.5 Applicability boundary

SGR applies when:

- the task has explicit sufficiency conditions or conservative proof rules;
- a coarse representation has a declared relation to finer states;
- refinement can reduce task-relevant uncertainty;
- the final domain conclusion remains outside GeoTask ownership.

SGR does not by itself solve:

- truth resolution;
- domain-specific safety rules;
- source authority;
- arbitrary semantic ambiguity without a declared refinement strategy;
- provider-side raster pyramid / data-cube production.

---

# 3. Measure

Metrics are frozen by responsibility: the primary metric tests whether coarse stopping is safe; counter-metrics prevent "always refine" from winning by construction.

## 3.1 Primary metric — Unsafe Stop Rate

```text
Unsafe Stop Rate =
  coarse/final stops that disagree with the pinned fine reference
  --------------------------------------------------------------
  all stopped cases
```

Target in the controlled benchmark: `0`.

## 3.2 Counter-metric — Unnecessary Refinement Rate

Under the declared representation and proof rule:

```text
Unnecessary Refinement Rate =
  cases refined even though current representation already proved the result
  --------------------------------------------------------------------------
  all refinement cases
```

Important boundary:

> `0` under one declared representation does **not** prove global information-theoretic optimality. A different task-aware sufficient statistic may sometimes stop earlier.

## 3.3 Efficiency metric — Context Payload Reduction

Compare task-carried context against an always-finest baseline.

This metric excludes provider/shared derivation cost unless that cost is explicitly added to the same ledger.

## 3.4 Counter-metric — Per-case Refinement Overhead

Average savings can hide expensive boundary cases.

Record:

- number of cases where adaptive payload exceeds always-finest payload;
- worst-case adaptive / always-finest payload ratio.

## 3.5 Coverage metric — Outcome Coverage

A real proof should record which task-result directions actually occurred.

Synthetic controls may exercise missing branches but do not substitute for real outcome coverage.

---

# 4. Evidence A — Spatial Resolution Stress

Pinned source:

```text
USGS 3DEP bare-earth elevation
Phoenix South Mountain
512 m x 512 m
1 m reference
```

Frozen before reading terrain values:

```text
resolution ladder   32 -> 16 -> 8 -> 4 -> 1 m
corridors           6
thresholds          8
cases               48
representation      exact block min/max envelope
```

Observed result:

```text
total cases                    48
stop at 32 m                   45
refinement cases                3
final at 16 m                   2
final at 8 m                    1
unsafe stops                    0
unnecessary refinements         0
```

Real refinement resolved in both task directions:

```text
32 -> 16 -> STOP_BLOCKED
32 -> 16 -> STOP_BLOCKED
32 -> 16 -> 8 -> STOP_CLEAR
```

Task-context payload ledger:

```text
adaptive min/max payload      12,992 bytes
always-1m float payload      344,064 bytes
aggregate reduction           96.22396%
```

Counter-ledger:

```text
pyramid derivation reads      1,310,720 fine-cell reads
```

The derivation cost is explicitly excluded from the context-reduction headline.

Engineering implication:

> This efficiency claim is meaningful only when multiresolution representations are provider-native, cached, indexed, or amortized across tasks.

---

# 5. Evidence B — Temporal Refinement Stress

Pinned source:

```text
NOAA/NWS hourly point forecast
South Mountain point: 33.35, -112.06
first 24 contiguous future hourly periods
```

Frozen before reading forecast values:

```text
task windows         2 x 12 h
temporal ladder      12 -> 6 -> 3 -> 1 h
wind thresholds      10 / 20 / 30 / 40 km/h
PoP thresholds       10 / 30 / 50 / 70 %
cases                32
representation       wind/PoP min/max envelopes
```

Observed result:

```text
total cases                    32
stop at 12 h                   24
refinement cases                8
final at 6 h                    4
final at 3 h                    4
unsafe stops                    0
unnecessary refinements         0
aggregate payload reduction    66.66667%
```

Counter-metric:

```text
adaptive payload > hourly baseline cases    4 / 32
worst-case payload ratio                     1.16667x
```

The four 3-hour-resolution cases carry cumulative coarse envelopes totaling 28 floats versus 24 floats for direct hourly context. The method therefore does not claim per-case cost dominance.

Real outcome-coverage caveat:

```text
STOP_AVAILABLE     observed
STOP_UNAVAILABLE   not observed in the frozen real fixture
```

Synthetic tests exercise unavailable/refinement paths, but they do not count as real outcome coverage.

---

# 6. Cross-Dimension Generalization

The terrain and weather experiments use different:

- physical variables;
- source systems;
- spatial vs temporal dimension;
- aggregation strategies;
- task semantics;
- cost shapes.

Yet both exhibit the same higher-order behavior:

```text
coarse representation
 -> task sufficiency proof
 -> most cases stop
 -> minority remain ambiguous
 -> refine only ambiguity
 -> stop when task result becomes provable
```

This is enough to treat **Sufficiency-Guided Refinement** as a reusable GeoTask method rather than a terrain-specific trick.

It is not enough to claim that one generic envelope algorithm should enter Core.

---

# 7. Tool / Carrier Decision

## 7.1 Current Core already contains the minimum trigger

`TaskContext` currently exposes:

```text
gap_requirement_ids
refinement_requirement_ids
```

The current baseline marks a requirement for refinement when a candidate is applicable but its declared spatial/temporal resolution is insufficient.

Therefore a new public object is not required merely to encode the method discovered by the benchmark.

## 7.2 Keep replaceable

The following remain replaceable strategies outside Core:

- rectangle / corridor envelope construction;
- DEM min/max pyramid derivation;
- temporal min/max envelope construction;
- provider query mechanics;
- task-specific thresholds;
- refinement search policy beyond the deterministic reference benchmark.

## 7.3 When a new contract becomes justified

A structured `ContextGap` / `RefinementRequest` should be reconsidered only when a real external consumer must execute refinement across a component boundary, for example:

```text
GeoTask assessment
 -> Harness / Agent receives executable gap
 -> Provider/tool acquires more context
 -> GeoTask reassesses
```

At that point the contract has a real consumer and measurable interoperability value.

---

# 8. Promotion Gates

## Method Generalization Gate

**PASS.**

Reason: same invariant repeated in spatial and temporal physical-world tasks with real pinned data.

## Safety Gate

**PASS for current controlled evidence.**

```text
spatial unsafe stops = 0 / 48
temporal unsafe stops = 0 / 32
```

This is benchmark evidence, not a universal safety guarantee.

## Counter-metric Gate

**PASS with explicit tradeoff.**

No structurally unnecessary refinement occurred under either declared representation, but temporal evidence contains 4 cases with higher adaptive payload than direct hourly context.

## Real Outcome Coverage Gate

**PARTIAL.**

Spatial evidence includes CLEAR and BLOCKED. Temporal real evidence includes only AVAILABLE; UNAVAILABLE remains unobserved.

## Core Algorithm Promotion Gate

**HOLD.**

No domain-neutral automatic refinement algorithm has been demonstrated.

## Core Schema Promotion Gate

**HOLD.**

Existing `gap_requirement_ids` / `refinement_requirement_ids` are sufficient for the current implementation stage.

---

# 9. Architecture Implication

The evidence recommends replacing the conceptual linear chain:

```text
Relevance -> Applicability -> Resolution -> Sufficiency
```

with:

```text
Relevance
 -> Applicability
 -> Sufficiency
      enough -> Task Context
      gap    -> selective Refinement
                   scope
                   spatial resolution
                   temporal resolution
                   representation
                   source/evidence
                   freshness
                -> reassess Sufficiency
```

This should be treated as an evidence-driven amendment candidate for the next strategic architecture revision. It should not silently rewrite an already frozen strategic specification without an explicit version change.

---

# 10. Feedback / Next Evidence

Do **not** create a third benchmark merely to increase scenario count.

The next evidence should come from one of two real needs:

1. **Negative temporal outcome coverage** — an independently frozen real task/fixture that naturally contains an UNAVAILABLE path without post-hoc threshold tuning; or
2. **External refinement consumer** — Harness / Agent / Lowa integration that must receive a structured context gap and invoke a provider to close it.

The second path has higher engineering value because it would test whether the method needs a new public contract rather than only another local benchmark.

---

# 11. Final Decision

> **Promote Sufficiency-Guided Refinement as a GeoTask method. Do not promote benchmark-specific refinement algorithms or new Core schema yet.**

The intellectual asset is the invariant and the measurable stop/refine discipline.

The current tools are evidence carriers, not the method itself.
