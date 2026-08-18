# GeoTask TC1 Task Context Proof Report v0.1

**Status:** synthetic proof complete; real-world proof not yet established  
**Date:** 2026-08-18  
**Branch:** `feat/task-context-engine-v0.1`  
**Scope:** TC0 Task Context foundation + TC1 deterministic synthetic proof

## 1. Executive conclusion

The TC1 synthetic proof supports a narrow claim:

> Given an explicit `TaskFrame`, explicit `ContextRequirement`s, and a bounded candidate-context universe with declared scope, resolution, and cost metadata, GeoTask can deterministically distinguish context that is relevant/applicable/sufficient from context that is missing, too coarse, out of scope, non-critical, or over budget.

The proof does **not** establish that GeoTask can yet discover the right requirements automatically, find the right real-world sources, estimate operational cost correctly, or improve a real flight/planning decision.

The current evidence therefore supports:

```text
TC0 contract foundation                 PASS
TC1 synthetic contract/proof harness    PASS
TC1 real-world value proof              NOT YET ESTABLISHED
TC2 automatic context operators          NOT YET ENTERED
```

This is intentionally not a product-completion claim.

## 2. Why TC1 exists

The working definition is:

> **GeoTask 是 Agent 的时空任务上下文引擎。**
>
> **GeoTask is a spatiotemporal task-context engine for AI agents operating in the physical world.**

The falsifiable hypothesis is not that a complete world model is always better. It is:

> For physical-world Agent tasks with heterogeneous multi-scale information, a task-adaptive context process can spend information cost on the conditions that matter to the task while avoiding unnecessary context, without increasing critical-context omission beyond an explicit bound.

TC1 begins with the simplest deterministic version of that hypothesis before any automatic requirement discovery or learned selection is introduced.

## 3. Compared policies

All current fixtures use the same three policies.

### B0 — `full_context`

Select every context candidate made available to the case.

Purpose: expensive upper-bound reference. B0 is **not** claimed to represent a good production workflow.

### B1 — `manual_template`

Select a fixed human-authored candidate list declared by the fixture.

Purpose: deterministic fixed-template baseline. The current synthetic B1 cases are deliberately constructed to expose a task-specific miss and therefore **must not** be presented as evidence that real experts or real manual workflows perform poorly.

### G0 — `declared_min_cost_v0`

For every critical requirement, choose one lowest-declared-cost candidate that is explicitly relevant, spatially/temporally applicable, and resolution-sufficient. Non-critical requirements are optional. Equal-cost candidates prefer the coarsest still-sufficient declared spatial resolution.

G0 lives under `benchmarks/`, not `geotask_core`. It is an experimental benchmark policy, not a public Core semantic rule.

G0 does not:

- discover requirements;
- search providers;
- infer geometry containment or temporal overlap from opaque scope ids;
- infer source authority;
- solve global set cover;
- estimate Value of Information;
- make a flight or planning decision.

## 4. Synthetic fixture results

All costs below use the artificial unit `fixture_cost_point`. They are useful only for deterministic comparison inside the fixture and are **not monetary, latency, labor, or compute savings claims**.

### 4.1 Low-altitude mission preparation

Critical requirements:

- corridor weather;
- applicable airspace context;
- obstacle context at 10 m or finer.

Non-critical requirement:

- POI labels for explanation.

| Policy | Selected items | Context status | CCMR | Cost | Item CRR | Key gap |
|---|---:|---|---:|---:|---:|---|
| B0 full context | 6 | `over_budget` | 0.000 | 19 | 0.000 | none |
| B1 fixed template | 4 | `insufficient` | 0.333 | 6 | 0.333 | obstacles too coarse |
| G0 task context | 3 | `sufficient_with_gaps` | 0.000 | 8 | 0.500 | non-critical POI omitted |

G0 selects:

```text
weather-500m
+ airspace-notice
+ obstacles-10m
```

It rejects the more expensive 100 m premium weather because 500 m already satisfies the declared 1000 m requirement, and it rejects the 100 m obstacle grid because the declared obstacle requirement is 10 m or finer.

