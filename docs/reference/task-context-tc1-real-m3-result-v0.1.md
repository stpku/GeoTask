# GeoTask TC1-Real M3 Temporal Applicability Result v0.1

**Status:** bounded real-data proof  
**Date:** 2026-08-18  
**Case:** M3 weather temporal mismatch  
**Decision boundary:** context preparation only; no flight feasibility, safety, or authorization claim

## 1. Question

M3 tests one narrow question:

> If real weather data matches the task in source, spatial extent, variables, levels, and model run, but its valid time is outside the task window, does GeoTask keep the affected context requirements as gaps?

This is a test of task applicability, not data existence.

## 2. Real A/B evidence

Two read-only NOAA/NCEP HRRR artifacts are compared.

Held constant:

```text
source        NOAA/NCEP HRRR
date          20260818
run cycle     06Z
bbox          -112.1,33.4,-112.0,33.5
variables     UGRD, VGRD, VIS
levels        10_m_above_ground, surface
```

Temporal difference:

```text
control       forecast hour 4 -> valid 2026-08-18T10:00:00Z -> 594 bytes
mismatch      forecast hour 2 -> valid 2026-08-18T08:00:00Z -> 596 bytes
```

The frozen benchmark task window is:

```text
[2026-08-18T10:00:00Z, 2026-08-18T11:00:00Z)
```

The two payloads have different source SHA-256 values and are preserved as exact recorded provider artifacts. The mismatch is not produced by editing a timestamp in a fixture.

## 3. Method

GeoTask Core v0.1 deliberately treats `spatial_scope` and `temporal_scope` as opaque caller-declared references. It does not parse UTC instants or calculate interval overlap.

M3 therefore uses a benchmark-layer adapter:

```text
provider validity
    -> explicit UTC task-window applicability check
    -> normalized opaque temporal scope if applicable
    -> existing GeoTask Core scope/resolution/sufficiency assessment
```

For an applicable artifact:

```text
valid time in task window
    -> temporal_scope = recorded-experiment-window
```

For an inapplicable artifact:

```text
valid time outside task window
    -> temporal_scope = outside-task-window:<valid_time>
    -> Core exact-scope mismatch
    -> critical context gap
```

Malformed or missing validity fields fail closed.

## 4. Result

### Control: real 10Z HRRR artifact

```text
temporal applicability     applicable
context status             sufficient
critical gaps              none
weather_wind               covered
weather_visibility         covered
```

### Real mismatch: 08Z HRRR artifact

```text
temporal applicability     not applicable
reason                     validity_before_task_window
context status             insufficient
critical gaps              weather_wind, weather_visibility
```

The weather candidate fails at exactly one declared boundary:

```text
temporal_scope_mismatch
```

The recorded UASFM and DDOF candidates are held fixed from M1, so their coverage is unchanged between control and mismatch.

The result is identical under the TC1-Real `network_byte` and `carried_byte` projections because cost projection changes burden accounting, not context applicability.

## 5. What M3 proves

M3 supports the following bounded claims:

1. **Data existence is not task applicability.** A real weather artifact may be valid source data and still be unusable for the current task because its valid time is wrong.
2. **Temporal mismatch can remain explicit instead of being silently accepted.** The two affected critical requirements remain gaps.
3. **Applicability and sufficiency are separable.** Non-weather context remains unchanged while only the time-sensitive requirements fail.
4. **The current Core contract is sufficient for fail-closed consumption after normalization.** No datetime semantics had to be added to `geotask_core` for M3.
5. **Rich temporal reasoning currently belongs outside Core v0.1.** A replaceable adapter can resolve physical time into normalized scope references before Core assessment.

## 6. What M3 does not prove

M3 does not establish:

- that a one-hour task window is universally correct;
- that any HRRR variable is sufficient for real flight decisions;
- weather forecast accuracy;
- automatic requirement discovery;
- automatic validity-window inference from arbitrary providers;
- a universal temporal algebra for GeoTask Core;
- cross-domain reuse of the temporal applicability method;
- decision outcome improvement or avoided operational regret.

## 7. Architecture implication

M1 already exposed a spatial version of the same boundary: broader real geometries had to be checked for containment before being normalized to an opaque task scope.

M3 now exposes the temporal version:

```text
physical geometry/time
    -> applicability resolution
    -> normalized task scope
    -> Core relevance / resolution / sufficiency
```

This makes **Spatiotemporal Applicability** a credible next abstraction candidate.

It should **not** be promoted into Core from this PR. The next Promotion Gate should first test whether one replaceable applicability operator/contract can serve both spatial containment and temporal validity, and then survive at least one independent non-low-altitude task/domain without embedding domain rules.

## 8. CI evidence

Exact implementation head before this report:

```text
726974afb38ba9afd06fead2c87023871cfd0005
```

`geotask-core #188` completed successfully across:

- Python 3.10 / 3.11 / 3.12 / 3.13 full pytest;
- public boundary/export;
- artifact roundtrip;
- build + twine checks;
- public export scan;
- RC build / Reference Agent replay evidence;
- merged RC evidence readiness.

The report commit must receive its own exact-head CI before the PR is considered evidence-closed.

## 9. Gate status

```text
TC1-Real M1 provider composition              PASS (bounded)
TC1-Real M3 real temporal mismatch            PASS (bounded)
Core datetime/interval semantics              NOT PROMOTED
Spatiotemporal Applicability abstraction      PROMOTION CANDIDATE
cross-domain applicability reuse              NOT YET PROVEN
M4 semantic weather breadth                   PENDING
```
