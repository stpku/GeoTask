# GeoTask TC1-Real M4 Semantic Weather Breadth Result v0.1

**Status:** bounded real-data proof  
**Date:** 2026-08-18  
**Case:** M4 unnecessary weather breadth  
**Decision boundary:** context preparation only; no flight feasibility, safety, or authorization claim

## 1. Question

M4 tests one narrow question:

> When source, model run, valid time, and task geometry are held constant, can task-specific semantic selection reduce provider payload without losing any frozen critical-context coverage?

This is a test of context breadth, not forecast quality.

## 2. Real A/B evidence

Two read-only NOAA/NCEP HRRR requests are compared.

Held constant:

```text
source        NOAA/NCEP HRRR
date          20260818
run cycle     06Z
forecast hour 4
valid time    2026-08-18T10:00:00Z
bbox          -112.1,33.4,-112.0,33.5
```

### Narrow task-specific request

```text
variables     UGRD, VGRD, VIS
levels        10_m_above_ground, surface
payload       594 bytes
```

### Real broader request

```text
variables     UGRD, VGRD, VIS, GUST, TMP, DPT, RH
levels        10_m_above_ground, surface, 2_m_above_ground
payload       1580 bytes
```

The broader request strictly contains the narrow variable and level sets.

## 3. Method

`benchmarks/tc1_real/semantic_breadth.py` fails closed unless the two recorded requests match in every non-semantic comparison dimension:

- provider source;
- date;
- model cycle;
- forecast hour;
- spatial bbox;
- run time;
- valid time.

It then requires the broad variable set and level set to be strict supersets of the frozen narrow sets.

Recorded UASFM and DDOF candidates are held fixed from M1. Both weather candidates are bound only to the frozen requirements they actually serve:

```text
weather_wind
weather_visibility
```

Extra source variables/levels do not automatically create extra requirement coverage.

## 4. Result

Provider-local HRRR payload reduction from the real broad request to the task-specific narrow request:

```text
1 - 594 / 1580
= 0.6240506329113924
~= 62.4%
```

At the same time:

```text
narrow full context status   sufficient
broad full context status    sufficient
narrow critical gaps         none
broad critical gaps          none
requirement coverage change  none
```

The result is identical under the TC1-Real `network_byte` and `carried_byte` projections for the HRRR payload itself. Full-context totals differ between those projections because DDOF has a different acquisition/selection shape; M4 therefore does not use full-context totals as its headline metric.

## 5. Measure and counter-measure

Primary M4 metric:

```text
provider-local unnecessary payload burden
```

Observed reduction:

```text
62.4% versus the recorded broader HRRR request
```

Required counter-metric:

```text
critical-context coverage loss
```

Observed:

```text
0 frozen critical requirements lost
```

This pairing is essential. Payload reduction alone would reward deleting useful context.

## 6. What M4 proves

M4 supports the following bounded claims:

1. **Semantic breadth is independently measurable from spatial and temporal breadth.** The A/B pair keeps bbox and valid time fixed.
2. **More provider data does not necessarily produce more task coverage.** The extra variables/level add bytes but do not cover any additional frozen critical requirement.
3. **Task-specific source selection can reduce provider payload while preserving the declared requirement set.** In this recorded HRRR pair, the payload reduction is approximately 62.4% with zero frozen coverage loss.
4. **The current Core contract does not need a provider-specific weather ontology for this proof.** Explicit requirement bindings remain outside source field count.

## 7. What M4 does not prove

M4 does not establish:

- a universal 62.4% context-saving rate;
- that `DPT/GUST/RH/TMP` are irrelevant to every low-altitude task;
- that bytes equal model tokens, human cognitive load, latency, or monetary cost;
- that the frozen narrow subset is sufficient for a real flight decision;
- automatic requirement discovery;
- automatic source-field selection;
- weather forecast accuracy;
- improved operational outcomes or avoided regret.

The broader request is an explicit engineering baseline, not a claim about an expert's normal workflow.

## 8. Architecture implication

M1, M3, and M4 now expose three separate dimensions of Task Context applicability and sufficiency:

```text
M1  spatial breadth / provider composition
M3  temporal applicability
M4  semantic breadth
```

Together they suggest that the next reusable abstraction should not be a larger hard-coded weather or low-altitude schema. A stronger candidate is a replaceable **Spatiotemporal Applicability + Context Selection** boundary that can resolve rich source semantics into the small stable Core contract.

This remains a promotion candidate, not a Core conclusion. Cross-domain evidence is still required before a universal contract is frozen.

## 9. CI evidence

Exact implementation/provenance head before this report:

```text
3c0f402fbcaf22e34d7324141f06ba84177c8982
```

`geotask-core #190` completed successfully across:

- Python 3.10 / 3.11 / 3.12 / 3.13 full pytest;
- public boundary/export;
- artifact roundtrip;
- build + twine checks;
- public export scan;
- RC build / Reference Agent replay evidence;
- merged RC evidence readiness.

The report commit must receive its own exact-head CI before the PR is considered evidence-closed.

## 10. Gate status

```text
TC1-Real M1 provider composition              PASS (bounded)
TC1-Real M3 real temporal mismatch            PASS (bounded, separate PR)
TC1-Real M4 real semantic breadth             PASS (bounded)
Core weather-variable ontology                NOT PROMOTED
Spatiotemporal/context-selection abstraction  PROMOTION CANDIDATE
cross-domain reuse                            NOT YET PROVEN
```