The synthetic result demonstrates the contract behavior **coarsest sufficient where possible, finer only where required**. It does not prove that 10 m is a universally correct obstacle resolution.

### 4.2 Multi-scale spatial planning

Critical requirements:

- district demand at 1 km or finer;
- district facility capacity at 1 km or finer;
- hotspot-C building-demand detail at 100 m or finer.

Non-critical requirement:

- district POI labels.

| Policy | Selected items | Context status | CCMR | Cost | Item CRR | Key gap |
|---|---:|---|---:|---:|---:|---|
| B0 full context | 7 | `over_budget` | 0.000 | 38 | 0.000 | none |
| B1 fixed template | 3 | `insufficient` | 0.333 | 6 | 0.571 | hotspot-C detail missing |
| G0 task context | 3 | `sufficient_with_gaps` | 0.000 | 8 | 0.571 | non-critical POI omitted |

G0 selects:

```text
demand-1km
+ capacity-1km
+ hotspot-buildings-100m
```

This fixture exposes an important correction to the simplistic idea that a context engine is mainly a compression engine:

> **G0 and B1 select the same number of items. G0 is useful because it reallocates the information budget from a non-critical explanatory item to the local detail required by the task.**

The target is therefore not `minimum item count`. It is **minimum sufficient task context under explicit cost and miss constraints**.

## 5. Perturbation controls

TC1 includes deterministic negative/robustness controls.

### Irrelevant-context expansion

Add 50 extra non-critical POI candidates.

Expected and tested behavior:

- G0 selected critical set does not change;
- G0 declared cost does not change;
- B0 cost grows because it loads all candidate context;
- critical coverage remains unchanged.

### Fine obstacle context removed

Remove the only usable 10 m obstacle candidate.

Expected and tested behavior:

- G0 does not silently promote the remaining 100 m item;
- obstacle requirement becomes a critical gap;
- CCMR becomes `1/3`;
- context remains `insufficient`.

### Wrong-scope weather

Move all weather candidates to another declared corridor.

Expected and tested behavior:

- no weather candidate is promoted into the current task;
- weather becomes a critical gap;
- exact-scope baseline fails closed instead of assuming overlap.

### Critical context becomes too expensive

Increase the only selected fine-obstacle candidate cost so total selected cost exceeds the task budget.

Expected and tested behavior:

- critical informational coverage remains complete;
- CCMR remains zero;
- status becomes `over_budget`.

This preserves the distinction:

```text
information sufficiency != affordability
```

## 6. CI evidence

The TC1 branch was validated by GitHub Actions run `geotask-core #166`.

Final result:

```text
workflow                       SUCCESS
Python 3.10 full pytest         SUCCESS
Python 3.11 full pytest         SUCCESS
Python 3.12 full pytest         SUCCESS
Python 3.13 full pytest         SUCCESS
public boundary/export          SUCCESS
artifact roundtrip              SUCCESS
build + twine checks            SUCCESS
public export scan              SUCCESS
RC build/reference replay       SUCCESS
merged RC evidence readiness    SUCCESS
```

An earlier TC1 run failed during test collection because repository-local `benchmarks/` was imported as if it were an installed package. The fix did **not** widen global `pythonpath` or package discovery. Benchmark tests now add the repository root only around benchmark imports, while the executable smoke test invokes the benchmark from the repository root through a subprocess. This preserves the distinction between:

```text
public geotask-core package
!=
repository-local experimental benchmark policy
```

## 7. What TC1 proves — and what it does not

### Supported by current evidence

TC1 supports the claim that the new Task Context contracts can represent and deterministically test:

- explicit task/context requirement binding;
- exact declared spatial/temporal applicability;
- resolution sufficiency with explicit units;
- critical versus non-critical gaps;
- refinement need;
- information sufficiency versus cost budget;
- bounded context-selection policies outside Core.

### Not supported by current evidence

TC1 does not support claims that:

- GeoTask automatically knows what context matters;
- G0 is globally optimal;
- synthetic cost points map to real commercial savings;
- a reduced context produces a correct low-altitude or planning decision;
- GeoTask transfers responsibility for the downstream decision;
- the current public product is already a complete automatic Context Engine.

