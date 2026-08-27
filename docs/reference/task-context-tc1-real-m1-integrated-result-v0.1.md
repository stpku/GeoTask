# GeoTask TC1-Real M1 Integrated Result v0.1

**Status:** first cross-provider real context-preparation comparison  
**Date:** 2026-08-18  
**Case:** M1 controlled-airspace context  
**Sources:** recorded FAA UASFM + FAA DDOF + NOAA/NCEP HRRR fixtures  
**Decision boundary:** context preparation only; no flight authorization or decision-accuracy claim

## 1. Why this result matters

The earlier real slices showed three different provider effects:

- UASFM: task-bounded server-side spatial retrieval reduced returned features/bytes;
- DDOF: broad network acquisition stayed fixed, while local task selection greatly reduced downstream context;
- HRRR: task-bounded server-side spatial retrieval reduced returned bytes, but the smaller request was not faster in the single observed pair.

Those provider-level percentages cannot simply be averaged or called a single “GeoTask saving rate.” M1 therefore integrates the same recorded evidence under two explicit burden views while holding frozen critical-context requirements constant.

## 2. Frozen M1 critical requirements

Both baselines and RG must cover all four accepted requirements:

```text
airspace_guidance
obstacle_context
weather_wind
weather_visibility
```

The recorded context uses three candidates because one HRRR payload explicitly covers both weather requirements.

All compared contexts are required to be `sufficient` with no critical gaps. A burden reduction achieved by dropping a critical requirement does not count.

## 3. Compared policies

### R0 — broad-data upper bound

```text
UASFM   broad 0.3 x 0.3 degree regional response
DDOF    full broad CSV carried downstream
HRRR    broad 0.3 x 0.3 degree regional subset
```

R0 is an engineering upper bound, not an expert workflow.

### R1 — fixed regional preprocessing

```text
UASFM   fixed 0.3 x 0.3 degree regional response
DDOF    broad download + local task-bbox filtering
HRRR    fixed 0.3 x 0.3 degree regional subset
```

R1 is deliberately stronger than the earlier synthetic fixed-template baseline. It covers all frozen critical requirements and performs the obvious local DDOF filter. It is a reproducible fixed engineering workflow, not a claim about expert practice.

### RG — task-bounded GeoTask context

```text
UASFM   task bbox
DDOF    broad download + local task-bbox filtering
HRRR    task bbox, same run/variables/levels
```

RG also covers every frozen critical requirement.

## 4. Why one cost number is misleading

The same physical evidence is projected into two single-dimensional views only for comparison with the current Core scalar cost contract.

### Network-byte view

Counts bytes actually transferred from the provider.

```text
UASFM task      67,529
UASFM R0/R1    280,585

DDOF RG/R0/R1  20,518,681

HRRR task      594
HRRR R0/R1     912
```

DDOF dominates this dimension and cannot currently be task-bounded at the provider acquisition layer.

### Carried-context-byte view

Counts recorded source payload bytes carried into the downstream task-context layer before later domain interpretation.

```text
UASFM task      67,529
UASFM R0/R1    280,585

DDOF RG/R1     47,401      # local bbox selection
DDOF R0         98,840,705 # broad CSV upper bound

HRRR task      594
HRRR R0/R1     912
```

This view is not token count and is not a universal cognitive-cost measure. It is a concrete serialized-data burden dimension.

## 5. Integrated measured results

### 5.1 Network-byte burden

| Policy | Critical gaps | Network bytes |
|---|---:|---:|
| R0 broad upper bound | 0 | 20,800,178 |
| R1 fixed regional preprocessing | 0 | 20,800,178 |
| RG task-bounded context | 0 | 20,586,804 |

RG reduction relative to R0/R1:

```text
0.010258277597432142  ~= 1.03%
```

This is an important negative/limiting result:

> **Task-aware context selection barely changes total network acquisition burden in M1 because DDOF's unavoidable broad download dominates the byte total.**

