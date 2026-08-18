# Task Context External Refinement Consumer Proof Plan v0.1

**Status:** Frozen test plan before implementation  
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
gap_requirement_ids            (obstacles)
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

## Measures

Primary:

- **Refinable Critical Gap Closure Rate** — the declared obstacle refinement gap closes after the provider returns a valid finer candidate.

Counter-metrics:

- **False Acquisition Count** — provider calls for non-refinement gaps must remain zero.
- **Unresolved Refinement Preservation** — if the provider returns another too-coarse candidate, Core must remain insufficient rather than pretending closure.
- **Reassessment Parity** — consumer final result must equal direct Core assessment over the same final candidate set.
- **Schema Delta** — target is zero new Core public objects / fields.
- **Provider Call Count** — exactly one call for exactly one refinable requirement in the reference success case.

## Promotion rule

If the proof succeeds with the current public objects:

> keep `ContextGap` / `RefinementRequest` schema promotion on HOLD.

If the proof cannot be implemented without parsing free text, guessing provider parameters, or reaching into Core internals:

> record the missing information precisely and use that failure as evidence for the smallest possible new contract.

## Ownership boundary

This reference consumer is Harness-neutral and lives outside Core.

Actual DeepSeek Harness / AgentReality integration belongs in the AgentReality adapter/extension layer, not in GeoTask Core.
