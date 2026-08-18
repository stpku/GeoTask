# GeoTask TC1-Real Measurement Plan v0.1

**Status:** experiment design candidate  
**Date:** 2026-08-18  
**Prerequisite:** TC1 synthetic proof; no real-world value claim yet

## 1. Question

TC1-Real asks one narrow question:

> **On a reproducible physical-world task, can a task-adaptive spatiotemporal context process reduce or redirect context-preparation effort toward task-critical information without increasing critical-context misses or defensible downstream regret?**

The experiment is about **context preparation**, not autonomous flight authorization, operational approval, or real-time control.

## 2. First public domain: low-altitude mission context preparation

Use a fictional mission geometry and time window, but populate context from independently maintained public sources.

The initial source families are:

### FAA UAS Facility Maps

Role: controlled-airspace planning context and grid altitude guidance around airports.

Important boundary: FAA states that UAS Facility Maps are informational/job-aid data for authorization requests and **do not themselves authorize operations**.

Candidate machine-readable layer observed during experiment design:

```text
FAA_UAS_FacilityMap_Data / FeatureServer / layer 0
spatial reference: EPSG:4326
geometry: polygon
query formats: JSON, GeoJSON, PBF
selected fields include:
  CEILING
  UNIT
  MAP_EFF
  LAST_EDIT
  LATITUDE
  LONGITUDE
  APT*_ICAO / APT*_NAME / APT*_LAANC
  AIRSPACE_*
```

The exact endpoint/version used by a recorded experiment must be captured in provenance rather than hard-coded as an eternal authority.

### FAA Digital Obstacle File / Daily Digital Obstacle File

Role: aviation-obstacle context.

The standard DOF is published on a 56-day cycle. FAA also publishes a Daily Digital Obstacle File; the DDOF CSV includes decimal-degree latitude and longitude.

### NOAA High-Resolution Rapid Refresh (HRRR)

Role: time-varying atmospheric context.

NOAA describes HRRR as a real-time 3-km, hourly updated atmospheric model. The experiment must record the exact run/valid time and variables actually used rather than treating “HRRR” as one timeless data item.

## 3. Do not collapse real preparation cost into one synthetic number

The synthetic TC1 suite uses one artificial scalar `fixture_cost_point` only to test deterministic contracts.

TC1-Real must measure a vector:

```text
AcquisitionMeasurement
  monetary_cost
  request_count
  bytes_transferred
  wall_clock_seconds
  processing_cpu_seconds     # where measurable
  storage_bytes              # where relevant
  human_preparation_seconds  # manual baseline only / measured, not guessed
```

Missing components remain `unknown`; they must not be silently converted to zero.

A later optimization policy may introduce an explicit utility/conversion function, but TC1-Real v0.1 should report raw dimensions side by side.

This means the current Core field `acquisition_cost: float` remains a declared abstract budget mechanism. TC1-Real measurement must **not** pretend that this scalar is already a universal real-cost model.

## 4. Evidence units

Each recorded source retrieval should preserve at least:

```text
source family
retrieval timestamp
source URL / endpoint identity
request parameters or bounded query geometry
source effective/run/valid time where available
response byte count
source-declared CRS
source-declared units
source-declared resolution or feature semantics where available
content hash of the stored offline fixture
```

Provider metadata is evidence about the input used by the benchmark; it is not proof that the downstream domain conclusion is correct.

## 5. Task variants

Use multiple mission variants so the experiment cannot succeed merely because one fixed list of three sources was hand-picked.

Minimum matrix:

### M1 — controlled-airspace context matters

The mission corridor intersects a recorded UASFM area. Airspace guidance, obstacle context, and weather context are all candidate requirements.

### M2 — local spatial detail stress

The mission geometry is chosen so local obstacle filtering materially reduces the obstacle context passed downstream compared with a broad/full-data preparation baseline.

### M3 — temporal mismatch

Provide a weather candidate whose valid/run time does not satisfy the mission time requirement. GeoTask must preserve the weather gap rather than treating any HRRR artifact as applicable.

### M4 — over-precision / unnecessary context

Make both coarse-enough and finer/more-expensive candidate context available for a declared requirement. The benchmark must show whether the named policy avoids unnecessary detail while preserving the reference requirement.

No variant may be presented as a real flight-safety determination.

## 6. Baselines

### R0 — broad retrieval / processing baseline

Acquire or process the broad source products required by the documented conventional pipeline, then crop/filter only downstream.

This is an upper-bound engineering baseline, not a strawman claim about expert practice.

### R1 — fixed documented checklist/script

Use one explicit, reproducible checklist or script that does not adapt requirements/resolution to the task variant.

If a real expert workflow is measured later, report it separately; do not relabel this synthetic/fixed baseline as “expert”.

### RG — GeoTask candidate policy

Use explicit TaskFrame + independently specified critical-context reference requirements + declared applicability/resolution checks. Automatic requirement discovery remains outside the first TC1-Real gate.

This deliberately tests context selection/refinement before testing automatic Relevance.

## 7. Critical-context reference set

TC1-Real cannot grade GeoTask using requirements generated by the same GeoTask policy being evaluated.

For each mission variant, the critical-context reference set must be frozen independently before running RG. Sources may include:

- explicit experiment/task specification;
- published source semantics;
- a domain checklist documented separately from the policy under test;
- independent expert review when available.

Any disputed requirement is marked disputed and excluded from headline CCMR until adjudicated.

## 8. Measurements

Report at least:

```text
Critical Context Miss Rate
request count
bytes transferred
wall-clock preparation time
processing time where measurable
human preparation time for manual baseline
selected context item count
selected context byte size
scope mismatch count
resolution-refinement count
unknown/disputed requirement count
```

`Task Outcome Regret` remains unavailable until an independently defensible downstream reference outcome is defined.

## 9. Success / failure rule

Do not define success as “GeoTask wins every row.”

A useful TC1-Real result should show at least one repeatable regime where:

```text
CCMR_RG <= CCMR_baseline
```

while one or more measured preparation burdens are lower or more effectively allocated.

Also record regimes where:

```text
GeoTask adds overhead with no context-quality benefit
```

Those cases define the boundary of where GeoTask should **not** be used.

## 10. Offline reproducibility

Network acquisition and benchmark replay are separate steps.

```text
acquire public source
  -> record provenance + raw response hash + measurement
  -> store a legally/reasonably sized bounded fixture or normalized excerpt
  -> run deterministic benchmark offline
```

CI must not depend on live FAA/NOAA network availability. Live-source refresh is a separate manual/optional acquisition workflow.

## 11. Promotion rule

TC1-Real can promote new Core semantics only when the real experiment exposes a reusable gap that cannot be represented by current contracts.

Likely candidates to evaluate, **not pre-approve**, include:

- real geometry/time applicability beyond opaque exact-scope ids;
- multi-dimensional acquisition cost;
- explicit source effective/run/valid time contracts;
- decision-sensitive resolution/refinement.

Do not add these to Core merely because they sound generally useful.

## 12. Current decision

The next implementation slice should therefore be a **read-only acquisition + measurement harness**, not a new autonomous Agent loop:

```text
public source
  -> bounded retrieval
  -> provenance/measurement record
  -> normalized ContextCandidate
  -> existing Task Context assessment
  -> offline R0 / R1 / RG comparison
```

This keeps TC1-Real focused on the product hypothesis: whether GeoTask improves the preparation of task-specific spatiotemporal context at a defensible cost.