`Task Outcome Regret` remains deliberately `not available` in the synthetic suite because no independently validated downstream outcome model exists in these fixtures.

## 8. TC1-Real: next evidence gate

The next gate must replace synthetic assumptions with independently sourced physical-world data and measurable acquisition/preparation cost.

### First candidate: public low-altitude context preparation

The preferred first public reproducible slice uses independent official sources with distinct spatiotemporal roles:

1. **FAA UAS Facility Maps (UASFM)** — spatial controlled-airspace planning context and grid altitude guidance. FAA explicitly states that the maps are informational/job-aid data and do **not** themselves authorize an operation. Actual controlled-airspace authorization remains external to GeoTask.
2. **FAA Digital Obstacle File / Daily Digital Obstacle File** — known aviation obstacle context, including daily CSV availability with decimal-degree latitude/longitude in DDOF; the standard DOF follows a 56-day publication cycle.
3. **NOAA High-Resolution Rapid Refresh (HRRR)** — time-varying weather context; NOAA describes HRRR as a real-time 3-km, hourly updated atmospheric model.

Authoritative references:

- FAA UAS Facility Maps: https://www.faa.gov/uas/commercial_operators/uas_facility_maps
- FAA UAS Facility Maps FAQ: https://www.faa.gov/uas/commercial_operators/uas_facility_maps/faq
- FAA Digital Obstacle File: https://www.faa.gov/air_traffic/flight_info/aeronav/digital_products/dof/
- FAA Daily Digital Obstacle File: https://www.faa.gov/air_traffic/flight_info/aeronav/digital_products/dailydof/
- NOAA HRRR: https://rapidrefresh.noaa.gov/hrrr/

The TC1-Real task must remain **context preparation**, not flight authorization:

```text
bounded mission request
→ required context profile
→ candidate public sources
→ scope / temporal / resolution applicability
→ measure data/API/bytes/latency/preparation cost
→ produce Task Context or explicit gaps
→ hand off to an external downstream assessment
```

### Required real baselines

TC1-Real must not reuse the synthetic B1 as if it represented expert practice. It should compare against at least:

- a documented fixed checklist/script or manual preparation workflow;
- a broad/full-data retrieval baseline where feasible;
- the named GeoTask selection/refinement policy.

Where possible, report cost components separately:

```text
human preparation time
provider/data requests
bytes transferred
processing time
compute/storage
```

Do not collapse them into one score without an explicit conversion rule.

## 9. Promotion gate before public positioning changes

The homepage, README, package metadata, and whitepaper should **not yet** be rewritten to claim that automatic task-context construction is complete.

Before that promotion, require at least:

1. one TC1-Real low-altitude slice with independently sourced public data;
2. one non-low-altitude task or independently structured second domain;
3. a real/manual baseline rather than a deliberately weak synthetic template;
4. measured context-preparation cost in explicit units;
5. an independently defined critical-context reference set;
6. a downstream outcome or regret measure where a defensible reference exists;
7. explicit reporting of failures and cases where GeoTask adds no value.

Only after those gates should the project decide whether the working definition can move from architecture direction to public product claim.

## 10. Distribution-boundary note

The current release manifest includes `src/geotask_core/**`, so `task_context.py` would enter the public source export if this branch is merged. The repository-local `benchmarks/` directory is not currently part of that export manifest.

Before merge/release, make an explicit decision:

```text
A. promote task_context contracts as experimental public Core API
or
B. keep them preview/internal until TC1-Real evidence exists
```

Do not let file location make this product/API decision implicitly.

## 11. Gate verdict

**TC1 synthetic verdict: PASS, with scope strictly limited to deterministic contract/proof behavior.**

The next project question is no longer “can the new contracts be coded?” It is:

> **On a real physical-world task, can GeoTask reduce context-preparation effort or redirect information cost toward task-critical spatiotemporal detail without increasing critical-context misses or downstream regret?**

That question is the TC1-Real gate and must be answered before TC2 automation is allowed to drive the product narrative.
