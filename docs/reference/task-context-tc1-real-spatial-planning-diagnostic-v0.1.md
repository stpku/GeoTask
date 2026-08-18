# TC1-Real Spatial Planning Diagnostic v0.1

**Status:** NON-SCORING / TRUNCATED diagnostic  
**Date:** 2026-08-18  
**Scenario:** Phoenix public-library service-coverage context preparation

## Why this diagnostic is retained

The first live bounded acquisition produced apparently attractive task-vs-broad
byte reductions. Those numbers are deliberately **not** admitted into the TC1
headline benchmark because the growth geometry and population-table responses
both hit the provider's 2,000-record transfer ceiling.

This is useful negative evidence:

> a smaller bounded response is not evidence of better Task Context when source
> completeness has not been established.

TC1 must not optimize Context Reduction Ratio by silently accepting provider
truncation and thereby increasing Critical Context Miss.

## Frozen scopes used

```text
broad region  [-112.20, 33.30, -111.90, 33.60]
task area     [-112.10, 33.40, -112.00, 33.50]
hotspot       [-112.075, 33.425, -112.050, 33.450]
```

## First live responses

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
bounding boxes. This is treated as another truncation warning, not as a source
semantics conclusion.

The population diagnostic observed multiple variables and years. No variable or
planning year is therefore selected after seeing burden results. A named
`popvar` / `year` pair will be frozen only before the complete R0/R1/RG headline
comparison.

## Method correction

The benchmark acquisition path now uses:

```text
bounded scope
  -> returnIdsOnly
  -> deterministic object-ID chunks
  -> retrieve exact pages
  -> verify retrieved IDs == source ID set
  -> only then construct/score context
```

This correction remains in the benchmark layer. It is not a new GeoTask Core
semantic.

## Gate

The first acquisition remains NON-SCORING until:

1. growth geometry is complete for task and broad scopes;
2. population rows are complete for the selected spatial units;
3. task units are proven to be contained by broad-region units under the same
   recorded source;
4. library and land-use counts are likewise source-complete or independently
   shown not to be truncated;
5. all scored payloads are pinned by exact request/provenance/hash evidence.

Only a later IDs-first fixture may replace this diagnostic as benchmark input.