The project must not market the provider-level UASFM/HRRR savings as if total network burden fell by 35–76%.

### 5.2 Carried-context-byte burden

| Policy | Critical gaps | Carried bytes |
|---|---:|---:|
| R0 broad upper bound | 0 | 99,122,202 |
| R1 fixed regional preprocessing | 0 | 328,898 |
| RG task-bounded context | 0 | 115,524 |

RG versus R0:

```text
0.9988345295234664  ~= 99.88% reduction
```

This large number mainly reflects the deliberately broad R0 DDOF carriage and must remain an upper-bound comparison.

More important is RG versus the stronger R1:

```text
0.6487543250491034  ~= 64.88% reduction
```

R1 and RG both already perform the same DDOF local filter. The remaining difference therefore comes from using task-bounded UASFM and HRRR responses instead of fixed regional responses.

## 6. Core methodological finding

The same RG candidate set is informationally sufficient under both views:

```text
network_byte projection  -> sufficient
carried_byte projection  -> sufficient
```

Only the burden number changes.

This supports an architecture decision:

> **Do not promote a universal `CostVector` into GeoTask Core yet.**

For TC1-Real M1, current Core contracts can evaluate relevance binding, exact normalized scope, resolution, shared-candidate coverage, and sufficiency. Real multi-dimensional acquisition measurements can remain in benchmark/provider metadata and be projected explicitly for a named comparison.

A Core cost abstraction should be reconsidered only if later tasks require native multi-objective budget/gate semantics that cannot remain outside Core.

## 7. Another important limitation: scope normalization is still external

The current v0.1 Core uses opaque exact scope identifiers. Recorded broader UASFM/HRRR regions are normalized to the task scope only after the benchmark adapter verifies bbox containment.

Therefore TC1-Real also exposes a real capability gap:

> **Physical geometry applicability is not yet a first-class Task Context Core operation.**

This is a better TC2 candidate than a generic cost framework because it is directly spatiotemporal and already required by real evidence.

However, this report does not automatically promote geometry applicability into Core. It becomes a candidate for the next Promotion Gate.

## 8. What M1 now supports

The current evidence supports:

1. three real public provider types can be normalized into one Task Context assessment;
2. all four frozen critical requirements can be covered by three recorded context candidates;
3. task-bounded context changes burden differently at acquisition and downstream-carriage layers;
4. a stronger fixed engineering baseline can be compared without relying on a deliberate critical miss;
5. GeoTask's M1 value is primarily **context shaping / burden allocation**, not a universal network-data saving.

## 9. What M1 still does not support

M1 does not establish:

- automatic Relevance discovery;
- real flight feasibility or authorization;
- complete obstacle/weather/airspace knowledge;
- expert-workflow labor savings;
- monetary savings;
- minimum sufficiency of the selected context;
- downstream Task Outcome Regret;
- generalization beyond the recorded Phoenix-area fixtures;
- decision-sensitive automatic spatial resolution.

## 10. Gate effect

```text
TC0 Task Context foundation                    PASS
TC1 synthetic proof                            PASS
TC1-Real UASFM provider slice                  PASS (bounded claim)
TC1-Real DDOF provider slice                   PASS (bounded claim)
TC1-Real HRRR provider slice                   PASS (bounded claim)
TC1-Real M1 integrated RG vs R0                PASS (bounded claim)
TC1-Real M1 integrated RG vs stronger R1       PASS (bounded claim)
M3 temporal mismatch                           PENDING integrated proof
M4 semantic weather breadth                    PENDING
manual/expert human-time baseline              NOT MEASURED
Task Outcome Regret                            NOT ESTABLISHED
```

The next technical question should therefore be:

> **Can GeoTask make real spatial/temporal applicability itself computable and reusable, rather than requiring the benchmark adapter to normalize broader physical scopes into opaque task-scope labels?**

That question is now supported by real evidence and is a credible candidate for the next architecture Promotion Gate.
