# GeoTask Real Resolution Stress Test Plan v0.1

**Status:** experiment specification; no Resolution Core promotion claim  
**Date:** 2026-08-18  
**Purpose:** distinguish task-sufficient representation from unnecessary finest-resolution retrieval

## 1. Why this experiment exists

TC1 proved that Task Context can reduce **scope/extent** burden. It did not prove
a generic rule for **resolution**.

This experiment tests a narrower proposition:

> Given one pinned fine physical-world source, can a task stop at a coarser
> representation when the coarse representation provably preserves the next
> task action, and refine only when the current resolution leaves multiple task
> actions possible?

The experiment must not win by always using the finest source.

## 2. Source discipline

Preferred source family:

```text
USGS 3DEP 1-meter bare-earth DEM
```

The fine reference is acquired once and pinned by source/product metadata and
content hash. Coarser representations are generated **locally from the same fine
source** at candidate scales such as 5 m / 10 m / 30 m.

This prevents source/model differences from being misreported as resolution
effects.

The benchmark is about terrain context preparation. The DEM is not interpreted
as flight authorization or a complete obstacle model.

## 3. Discovery phase is non-scoring

1-meter 3DEP coverage is not universal. A separate diagnostic acquisition may
query The National Map product API for candidate areas.

This phase may choose a source-covered rugged area, but it must not choose the
final corridor, threshold, aggregation rule, or resolution ladder based on a
favorable benchmark score.

Discovery output may contain only:

- candidate bbox;
- matching 1-meter product metadata;
- source/download identity;
- coverage diagnostics;
- no resolution headline metric.

## 4. Frozen task after source coverage is known

The scored task will be a fictional terrain-context screening task, not a real
flight decision.

Before scoring, freeze:

```text
physical source tile / hash
analysis CRS
corridor geometry
corridor support rule
reference fine resolution
candidate coarse resolutions
next-action states
threshold(s)
aggregation rule(s)
uncertainty / conservative-bound rule
cost measures
```

Allowed next-action states in v0.1:

```text
STOP_COARSE     current context already decision-preserving
REFINE          current context permits more than one next action
RESOLVED_FINE   finer context collapses ambiguity
```

The benchmark must not change these after reading the fine-resolution outcome.

## 5. Mandatory control A — decision-preserving coarse context

Define one frozen statistic whose aggregation is intentionally sufficient for
the task, for example a conservative terrain extremum over exactly the same
support.

Expected behavior:

```text
coarse representation
  -> conservative bound lies on one side of frozen threshold
  -> every admissible finer state has same next action
  -> STOP_COARSE
```

A policy that automatically selects 1-meter data fails this control because it
cannot distinguish useful precision from unnecessary precision.

## 6. Mandatory control B — genuinely resolution-sensitive context

Define a second frozen task in which the coarse representation mixes spatial
structure relevant to the next action (for example, conservative cells that
cover both the task corridor and nearby high terrain), so the coarse context
cannot prove one action.

Expected behavior:

```text
coarse uncertainty / conservative envelope crosses task boundary
  -> REFINE
finer representation resolves the relevant spatial structure
  -> RESOLVED_FINE
```

The stress case is valid only when the ambiguity follows from the predeclared
representation contract. Deliberately choosing a lossy mean statistic after
seeing a narrow terrain peak is invalid evidence.

## 7. Resolution sufficiency contract

For task `T` and current resolution `r`, let `U_r(T)` be the set of admissible
fine-scale states consistent with the current context and its declared
aggregation/error contract.

```text
possible_actions(r) = { D_T(x) : x in U_r(T) }
```

Decision rule:

```text
len(possible_actions(r)) == 1  -> STOP_COARSE
len(possible_actions(r)) > 1   -> REFINE
```

For a scalar threshold this may be implemented with a frozen interval/bound:

```text
[lower_r, upper_r] entirely below threshold -> STOP_COARSE
[lower_r, upper_r] entirely above threshold -> STOP_COARSE
interval intersects threshold               -> REFINE
```

The bound must be constructed without observing the fine answer.

## 8. Cost model

Do not collapse resolution cost into one scalar prematurely. Record at least:

- source bytes acquired once;
- derived cell count per resolution;
- serialized context bytes;
- processing time;
- number of refinement stages evaluated.

The 1-meter source acquisition itself is a shared reference cost when all coarse
representations are locally derived from it; the headline optimization concerns
how much context is carried/processed for the task, not a false claim that local
resampling reduced upstream acquisition bytes.

## 9. Metrics

### Unsafe Resolution Stop Rate (URSR)

```text
coarse STOP cases whose fine reference changes the frozen next action
/ all resolution-sensitive cases
```

### Unnecessary Refinement Rate (URR)

```text
cases refined even though current context already proves one next action
/ all decision-preserving coarse cases
```

### Resolution Burden Reduction

Compare carried cells/bytes/processing against an always-finest baseline, but
only among policies with the same frozen task outcome guarantees.

### Decision-Preservation Margin

Record the current conservative bound's distance from the frozen task boundary.
This is diagnostic evidence for stop/refine behavior, not a universal threshold.

## 10. Hard anti-cheating guards

The experiment fails closed if any of these occur:

- fine and coarse contexts come from different source products without an
  explicit non-resolution comparison goal;
- the task threshold is selected after observing fine terrain;
- the corridor is moved after observing a resolution flip;
- the aggregation rule is changed after seeing benchmark results;
- missing DEM cells are coerced to zero;
- a smaller payload is reported as success while next-action preservation fails;
- an always-finest policy is accepted without measuring unnecessary refinement.

## 11. Promotion gate

Automatic/adaptive Resolution remains **HOLD** until this benchmark produces
both:

```text
one real STOP_COARSE control
one real REFINE -> RESOLVED_FINE stress case
```

under one task-relative rule, with no low-altitude-specific semantics required in
Core.

Only then should GeoTask consider a new Resolution method or primitive. Until
then the existing `max_spatial_resolution` field remains a caller-declared
requirement check, not an automatic resolution-selection algorithm.
