# GeoTask Task Context Engine v0.1

**Status:** architecture candidate  
**Date:** 2026-08-18  
**Purpose:** reframe GeoTask around task-adaptive spatiotemporal context without invalidating the existing deterministic Core.

## 1. Working definition

> **GeoTask 是 Agent 的时空任务上下文引擎。**
>
> **GeoTask is a spatiotemporal task-context engine for AI agents operating in the physical world.**

This is a product and research direction, not a claim that the current public Core already implements automatic context construction.

The current Core is strongest at representing and verifying **given** spatiotemporal task inputs. The next step is to help an Agent determine which physical-world information belongs in the task context, whether the context is sufficient, and whether more spatial or temporal detail is worth acquiring.

## 2. Root problem

Physical-world information is effectively unbounded, heterogeneous, multi-source, and multi-scale. A concrete task has limited time, data, computation, and human-attention budgets.

The problem is therefore not to maintain a complete real-time world model. It is:

> **For this task, at this place and time, what information matters, how much is enough, and how fine does it need to be?**

GeoTask should reduce context-preparation cost without hiding critical task conditions.

## 3. Scope

GeoTask is intended for physical-world tasks where results depend materially on object, place, time, state, rules, or scale, and where multiple heterogeneous sources must be composed under finite information cost.

Representative classes include:

- low-altitude mission planning and operational preparation;
- emergency and field-resource coordination;
- engineering, inspection, construction, and field operations;
- multi-scale spatial planning where local detail is acquired selectively.

GeoTask is not intended to become:

- a general coding/office Agent trust layer;
- a millisecond control loop for autonomous driving, robots, or flight control;
- a complete digital twin or universal real-time world model;
- a replacement for domain models, GIS engines, planning optimizers, or Systems of Record.

## 4. Four context questions

### 4.1 Relevance — what matters?

Determine which objects, spatial regions, time windows, rules, evidence, models, and constraints can materially affect the current task.

v0.1 principle: relevance may be declared explicitly. Automatic relevance discovery is a later capability and must be benchmarked before becoming authoritative.

### 4.2 Applicability — can this information be used here?

A data item, rule, evidence item, or model result may be valid in general but not applicable to the current object, spatial scope, temporal scope, operating state, or task.

Applicability should be evaluated from explicit scope metadata wherever possible. GeoTask must not invent an applicable scope that the source did not declare.

### 4.3 Sufficiency — do we know enough?

GeoTask should not pursue complete information. It should determine whether the currently selected context is sufficient for the requested task output under declared requirements and tolerances.

If context is insufficient, the system should expose a bounded context gap rather than silently continue.

### 4.4 Resolution — do we need to look more closely?

Finer spatial or temporal detail is not automatically better. Higher resolution costs more and may add noise.

The preferred rule is:

> **Use the coarsest resolution that is still sufficient for the task; refine only when resolution uncertainty can change the task outcome.**

v0.1 only represents and checks declared resolution requirements. Automatic decision-sensitive refinement remains a target capability.

## 5. Core flow

```text
Task
  ↓
Task Frame
  ↓
Context Requirements
  ↓
Candidate Context
  ↓
Relevance / Applicability checks
  ↓
Sufficiency / Resolution assessment
  ├── sufficient → Task Context
  └── gap → acquire / refine / review
```

The output is a bounded **Task Context**, not a complete World State.

## 6. Relationship to existing GeoTask assets

Existing Core assets remain valuable but change role:

- spatial objects, CRS, units, time and altitude semantics → context representation foundation;
- deterministic operators → context computation and local verification;
- Evidence / Unknown / Conflict → context quality and gap semantics;
- World State / Observation → optional bounded state snapshots when the task needs them;
- Impact Graph / incremental reevaluation → bounded context-change impact where declared dependencies exist;
- Control / Authorization → downstream action boundary, not the primary product identity;
- Artifact / Replay → reproducibility of how a Task Context and result were constructed.

World State is therefore a supporting representation, not the universal top-level abstraction for every GeoTask use case.

## 7. Minimum public contracts

The first engineering slice introduces three lightweight contracts.

### TaskFrame

Defines the task before context is selected:

- task id and goal;
- physical subject/object references;
- spatial scope;
- temporal scope;
- requested outputs;
- optional context budget.

### ContextRequirement

Declares one piece of context the task requires:

- what is needed and why;
- whether it is critical;
- applicable spatial/temporal scope;
- maximum acceptable spatial/temporal resolution;
- optional tolerance/metadata.

### ContextCandidate

Describes one available context input:

- source and requirement bindings;
- declared spatial/temporal scope;
- available spatial/temporal resolution;
- acquisition cost;
- metadata needed for explicit applicability checks.

A derived TaskContext records selected candidates, gaps, cost, and sufficiency state.

## 8. v0.1 deterministic baseline

The first Core implementation should remain deliberately small:

1. accept an explicit TaskFrame;
2. accept explicit ContextRequirements;
3. accept caller-selected ContextCandidates;
4. check requirement binding, scope compatibility, and declared resolution;
5. report critical gaps and refinement needs;
6. calculate declared acquisition cost and budget status;
7. never infer missing scope, relevance, source authority, or decision truth.

This is a contract-and-assessment baseline, not an automatic context search engine.

## 9. Benchmark direction

The Task Context Engine must eventually be evaluated against a baseline that loads all available data or relies on manually prepared context.

Primary metrics:

- **Critical Context Miss Rate:** critical conditions omitted from the task context;
- **Context Reduction Ratio:** irrelevant/unnecessary context removed;
- **Context Preparation Cost:** human time, data/API cost, latency, and computation;
- **Resolution Efficiency:** cost saved by avoiding unnecessary high-resolution processing;
- **Task Outcome Regret:** degradation caused by using the reduced context rather than a stronger reference context.

The optimization objective is conceptually:

```text
minimize context preparation cost
subject to critical context miss <= epsilon
```

No benchmark result should be presented as general physical-world decision accuracy unless the underlying domain data and outcome labels support that claim.

## 10. Reference scenario direction

The next Reference Scenario should start from an under-specified physical-world task rather than from an already-complete World State.

Recommended first scenario:

> A user asks an Agent to prepare a low-altitude delivery mission between A and B for a specified vehicle and time window.

The demonstration should show:

1. TaskFrame extraction;
2. explicit context requirements;
3. rejection of irrelevant or inapplicable context;
4. discovery of a critical context gap;
5. refinement only where required resolution is insufficient;
6. construction of a bounded Task Context;
7. handoff to an external route/risk/domain model;
8. trace of why each selected context item was needed.

GeoTask should not claim to perform real flight authorization or vehicle control in this public scenario.

## 11. Architecture invariants

- **Task first:** do not build a world model before knowing the task.
- **Bounded context:** represent only the part of the physical world required by the task.
- **Explicit scope:** do not infer spatial, temporal, object, or source applicability without a declared method.
- **Coarsest sufficient resolution:** refinement requires a task-related reason.
- **Unknown remains unknown:** a missing critical context item is a gap, not `false`.
- **Tool last:** GIS, models, maps, sensors, and Agent runtimes are replaceable providers/carriers.
- **No decision guarantee:** better context preparation does not transfer responsibility for the final domain decision to GeoTask.

## 12. Migration rule

This direction does not delete or rewrite existing v0.4.x/v0.5 capabilities. Existing public contracts remain stable unless a separate compatibility decision is recorded.

New context-engine capabilities should be introduced additively and validated in at least one Reference Scenario before README, package metadata, or public release notes claim that automatic task-context construction is implemented.
