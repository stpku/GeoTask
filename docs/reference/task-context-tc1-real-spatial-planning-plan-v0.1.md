# GeoTask TC1-Real Spatial Planning Proof Plan v0.1

**Status:** experiment specification; no planning recommendation claim  
**Date:** 2026-08-18  
**Scenario:** Phoenix public-library service-coverage context preparation  
**Stack:** PR #18 real-measurement harness → this scenario branch

## 1. Purpose

This is the first non-low-altitude TC1-Real scenario. It tests whether the same
Task Context contracts remain useful for a long-cycle physical-world planning
task without importing low-altitude semantics into Core.

The experiment does **not** decide where a library should be built, estimate
library capacity, or claim an optimal public investment. It only compares the
burden and critical-gap behavior of different ways of preparing spatial planning
context.

A deliberate control is retained from M1: the experiment uses the same Phoenix
area as the low-altitude case. The task changes while the place stays similar.
This makes the architectural question explicit:

> Does a different physical-world task select a different useful context even
> when it concerns the same place?

## 2. Frozen spatial scopes

All WGS84 envelopes are frozen before the RG policy is evaluated.

```text
R0 broad region   [-112.20, 33.30, -111.90, 33.60]
task area         [-112.10, 33.40, -112.00, 33.50]
hotspot           [-112.075, 33.425, -112.050, 33.450]
```

The hotspot is an experiment input, not an RG output. TC1 v0.1 does not yet
claim automatic hotspot discovery.

## 3. Public source families

The experiment uses read-only public GIS services. Source-use terms remain part
of provider provenance; upstream raw data is not automatically republished as a
GeoTask fixture.

1. **Growth projections**
   - base planning-unit geometry: `GrowthProjections_MapViewer_0524_WFL1/FeatureServer/4` (`FinalLUAUs`);
   - related population table: `.../FeatureServer/13` (`New_Pop_Emp_Data`);
   - the public service explicitly relates layer 4 to table 13;
   - planning units are keyed by `newluau`;
   - the table exposes `newluau`, `popvar`, `vardesc`, `year`, `popcount`.

   An initial diagnostic used layer 2 (`FinalLUAUs_PopEmp`). Complete ID
   measurement showed that representation repeats planning-unit geometry across
   joined population/employment records. It is retained only as negative
   provider-selection evidence and is excluded from scoring.

2. **Phoenix libraries**
   - `Public/Libraries/MapServer/0`
   - point locations only; no capacity is inferred.

3. **Land Use Area Zones**
   - `Hosted/Land_Use_Area_Zones/FeatureServer/14`
   - current service query contract is JSON-only;
   - used only as fine-grained local planning context;
   - land-use geometry is not converted into a recommendation score.

Scoring evidence records request shape, response byte/count measurements,
retrieval time and hashes. Where upstream use terms discourage redistribution,
raw source records remain outside the long-lived public fixture and only compact
measurement/provenance artifacts are retained.

## 4. Frozen critical requirements

```text
P1 projected_population_context
   Need growth-projection records for planning units intersecting the task area.

P2 existing_library_locations
   Need current source records for library locations intersecting the task area.

P3 hotspot_land_use_detail
   Need detailed land-use-zone context only for the frozen hotspot.
```

No requirement says that full task-area or broad-region land-use detail is
necessary. Carrying it is therefore measurable irrelevant-context admission.

The population table may contain multiple years/variables. The first complete
live acquisition records the observed years/`popvar` values for the frozen task
units. A specific planning year/variable must then be frozen in the benchmark
before R0/R1/RG headline comparison. RG is not allowed to choose a favorable
year after seeing burden results.

## 5. Compared preparation policies

### R0 — broad-regional upper bound

```text
growth geometry/table   broad-region planning units
libraries               broad region
land-use detail         broad region
```

R0 is an engineering upper bound, not an expert workflow.

### R1 — fixed task-area preprocessing

```text
growth geometry/table   task area
libraries               task area
land-use detail         task area
```

R1 is a reproducible fixed spatial preprocessing workflow.

### RG — task-adaptive multi-scale context

```text
growth geometry/table   task area
libraries               task area
land-use detail         hotspot only
```

RG differs from R1 only in the scale at which the explicitly local requirement
P3 is acquired. This prevents the comparison from being won by dropping a
critical requirement.

## 6. Measures

Primary measurements:

- provider request count;
- bytes transferred;
- carried serialized context bytes;
- feature / row count;
- critical gaps;
- Irrelevant Context Admission Rate for land-use records outside the frozen
  hotspot but admitted by the compared policy.

Counter-metrics / hard guards:

- provider completeness must be proven before reduction is scored;
- every headline policy must cover P1/P2/P3;
- any reduction achieved by dropping a critical requirement is a failure;
- a smaller land-use payload does not imply a better planning decision;
- no Task Outcome Regret claim is made until an independently defined downstream
  planning task and outcome metric exist.

## 7. Gate

This scenario passes TC1 cross-domain proof only if:

1. the same public Task Context contracts can represent the planning case;
2. scored provider responses are proven complete rather than silently capped;
3. all policies are evaluated against the same frozen P1-P3 requirements;
4. RG reduces at least one real context-burden / irrelevant-admission dimension
   relative to a stronger fixed R1;
5. the reduction is not achieved by increasing critical-context misses;
6. no new planning-specific concept has to be added to GeoTask Core.

If the experiment needs a new general spatial applicability primitive, that is a
TC2 Promotion Candidate, not an automatic Core change.
