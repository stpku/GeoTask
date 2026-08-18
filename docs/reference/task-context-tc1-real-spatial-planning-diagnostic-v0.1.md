# TC1-Real Spatial Planning Diagnostic v0.1

**Status:** NON-SCORING / TRUNCATED + WRONG-REPRESENTATION diagnostic  
**Date:** 2026-08-18  
**Scenario:** Phoenix public-library service-coverage context preparation

## Why this diagnostic is retained

The first live bounded acquisition produced apparently attractive task-vs-broad
byte reductions. Those numbers are deliberately **not** admitted into the TC1
headline benchmark because two independent problems were discovered before
scoring:

1. ordinary feature/table queries hit the provider's 2,000-record transfer
   ceiling;
2. the first growth geometry source was layer 2 (`FinalLUAUs_PopEmp`), a joined
   Pop/Emp representation that repeats base planning-unit geometry across
   related records rather than the minimal base-unit representation required by
   the task.

These are useful negative results:

> a smaller bounded response is not evidence of better Task Context when source
> completeness has not been established;

and:

> context cost can be dominated by choosing the wrong physical-world
> representation before spatial scope reduction is even considered.

TC1 must not optimize Context Reduction Ratio by silently accepting provider
truncation or by comparing against an unnecessarily duplicated representation.
Either behavior could make the benchmark look better while increasing Critical
Context Miss or artificial context burden.

## Frozen scopes used

```text
broad region  [-112.20, 33.30, -111.90, 33.60]
task area     [-112.10, 33.40, -112.00, 33.50]
hotspot       [-112.075, 33.425, -112.050, 33.450]
```

## First bounded responses — NON-SCORING

```text
growth-broad        2,000 features   4,573,559 bytes
growth-task         2,000 features   2,485,291 bytes
population-broad    2,000 rows         251,974 bytes
population-task     2,000 rows         251,921 bytes
libraries-broad        12 features        6,169 bytes
libraries-task          2 features        1,053 bytes
land-use-broad          45 features      384,190 bytes
land-use-task           17 features      145,047 bytes
land-use-hotspot         3 features       24,540 bytes
```

The first growth responses also produced task and broad `newluau` sets that did
not satisfy the containment relationship expected from the frozen nested
bounding boxes. This is treated as a truncation warning, not as a source
semantics conclusion.

The population diagnostic observed multiple variables and years. No variable or
planning year is selected after seeing burden results. A named `popvar` / `year`
pair will be frozen only before the complete R0/R1/RG headline comparison.

## Second diagnostic — completeness exposed the wrong representation

The benchmark then switched to an IDs-first acquisition path:

```text
bounded scope
  -> returnIdsOnly
  -> deterministic object-ID chunks
  -> retrieve exact pages
  -> verify retrieved IDs == source ID set
```

Applied to layer 2 (`FinalLUAUs_PopEmp`), the complete broad-region measurement
returned:

```text
complete feature count     118,190
unique newluau count             471
page count                       119
network bytes             172,127,458
complete                        true
```

This is retained as **negative provider-representation evidence**, not as an R0
baseline. The public Growth Projections service exposes base planning-unit layer
4 (`FinalLUAUs`) and relates it to population table 13 (`New_Pop_Emp_Data`). The
formal TC1 planning experiment therefore uses:

```text
base geometry       layer 4  FinalLUAUs
population context  table 13 New_Pop_Emp_Data
relationship key    newluau
```

Layer 2 is excluded from scoring. The benchmark must not manufacture a large
"context reduction" by comparing task context against duplicated joined
geometry that the task never needed in the first place.

## Method corrections

Two corrections are now frozen in the benchmark layer:

### A. Completeness before reduction

```text
scope
  -> source object-ID set
  -> complete page retrieval
  -> retrieved IDs == source IDs
  -> only then construct/score context
```

### B. Task-appropriate representation before scope refinement

```text
Task requirement
  -> choose the least-duplicative source representation that preserves the
     required semantics
  -> prove source completeness
  -> then compare broad/task/hotspot scope burden
```

Neither correction is automatically promoted into GeoTask Core. They are TC1
method evidence and possible inputs to a later Promotion Gate.

## Source redistribution boundary

The Growth Projections service carries upstream source-use conditions. Its raw
geometry/population records are therefore not vendored into the long-lived
public benchmark fixture by default. Long-lived evidence should retain compact
request/provenance/measurement artifacts, source/set hashes, completeness
proofs, and aggregate counts sufficient to audit the comparison without turning
GeoTask into a copy of the provider's dataset.

## Gate

The planning scenario remains NON-SCORING until:

1. base layer 4 geometry is complete for task and broad scopes;
2. table 13 population rows are complete for the selected planning units;
3. task planning units are proven to be contained by broad-region units under
   the same recorded source;
4. library and land-use counts are source-complete;
5. a specific population variable/year is frozen before headline comparison;
6. R0/R1/RG all cover the same P1/P2/P3 critical requirements;
7. all scored measurements are pinned by explicit request/provenance/hash
   evidence.

Only a later layer-4 IDs-first measurement may become benchmark input.
