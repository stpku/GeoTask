# GeoTask Task Context Resolution Promotion Review v0.1

**Status:** AUTOMATIC RESOLUTION PROMOTION = HOLD; REAL STRESS TEST REQUIRED  
**Date:** 2026-08-18

## 1. Review question

TC1 established real value for **scope/extent selection**:

```text
which part of the physical world should enter this task context?
```

It has not yet established a generic answer to the different question:

```text
how fine must the selected physical context be?
```

The distinction is mandatory:

- `scope / extent` = which area/time/object subset is admitted;
- `resolution` = granularity inside the admitted scope;
- `representation / aggregation` = what task-relevant information is preserved
  when that context is made coarser.

The spatial-planning proof's task-area -> hotspot transition is scope refinement,
not evidence of 1 km -> 100 m -> 10 m resolution refinement.

Low-altitude M1 declares HRRR <= 3 km / <= 1 hour requirements, but TC1 contains
no same-source coarse-vs-fine experiment proving that a coarser representation
would change the frozen task result.

Therefore adaptive Resolution is not yet eligible for Core promotion.

## 2. Core counterexample: finer is not automatically better

Suppose a task only needs the maximum bare-earth elevation inside a frozen
corridor and a fine raster is deterministically coarsened with maximum
aggregation over exactly the same support.

The maximum can be decision-preserving even at a much coarser raster scale.
Blindly refining to the finest available cells would increase cost without
changing the task-relevant statistic.

Conversely, using mean elevation and then observing that a narrow peak was lost
would only prove that the chosen aggregation was unsuitable. It would not prove
that GeoTask needs a generic adaptive-resolution algorithm.

This creates a stronger architectural principle:

> **Resolution sufficiency is relative to the task operator and the information
> invariant preserved by the representation, not to pixel size alone.**

## 3. Candidate method: Decision-Preserving Coarsening

Let:

- `T` be the frozen task;
- `C_r` be context available at resolution `r`;
- `U_r(T)` be the set of admissible fine-scale physical states consistent with
  `C_r` and the declared aggregation/error contract;
- `D_T(x)` be the next task decision/action for fine-scale state `x`.

Resolution `r` is sufficient only when:

```text
| { D_T(x) : x in U_r(T) } | = 1
```

In words:

> every fine-scale world still compatible with the current coarse context leads
> to the same next task action.

If the possible-decision set has more than one member, refinement is justified.
If it has exactly one member, refinement should stop even when finer data exists.

For a scalar threshold `tau`, a common special case is:

```text
coarse estimate/bounds = [lower_r, upper_r]

upper_r < tau   -> same below-threshold action for every admissible fine state
lower_r > tau   -> same above-threshold action for every admissible fine state
otherwise       -> resolution-sensitive; refine if the task still justifies cost
```

The error/bound contract must be defined before reading the fine reference. A
post-hoc bound chosen after seeing the answer is invalid evidence.

## 4. Why this is stronger than a fixed resolution rule

A rule such as:

```text
low altitude -> always 1 m
planning -> always 100 m
```

is only a domain convention. It cannot explain when finer data is unnecessary or
when a nominally fine dataset still omits the statistic the task needs.

The candidate method instead asks:

```text
Task
 -> required decision invariant
 -> representation / aggregation contract
 -> uncertainty or conservative bound at current resolution
 -> can any admissible finer state change the action?
      no  -> STOP
      yes -> REFINE
```

This makes resolution choice an ex-ante action rule rather than an ex-post
justification.

## 5. Required real benchmark structure

A TC2 Resolution Stress Test must use the **same underlying authoritative source**
for fine and coarse representations whenever possible. Coarse variants should be
derived deterministically from one pinned fine reference so that source/model
changes are not mistaken for resolution effects.

Preferred first source family:

```text
USGS 3DEP 1 m bare-earth DEM
```

The benchmark may derive 5 m / 10 m / 30 m representations locally with frozen
aggregation rules. The source is a physical-world elevation reference, not a
flight authorization product.

The benchmark must freeze before scoring:

1. physical task scope/corridor;
2. task output and decision threshold(s);
3. fine-reference role;
4. coarse aggregation method(s);
5. uncertainty/conservative-bound construction;
6. candidate resolution ladder;
7. refinement cost measure.

## 6. Two mandatory controls

### R-A — no-refinement positive control

Construct a task statistic for which the coarse representation is explicitly
decision-preserving (for example, a conservative extremum statistic over the
same support).

Expected behavior:

```text
coarse context sufficient -> STOP
```

A policy that always asks for the finest data fails this control.

### R-B — resolution-sensitive stress case

Construct a different frozen physical task in which a coarse cell/aggregation
leaves multiple task outcomes possible, while a finer representation resolves
the ambiguity.

Expected behavior:

```text
coarse decision set has >1 possible action -> REFINE
fine context resolves to one action        -> STOP
```

The stress case must arise from real source structure, not from changing the
threshold after inspecting the fine answer.

## 7. Measures

Primary metric:

### Unsafe Resolution Stop Rate (URSR)

```text
URSR =
  cases where policy stops at a coarse resolution but fine reference changes
  the frozen task action
  / all resolution-sensitive cases
```

Target direction: `-> 0`.

Counter-metric:

### Unnecessary Refinement Rate (URR)

```text
URR =
  cases refined despite an already proven decision-preserving coarse context
  / all decision-preserving coarse cases
```

Target direction: `-> 0`.

Cost measure:

### Refinement Cost Ratio

Track bytes / cells / processing time / provider requests separately. Do not
collapse them into one universal scalar until real evidence justifies a cost
projection.

Additional diagnostic:

### Decision-Preservation Margin

Record the distance between the current conservative decision bound and the
frozen threshold. Small/overlapping margins are candidates for refinement;
large one-sided margins are evidence for stopping.

## 8. Promotion gate

Adaptive Resolution may be considered for Core only if a real benchmark shows:

1. the same task-relative sufficiency rule handles both the mandatory STOP and
   REFINE controls;
2. URSR remains zero or acceptably bounded under the frozen reference test;
3. URR is materially lower than an always-finest baseline;
4. the method does not require low-altitude-specific semantics in Core;
5. the needed abstraction is not already expressible as a domain-specific
   aggregation/uncertainty contract outside Core.

Until then:

> **HOLD automatic/adaptive Resolution promotion.**

The existing `ContextRequirement.max_spatial_resolution` remains a declared
contract check. It must not be misrepresented as an automatic resolution-choice
algorithm.
