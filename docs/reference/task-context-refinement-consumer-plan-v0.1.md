# Task Context External Refinement Consumer Proof Plan v0.1

**Status:** Implementation Complete / Combined CI Pending  
**Date:** 2026-08-18

## Problem

GeoTask now has real spatial and temporal evidence for **Sufficiency-Guided Refinement**, but method evidence alone does not prove that the current public Task Context objects are sufficient across a component boundary.

The concrete question is:

> Can a caller outside `geotask_core` consume the existing `gap_requirement_ids` / `refinement_requirement_ids`, acquire additional context through a provider, and reassess to a sufficient Task Context without a new public `ContextGap` or `RefinementRequest` object?

## Frozen method

The external consumer must retain the original:

```text
TaskFrame
ContextRequirement[]
selected ContextCandidate[]
```

It may inspect the returned `TaskContext`, but it may not reach into Core internals.

For each `refinement_requirement_id`:

```text
id
 -> resolve original ContextRequirement
 -> call external provider with TaskFrame + ContextRequirement
 -> receive ContextCandidate[]
 -> append newly acquired candidates
 -> call assess_task_context(...) again
```

The consumer must not automatically acquire for a `gap_requirement_id` that is **not** also a refinement requirement. Missing context and refinable context remain distinct.

## Reference scenario

Reuse the existing fictional low-altitude mission example:

```text
weather       usable
airspace      usable
obstacles     applicable but 100 m > required 10 m
poi_labels    optional / absent
```

Initial expected state:

```text
status                         insufficient
gap_requirement_ids            (obstacles, poi_labels)
refinement_requirement_ids     (obstacles)
```

A fictional external obstacle provider returns a 5 m candidate for the same task scope.

Expected final state:

```text
status                         sufficient_with_gaps
critical gaps                  none
refinement_requirement_ids     none
optional poi_labels gap        remains
```

The proof concerns context closure only; it does not authorize or assess a real flight.

## Implemented carrier

The reference consumer lives outside Core at:

```text
examples/task_context/refinement_consumer.py
```

It defines only:

```text
RefinementProvider
RefinementCycle
run_refinement_cycle(...)
```

It does not add a provider registry, scheduler, Agent loop, Harness dependency, or second context-selection algorithm.

The consumer resolves emitted requirement ids against the caller's original structured `ContextRequirement[]`; it never parses `what` / `reason` prose and never reads hidden Core state.

## Implemented proof cases

### 1. Successful critical-gap closure

The provider returns a 5 m obstacle candidate.

Expected evidence:

```text
provider call count                 1
provider call requirement           obstacles
false acquisition count             0
critical obstacle gap closed        yes
optional poi_labels gap preserved   yes
final refinement ids                none
final acquisition cost              6 credits
```

The original 100 m obstacle acquisition remains in the total cost. Refinement does not erase sunk context-preparation cost.

### 2. Too-coarse refinement remains unresolved

The provider returns 50 m while the requirement needs <=10 m.

Expected:

```text
final status                  insufficient
obstacles gap                 preserved
obstacles refinement signal   preserved
```

### 3. Missing non-refinement critical gap does not trigger provider

Remove the airspace candidate while preserving the refinable obstacle gap.

Expected:

```text
initial gaps                  airspace, obstacles, poi_labels
refinement ids                obstacles
provider calls                obstacles only
false airspace acquisition    0
final status                  insufficient
```

### 4. No refinement signal means no provider call

When a 5 m obstacle candidate is already present:

```text
refinement ids        none
provider calls        0
final == initial      yes
```

## Measures

Primary:

- **Refinable Critical Gap Closure Rate** — the declared obstacle refinement gap closes after the provider returns a valid finer candidate.

Counter-metrics:

- **False Acquisition Count** — provider calls for non-refinement gaps must remain zero.
- **Unresolved Refinement Preservation** — if the provider returns another too-coarse candidate, Core must remain insufficient rather than pretending closure.
- **Reassessment Parity** — consumer final result must equal direct Core assessment over the same final candidate set.
- **Schema Delta** — target is zero new Core public objects / fields.
- **Provider Call Count** — exactly one call for exactly one refinable requirement in the reference success case.
- **Sunk Cost Preservation** — previously acquired coarse context remains in the declared total acquisition cost.

## Promotion rule

If the proof succeeds with the current public objects:

> keep `ContextGap` / `RefinementRequest` schema promotion on HOLD.

If the proof cannot be implemented without parsing free text, guessing provider parameters, or reaching into Core internals:

> record the missing information precisely and use that failure as evidence for the smallest possible new contract.

## Applicability boundary

This proof is intentionally narrower than a generic asynchronous job protocol.

It proves only the boundary where the external consumer retains:

```text
TaskFrame
ContextRequirement[]
TaskContext
```

through the refinement cycle.

It does **not** prove that a bare persisted `TaskContext` artifact containing only requirement ids is sufficient for a later asynchronous worker that no longer has the original `ContextRequirement[]`.

That future boundary should be tested only when a real Harness / AgentReality / Lowa consumer requires it. If the original requirement objects cannot be preserved or re-resolved there, that failure may justify a structured `ContextGap` / `RefinementRequest` contract.

## Ownership boundary

This reference consumer is Harness-neutral and lives outside Core.

Actual DeepSeek Harness / AgentReality integration belongs in the AgentReality adapter/extension layer, not in GeoTask Core.

## Current implementation verdict before CI

```text
Core code changes             0
Core public schema changes    0
external consumer             implemented
success/counterexample tests  implemented
combined exact-head CI        pending
```
