# GeoTask Task Context Method Update v0.2

**Status:** architecture candidate supported by TC1 + first real Resolution Stress Test  
**Date:** 2026-08-18

## 1. Why v0.1 needs a method correction

The initial Task Context Engine direction used the linear chain:

```text
Task
 -> Relevance
 -> Applicability
 -> Sufficiency
 -> Resolution
 -> Task Context
```

TC1 and the first real Resolution Stress Test show that this ordering is too
linear.

Three observations now matter:

1. scope refinement can reduce irrelevant context without changing spatial
   resolution;
2. the correct source representation can dominate context cost before any scope
   or resolution decision;
3. resolution is needed only when the **current context remains insufficient for
   the task**, not as an independent stage every task must execute.

Therefore `Resolution` should not remain a mandatory step after `Sufficiency`.

## 2. Revised method

The architecture candidate becomes:

```text
Task
  |
  v
Requirements
  |
  v
Relevance
  |
  v
Applicability
  |
  v
Candidate Context
  |
  v
Sufficiency
  |-------------------------------|
  | enough                        | insufficient
  v                               v
Task Context                 Context Gap
                                  |
                                  v
                              Refinement
                         /        |        \
                    scope   resolution   representation
                       \       source/evidence      /
                         \       time/freshness    /
                                  |
                                  v
                            Candidate Context
                                  |
                                  +----> Sufficiency
```

The loop terminates when the task context is sufficient or when the declared
context budget/policy says further refinement is not justified.

## 3. What Sufficiency now means

Sufficiency is not "all relevant world data has been collected."

It asks a task-relative question:

> Does the current context distinguish the next task action/output to the degree
> required by the task contract?

For deterministic threshold-like tasks, one useful formulation is:

```text
U(C,T) = all physical states still compatible with context C and its declared
         uncertainty / aggregation / applicability contracts

A(C,T) = { next_action(x,T) : x in U(C,T) }

sufficient(C,T) iff |A(C,T)| = 1
```

Other task families may use different sufficiency measures, but they must define
their own countermetric against unsupported stopping.

## 4. Resolution moves under Refinement

The first real DEM stress test shows:

```text
48 frozen cases
45 stop at 32 m
 3 refine
 2 stop at 16 m
 1 stop at 8 m
 0 require 4 m / 1 m
```

The same conservative sufficiency rule produces all of these outcomes.

Therefore the architecture should ask:

```text
Is current context sufficient?
```

before it asks:

```text
Should spatial resolution be increased?
```

Resolution becomes one possible response to a specific context gap.

## 5. Scope is also a refinement dimension

TC1 planning showed that:

```text
P3 task-area land use  -> hotspot-only land use
```

reduced irrelevant context while preserving the same requirement. That was
**scope refinement**, not resolution refinement.

Low-altitude UASFM/HRRR similarly use task-bounded provider retrieval where the
provider permits it.

Thus `Refinement` must not be synonymous with "make the grid finer."

## 6. Representation is a refinement dimension

The Phoenix planning experiment initially used a joined Growth layer with
118,190 complete features for only 471 unique planning units. Switching to the
base planning-unit layer + related population table removed duplicated geometry
before any resolution optimization.

The DEM stress test adds the complementary lesson that a coarse representation
can remain sufficient when it preserves the task-relevant invariant (for
example a conservative min/max envelope).

Therefore a context engine must distinguish:

```text
more data
finer data
better task-preserving representation
```

They are not interchangeable.

## 7. Source/evidence and time are refinement dimensions

Existing GeoTask Evidence / Evidence Request semantics fit naturally into the
same loop:

```text
Context Gap
 -> missing authoritative source
 -> request/acquire evidence
 -> bind applicability
 -> re-evaluate sufficiency
```

Likewise a stale or temporally inapplicable candidate may require a fresher
source rather than finer spatial resolution.

This keeps Evidence as important infrastructure without making "continuous
World State update" the center of every task.

## 8. Cost enters after the gap is identified

A gap does not imply unlimited acquisition.

Refinement choices should eventually compare alternatives such as:

```text
finer resolution
narrower/broader scope
new provider
fresh observation
manual verification
accept unresolved gap / stop task
```

against explicit cost dimensions.

TC1-Real already showed that cost is multi-dimensional:

- network requests/bytes;
- carried context bytes;
- local processing;
- storage;
- human work.

Do not collapse these into one universal cost scalar until a task/application
provides a valid projection.

## 9. Tool implication

GeoTask should not become the producer of every multiresolution or transformed
source representation.

Preferred boundary:

```text
Provider / GIS / domain system
    -> exposes native or cached representations

GeoTask
    -> knows which representation is applicable
    -> evaluates whether current context is sufficient
    -> requests the next refinement only when needed

Agent / domain model
    -> consumes the resulting Task Context
```

This keeps GeoTask as a **Task Context Engine**, not a remote-sensing processing
platform, database, or general GIS.

## 10. Revised method vocabulary

The working vocabulary should therefore be:

```text
Relevance      what can matter to this task?
Applicability  can this source/rule/model/context item be used here and now?
Sufficiency    does the current context support the required next task output?
Gap            what specifically remains unresolved?
Refinement     what context action could resolve that gap?
Task Context   the bounded context admitted for task reasoning/action
```

`Resolution` remains an important physical-world attribute and refinement mode,
but is no longer a peer stage that every task must traverse.

## 11. Updated core research question

The method now points to a more precise research problem:

> **Given a physical-world task and finite context budget, how can an Agent know
> what context is relevant and applicable, determine when that context is
> already sufficient, and choose the lowest-cost refinement that resolves any
> remaining task-critical ambiguity?**

This is a stronger statement of "因地制宜、因时而变" because the adaptation is
not tied only to place/time or grid size; it is driven by the concrete gap
between current context and task sufficiency.

## 12. Current promotion status

```text
Task Context contracts                    implemented v0.1
Spatial scope relation primitive          TC2.0 PASS
Real scope-refinement evidence             PASS
Real resolution-refinement evidence        first scenario PASS
Sufficiency-Guided Refinement Core method  HOLD pending independent reuse
Automatic Relevance discovery              NOT CLAIMED
Automatic optimal context construction     NOT CLAIMED
```

The next high-value validation is a second independent physical-world task where
the same `Sufficiency -> Gap -> selective Refinement` pattern appears without
terrain/DEM-specific semantics.
