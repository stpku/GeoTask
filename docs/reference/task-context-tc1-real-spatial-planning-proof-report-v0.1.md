# GeoTask TC1-Real Spatial Planning Proof Report v0.1

**Status:** R1↔RG HEADLINE PASS; R0 retained as source-gap diagnostic  
**Date:** 2026-08-18  
**Scenario:** Phoenix public-library service-coverage **context preparation**  
**Claim boundary:** context preparation only; no library investment recommendation or planning-outcome accuracy claim

## 1. Question tested

This is the first non-low-altitude TC1-Real scenario. It asks whether the same
GeoTask Task Context contracts used by the low-altitude proof remain useful for
a long-cycle physical-world planning task when the place is similar but the task
changes.

The experiment does **not** decide where a library should be built. It tests a
narrower question:

> Can a task-scoped, multi-resolution preparation policy carry materially less
> spatial context than a fixed task-area policy while preserving the same frozen
> critical context requirements?

## 2. Frozen inputs

The following were fixed before headline scoring:

```text
R0 broad region   [-112.20, 33.30, -111.90, 33.60]
task area         [-112.10, 33.40, -112.00, 33.50]
hotspot           [-112.075, 33.425, -112.050, 33.450]

P1 projected_population_context
P2 existing_library_locations
P3 hotspot_land_use_detail

population variable   HHPop
source description    Houshold Population   # exact source spelling
planning year         2030
```

The hotspot is an experiment input, not an RG output. The 2030 horizon is a
benchmark input, not a claim that 2030 is the uniquely correct real-world
library-planning horizon.

## 3. Provider representation corrections before scoring

The first live experiment produced two failures that were retained as negative
evidence rather than tuned away:

1. ordinary ArcGIS responses hit a 2,000-record transfer ceiling;
2. joined Growth Projections layer 2 (`FinalLUAUs_PopEmp`) repeated base
   planning-unit geometry across related Pop/Emp records.

Complete IDs-first measurement of that joined layer returned 118,190 features
for only 471 unique `newluau` planning units and approximately 172 MB of network
payload. It is therefore excluded from scoring rather than used to manufacture a
large reduction baseline.

The scored representation uses:

```text
base planning units   layer 4  FinalLUAUs
population context    table 13 New_Pop_Emp_Data
relationship key      newluau
```

Layer 4 complete measurement produced:

```text
broad base units   471
 task base units   125
 task ⊂ broad      proven
```

## 4. Population coverage result

After population semantics were frozen to `HHPop @ 2030`, the source exposed a
real coverage asymmetry:

```text
R0 broad units               471
matching frozen population   469
missing units                  2
R0 P1 coverage               FAIL
```

The missing rows are preserved as unknown/gaps. They are not interpreted as zero
population and the experiment does not switch variables or years after observing
the failure.

An independent task-only measurement then established:

```text
task base units              125
HHPop@2030 rows              125
covered units                125
missing units                  0
extra units                    0
P1 task coverage             PASS
population network bytes   18,015
base-unit lookup bytes       6,663
```

Therefore R0 is retained as a **non-scoring broad source-gap diagnostic**. The
headline comparison is R1 vs RG, where both policies satisfy the same frozen
P1/P2/P3 requirements.

## 5. Headline policies

### R1 — fixed task-area preprocessing

```text
P1 population   task-area base units + HHPop@2030
P2 libraries    task area
P3 land use     entire task area
```

### RG — task-adaptive multi-scale preparation

```text
P1 population   task-area base units + HHPop@2030
P2 libraries    task area
P3 land use     frozen hotspot only
```

RG does not drop a critical requirement. Relative to R1, it changes only the
spatial scale at which the explicitly local P3 requirement is acquired.

## 6. Recorded real measurements

Common R1/RG burden:

```text
P1 base-unit lookup       6,663 bytes
P1 HHPop@2030            18,015 bytes
P2 task libraries           488 bytes
```

P3 differs:

```text
R1 task-area land use   145,870 bytes   17 records
RG hotspot land use      26,147 bytes    3 records
```

Total recorded network burden:

```text
R1   171,036 bytes
RG    51,313 bytes
```

Therefore:

```text
RG vs R1 network-burden reduction = 69.9987%
```

For the explicitly local P3 requirement alone:

```text
land-use network reduction = 82.0751%
```

The hotspot contains 3 required land-use records. R1 admits 14 additional
land-use records outside that frozen hotspot:

```text
R1 irrelevant land-use admission = 14 / 17 = 82.3529%
RG irrelevant land-use admission = 0 / 3  = 0%
```

These are context-preparation measurements, not outcome-quality measurements.

## 7. Existing Core replay

The compact measurements are converted into the existing v0.1 contracts:

```text
TaskFrame
ContextRequirement
ContextCandidate
assess_task_context(...)
```

No new planning-specific Core concept is required.

Because Core v0.1 deliberately performs exact scope-reference matching rather
than geometric containment, the benchmark adapter may normalize a provider
scope to a requirement scope only after compact measurement has independently
proved the relevant subset relationship. Missing population coverage, truncated
provider responses, changed frozen population semantics, or unproven scope
containment all fail closed in offline tests.

## 8. What this experiment proves

Within this frozen scenario, the evidence supports the following limited claim:

> A task-scoped multi-resolution context policy can materially reduce real
> context acquisition/admission burden relative to fixed task-area preprocessing
> while preserving the same declared critical context requirements.

It also provides cross-domain evidence for three architectural ideas:

1. **Task, not place, determines useful context.** The Phoenix low-altitude and
   planning cases concern a similar physical area but require different source
   families and context structures.
2. **Representation selection precedes resolution optimization.** Choosing a
   duplicated joined world representation can dominate cost before spatial
   refinement begins.
3. **Completeness and coverage are distinct.** A provider response can be
   completely retrieved yet still leave required entities without matching
   context.

## 9. What this experiment does not prove

This report does **not** prove:

- that GeoTask improves library siting accuracy;
- that 2030 is the correct planning horizon;
- that the frozen hotspot is automatically discoverable;
- that 69.9987% is a general GeoTask savings rate;
- that smaller context always improves downstream model or human decisions;
- that the broad R0 policy is a valid expert baseline;
- that Relevance, Sufficiency, or Resolution should already be promoted as fully
  automatic Core algorithms.

Task Outcome Regret remains unmeasured because no independently defined
planning-decision outcome function exists in TC1 v0.1.

## 10. TC1 cross-domain gate interpretation

The planning scenario satisfies the narrow cross-domain proof requirements for
**Task Context contracts + task-scoped multi-resolution preparation**:

- same general Task Context contracts: **PASS**;
- no planning-specific Core semantic added: **PASS**;
- provider completeness checked before scoring: **PASS**;
- frozen P1/P2/P3 preserved in R1/RG: **PASS**;
- real burden dimension reduced relative to stronger task-area R1: **PASS**;
- Critical Context Miss increased by RG: **NO** under the frozen requirements;
- planning outcome quality proven: **NOT CLAIMED**.

R0 does not pass P1 and remains a diagnostic rather than being repaired for the
sake of a symmetric three-policy chart.

## 11. Promotion candidate created by TC1

The repeated cross-domain need is now narrower than a generic "World State"
primitive:

> determine whether a provider context scope is applicable to a task requirement
> scope, including explicit spatial containment/overlap and resolution semantics,
> without relying on opaque string equality.

This is a candidate for **TC2 Spatial Applicability Promotion Gate**. It is not
automatically promoted by this report. Promotion requires review against both
the low-altitude and planning evidence, a stable deterministic contract, and no
domain-specific policy leakage.
