# GeoTask TC1-Real HRRR Result v0.1

**Status:** paired real HRRR task/R0 acquisition recorded  
**Date:** 2026-08-18  
**Scope:** one NOAA/NCEP HRRR run/forecast hour, same variables/levels, task bbox vs broader R0 bbox  
**Decision boundary:** weather-context acquisition evidence only; not meteorological interpretation or flight-safety accuracy

## 1. Question

This slice asks:

> When a weather provider supports server-side geographic/field subsetting, can task-bounded acquisition reduce the returned context bytes relative to a broader regional request while holding model run, forecast hour, variables, and levels constant?

To avoid comparing different weather states, task and R0 were acquired in the same one-time workflow from the same HRRR run.

## 2. Frozen comparison dimensions

Both requests used:

```text
model/source       NOAA/NCEP HRRR
model date         20260818
cycle              06 UTC
forecast hour      f04
run time           2026-08-18T06:00:00Z
valid time         2026-08-18T10:00:00Z
variables          UGRD, VGRD, VIS
levels             10_m_above_ground, surface
request_count      1 per request
monetary_cost      unknown
```

Only the spatial bbox changed.

### Task bbox

```text
[-112.1, 33.4, -112.0, 33.5]
```

### R0 broader regional bbox

```text
[-112.2, 33.3, -111.9, 33.6]
```

The offline comparison refuses to calculate a reduction when source/run/valid time/forecast hour/variables/levels differ or when R0 does not contain the task bbox.

## 3. Recorded exact responses

### Task request

```text
payload bytes          594
SHA-256                bc0a27b7194b4079d3ed0b0c4afc4287f79c379ec86ffe2c766ef099d112f357
wall-clock observation 0.7786113619999995 s
```

### R0 request

```text
payload bytes          912
SHA-256                5780d52a6ab74f10a5a46e983bb78f61d96e5a482028e4c547d6045528e1f7f3
wall-clock observation 0.6329548490000008 s
```

Both stored payloads are exact GRIB2 byte sequences and are replayed offline in CI.

## 4. Measured result

For this one paired acquisition:

```text
byte reduction ratio   0.3486842105263158  (~34.87%)
```

The task-bounded request returned fewer bytes than the broader regional request while holding the weather run and requested fields constant.

However, the single task request was **slower**, not faster:

```text
task wall time   0.7786 s
R0 wall time     0.6330 s
```

This negative result is intentionally preserved.

> **Smaller context does not imply lower single-request latency.**

Network/server latency is noisy and each request was sampled only once. The result therefore supports a payload-breadth comparison, not a stable latency-performance claim.

## 5. What this supports

This evidence supports only a provider-specific statement:

> **For the recorded HRRR 06Z/f04 pair, narrowing the geographic subregion from the documented regional R0 bbox to the task bbox reduced returned GRIB2 bytes by about 34.9% while preserving the same run, valid time, variables, and levels.**

Together with the recorded UASFM and DDOF results, it shows that context cost depends on provider capabilities:

```text
UASFM
  server-side spatial bounding
  -> ~76% fewer returned features/bytes in the recorded pair

HRRR
  server-side weather subregion bounding
  -> ~34.9% fewer returned bytes in the recorded pair
  -> no latency improvement in this one pair

DDOF
  broad download remains broad
  -> no network acquisition reduction claim
  -> ~99.95% downstream row/serialized-context reduction after local selection
```

The percentages are provider/fixture-specific evidence, not universal GeoTask rates.

## 6. What this does not support

This result does not establish that:

- 34.9% is a general HRRR or GeoTask saving rate;
- smaller HRRR requests are consistently faster;
- UGRD/VGRD/VIS are sufficient for real flight weather assessment;
- the chosen bbox is minimum sufficient;
- the GRIB fields have been interpreted into a mission decision;
- the weather context is complete;
- the task request improves decision accuracy;
- automatic Relevance or decision-sensitive Resolution is solved.

It also does not yet test M4's semantic breadth dimension (necessary variables/levels versus a wider variable/level set). This slice isolates **spatial breadth** only.

## 7. Reproducibility

Stored evidence:

```text
benchmarks/tc1_real/fixtures/hrrr_phx_20260818/
  hrrr-task.grib2
  hrrr-task.record.json
  hrrr-r0-regional.grib2
  hrrr-r0-regional.record.json
  summary.json
  diagnostic.json
```

Offline tests verify:

- exact GRIB2 signatures, byte counts and SHA-256 hashes;
- same run/valid time/forecast hour/variables/levels;
- R0 bbox contains task bbox;
- recorded byte-reduction ratio;
- the observed negative latency result;
- failure when run or variable identity changes.

## 8. Gate effect

TC1-Real status after this slice:

```text
UASFM acquisition-breadth comparison       PASS (provider-specific)
DDOF downstream-context comparison          PASS (provider-specific)
HRRR spatial acquisition comparison         PASS (provider-specific)
HRRR semantic-breadth M4 comparison         PENDING
R1 fixed documented workflow                PENDING
M1–M4 integrated R0/R1/RG comparison        PENDING
real-world decision/outcome regret          NOT ESTABLISHED
```

The next step should no longer be adding another provider. The next step is to normalize these recorded UASFM/DDOF/HRRR artifacts into the same task-context comparison layer and determine whether the existing Core contracts are sufficient to express M1–M4 without introducing new abstractions prematurely.
