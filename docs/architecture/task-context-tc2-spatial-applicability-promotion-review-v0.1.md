# GeoTask TC2 Spatial Applicability Promotion Review v0.1

**Status:** TC2.0 OPERATOR PROMOTION = APPROVE; TC2.1 TASK-CONTEXT BINDING = HOLD  
**Date:** 2026-08-18

## 1. Promotion question

TC1 deliberately kept physical-scope reasoning outside GeoTask Core. Both real
proof lines now independently expose the same limitation:

> a provider context can cover a task requirement even when its scope identifier
> is not exactly equal to the task scope identifier, but v0.1 Task Context can
> only compare opaque scope strings.

The promotion question is therefore not whether GeoTask needs a new GIS model.
It is narrower:

> Has deterministic **spatial scope applicability** appeared in enough
> independent physical-world tasks to justify a generic Core primitive?

## 2. Evidence A — low-altitude M1

Recorded UASFM and HRRR baselines use a broader regional bbox than the task bbox.
The TC1-Real adapter may normalize those candidates to the task scope only after
it proves bbox containment.

The M1 integrated result explicitly records this as a capability gap:

```text
broader physical provider scope
  -> adapter verifies bbox containment
  -> adapter normalizes to opaque task-scope id
  -> current Task Context exact-string applicability succeeds
```

Without the adapter proof, exact scope-label matching is insufficient.

## 3. Evidence B — long-cycle spatial planning

The planning proof repeats the same structural need under a different task and
different provider families:

```text
broad region  contains task area
 task area    contains frozen hotspot
```

R0/R1/RG adapters currently prove those relationships from recorded provider ID
sets/bboxes before normalizing candidates to the requirement scope.

This task is not a low-altitude task, does not use airspace/weather semantics,
and does not require any new planning-specific Core concept.

## 4. Reuse test

Promotion Gate criterion:

```text
same capability need
+ two independent physical-world task families
+ deterministic semantics
+ no domain policy leakage
= eligible for Core review
```

The current evidence passes that test for **axis-aligned rectangular scope
relations**.

It does **not** yet prove a universal geometry applicability abstraction covering
all polygon/multipolygon/trajectory/topological cases.

## 5. Existing Core capability audit

GeoTask Core already owns deterministic spatial predicates including:

- `line_intersects_rect`;
- `multi_polyline_intersects_rect`;
- `point_in_polygon`;
- `polygon_contains_point`;
- `rect_contains_point`;
- time/altitude overlap predicates.

Therefore TC2 should reuse the existing deterministic spatial kernel rather than
introducing a second GIS or world-model subsystem.

The missing primitive for the two TC1 real proofs is narrower:

```text
rect_contains_rect(container, target)
rect_overlaps_rect(a, b)
```

Boundary contact semantics must be explicit and consistent with existing closed
rectangle predicates.

## 6. TC2.0 decision — APPROVE operator-only promotion

Promote only deterministic rectangle-to-rectangle spatial relations into the
existing Core spatial-operator layer.

### Required properties

1. dependency-free and deterministic;
2. coordinates remain in the already normalized common coordinate space;
3. no CRS transformation inside the operator;
4. closed-boundary semantics are explicit;
5. malformed/min-max ordering remains a validation responsibility at the
   contract/document boundary, consistent with existing Core design;
6. unit tests cover equality, strict containment, partial overlap, boundary
   contact, and disjoint scopes;
7. both low-altitude and planning benchmark adapters can replay against the new
   predicates without changing their frozen task requirements.

### Non-goals

- no automatic spatial-scope discovery;
- no polygon-to-polygon generalization yet;
- no spatial index;
- no provider-specific query logic;
- no automatic hotspot selection;
- no resolution policy;
- no new World State abstraction.

## 7. TC2.1 decision — HOLD Task Context native binding

Do **not** yet change `TaskFrame.spatial_scope` / `ContextRequirement.spatial_scope`
/ `ContextCandidate.spatial_scope` from opaque references into a new geometry
object.

Reasons:

1. the two real proofs establish the need for deterministic scope relations, but
   not the correct long-term geometry-reference contract;
2. existing GeoTask documents already have their own object/CRS/unit model, and
   duplicating geometry inside Task Context would create parallel semantics;
3. a callback/resolver injected into `assess_task_context()` could make Core
   applicability depend on arbitrary caller logic, weakening determinism;
4. automatic native binding should be promoted only after operator replay shows
   that the remaining adapter ceremony is stable and repetitive.

Therefore TC2.0 should first make the missing relation **computable**. TC2.1 may
later make it **native to Task Context**.

## 8. Measure

TC2.0 is successful only if it removes benchmark-local containment arithmetic
without changing frozen task outputs.

Primary regression measure:

```text
low-altitude M1 replay outcome  unchanged
planning R1/RG replay outcome   unchanged
```

Structural measure:

```text
benchmark-local bbox containment implementations  -> 0
```

Counter-metric:

```text
new domain-specific Core concepts -> 0
```

A performance benchmark is unnecessary at this stage; the operators are constant
size comparisons and the primary risk is semantic duplication, not runtime.

## 9. Resulting architecture if TC2.0 passes

```text
Task / Provider scopes
        |
        v
existing normalized geometry / bbox representation
        |
        v
Core deterministic spatial relation operators
        |
        v
benchmark / adapter applicability proof
        |
        v
existing Task Context exact-scope assessment
```

This keeps the architectural subject as **Task Context**, while using the mature
GeoTask spatial kernel as the physical-world grounding layer.

## 10. Promotion verdict

```text
Generic problem repeated across independent domains       PASS
Physical/spatiotemporal specificity                       PASS
Deterministic implementation possible                     PASS
Existing Core layer naturally owns the operation          PASS
Requires new domain policy in Core                        NO
Requires new geometry/world-model subsystem               NO
Task Context native geometry contract already proven      NO
```

Therefore:

> **APPROVE TC2.0: add minimal rectangle scope-relation operators to the existing
> Core spatial kernel.**

> **HOLD TC2.1: do not yet redesign Task Context scope fields or make geometry
> applicability an implicit part of `assess_task_context()`.**
