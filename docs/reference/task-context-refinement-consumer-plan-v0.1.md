# Task Context External Refinement Consumer Proof v0.1

**Status:** Proof Complete / Schema Promotion HOLD  
**Date:** 2026-08-18

## 0. Verdict

The external-consumer proof passes at the tested boundary:

> A caller that retains the original `TaskFrame + ContextRequirement[]` can consume the existing `TaskContext.gap_requirement_ids` / `refinement_requirement_ids`, acquire additional candidates from an external provider, and reassess Task Context sufficiency without any new GeoTask Core public object or field.

Therefore:

```text
Refinable critical-gap closure      PASS
False acquisition                   0
Unresolved refinement preservation  PASS
Direct reassessment parity          PASS
Sunk acquisition cost preservation  PASS
Core code delta                     0
Core public schema delta            0
ContextGap / RefinementRequest       HOLD
```

This does **not** prove that a bare persisted `TaskContext` ids-only artifact is sufficient for a later asynchronous worker that no longer has the original requirement objects.

---

## 1. Problem

GeoTask has real spatial and temporal evidence for **Sufficiency-Guided Refinement**, but method evidence alone does not prove that the current public Task Context objects are sufficient across a component boundary.

The concrete question is:

> Can a caller outside `geotask_core` consume the existing `gap_requirement_ids` / `refinement_requirement_ids`, acquire additional context through a provider, and reassess to a sufficient Task Context without a new public `ContextGap` or `RefinementRequest` object?

---

## 2. Frozen Method

The external consumer retains the original:

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

---

## 3. Reference Scenario

Reuse the existing fictional low-altitude mission semantics:

```text
weather       usable
airspace      usable
obstacles     applicable but 100 m > required 10 m
poi_labels    optional / absent
```

Initial state:

```text
status                         insufficient
gap_requirement_ids            (obstacles, poi_labels)
refinement_requirement_ids     (obstacles)
```

A fictional external obstacle provider returns a 5 m candidate for the same task scope.

Final state:

```text
status                         sufficient_with_gaps
critical gaps                  none
refinement_requirement_ids     none
optional poi_labels gap        remains
```

The proof concerns context closure only; it does not authorize or assess a real flight.

---

## 4. Minimum Carrier

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

---

## 5. Proof Cases

### 5.1 Successful Critical-Gap Closure

Provider returns a 5 m obstacle candidate.

Observed/frozen expectations:

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

The consumer's final `TaskContext` is asserted equal to a direct call to `assess_task_context()` over the identical final candidate set. The consumer therefore contains no second sufficiency algorithm.

### 5.2 Too-Coarse Refinement Remains Unresolved

Provider returns 50 m while the requirement needs <=10 m.

Expected and tested:

```text
final status                  insufficient
obstacles gap                 preserved
obstacles refinement signal   preserved
```

The external consumer cannot turn acquisition activity into fake sufficiency.

### 5.3 Missing Non-Refinement Critical Gap Does Not Trigger Provider

Remove the airspace candidate while preserving the refinable obstacle gap.

Expected and tested:

```text
initial gaps                  airspace, obstacles, poi_labels
refinement ids                obstacles
provider calls                obstacles only
false airspace acquisition    0
final status                  insufficient
```

The obstacle refinement may close, but the unrelated missing critical airspace gap remains authoritative.

### 5.4 No Refinement Signal Means No Provider Call

When a 5 m obstacle candidate is already present:

```text
refinement ids        none
provider calls        0
final == initial      yes
```

This prevents a generic "always acquire more context" behavior from masquerading as refinement intelligence.

---

## 6. Measures

### Primary

**Refinable Critical Gap Closure Rate**

The one declared refinable critical requirement in the success scenario closes after the provider returns a valid finer candidate.

### Counter-metrics

**False Acquisition Count**

Provider calls for non-refinement gaps remain zero.

**Unresolved Refinement Preservation**

A still-too-coarse provider response preserves the gap and refinement signal.

**Reassessment Parity**

The consumer final result equals direct Core assessment over the same final candidate set.

**Schema Delta**

```text
new Core code                 0
new Core public objects       0
new TaskContext fields        0
```

**Provider Call Count**

Exactly one call for exactly one refinable requirement in the success case.

**Sunk Cost Preservation**

Previously acquired coarse context remains in the declared total acquisition cost.

---

## 7. Exact-Head Validation

Implementation head `917053e614ff68d40b33269650169d26da8325b3` passed combined `main` CI run #226:

```text
Python 3.10 pytest + RC attestation     PASS
Python 3.11 pytest + RC attestation     PASS
Python 3.12 pytest + RC attestation     PASS
Python 3.13 pytest + RC attestation     PASS
artifact roundtrip                      PASS
public boundary                         PASS
build / twine                           PASS
provider-neutral Adapter build          PASS
OpenAI Adapter build + smoke            PASS
public scan                             PASS
RC build / Reference Agent evidence     PASS
RC evidence merge / readiness audit     PASS
workflow                                completed / success
```

This document-close commit is intentionally revalidated separately so the final branch head remains bound to an exact CI result.

---

## 8. Applicability Boundary

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

---

## 9. Ownership Boundary

This reference consumer is Harness-neutral and lives outside Core.

Actual DeepSeek Harness / AgentReality integration belongs in the AgentReality adapter/extension layer, not in GeoTask Core.

GeoTask should expose context semantics and reassessment; it should not become an Agent job system, provider scheduler, or second Harness runtime.

---

## 10. Promotion Decision

At the tested synchronous/caller-retained boundary:

> **Keep `ContextGap` / `RefinementRequest` schema promotion on HOLD.**

The current public objects already support the required acquire -> reassess loop.

A future new contract must earn promotion from a concrete interoperability failure, not from architectural aesthetics.

The most plausible next trigger is an actual asynchronous Harness / AgentReality handoff in which the original `ContextRequirement[]` cannot remain available across the component boundary.
