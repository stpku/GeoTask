# GeoTask Architecture Manifesto v2

**Date:** 2026-08-18  
**Status:** architecture candidate for the next product phase  
**Supersedes for future direction:** Architecture Manifesto v1 positioning; existing public contracts remain compatible unless separately changed.

## 1. Working definition

> **GeoTask 是 Agent 的时空任务上下文引擎。**
>
> **GeoTask is a spatiotemporal task-context engine for AI agents operating in the physical world.**

GeoTask helps an Agent determine, for a concrete physical-world task:

- what information is relevant here and now;
- whether a data item, rule, model, or result is applicable to the current object/place/time;
- whether the currently available context is sufficient for the requested task output;
- whether finer spatial or temporal resolution is worth acquiring.

GeoTask does not promise complete knowledge of the world or correctness of the final domain decision.

## 2. Task first, world second

The top-level abstraction is **Task**, not a universal World State.

A task defines a bounded reason to inspect the physical world. Only the part of the world that is relevant to that task should enter the task context.

```text
Task
  ↓
Task Frame
  ↓
Relevant / Applicable Context
  ↓
Sufficiency / Resolution
  ↓
Task Context
  ↓
Agent / Domain Model / Tool
```

World State remains useful when a task needs a bounded state snapshot, but GeoTask does not require every task to build or continuously maintain a complete world model.

## 3. Physical-world specialization is a feature

GeoTask should remain specialized around physical-world spatiotemporal tasks. Its professional identity would be weakened by expanding into generic coding, office-agent, or broad AI-governance trust problems.

A task is a strong GeoTask candidate when its result depends materially on combinations of:

- physical objects or resources;
- location, region, route, height, or topology;
- time windows, temporal order, or update cadence;
- object/operational state;
- spatially or temporally scoped rules;
- heterogeneous data and models at different resolutions.

GeoTask is not the control loop for millisecond autonomous-driving, robot, or flight-control decisions. It may support a higher-level mission/task layer while dedicated control systems remain responsible for real-time execution.

## 4. The world is too large; context must be bounded

The physical world contains effectively unlimited potentially relevant information. A real task has finite acquisition cost, latency, computation, and human-attention budgets.

GeoTask therefore rejects the implicit objective “collect everything first.”

The preferred objective is:

> **Construct the minimum sufficient spatiotemporal context for the current task.**

Completeness is not an end in itself. Additional information is valuable only when it can reduce an important task uncertainty, satisfy a declared requirement, prevent a critical miss, or justify a necessary refinement.

## 5. Four context dimensions

### 5.1 Relevance

What can materially affect the current task?

Relevance narrows candidate objects, areas, time windows, rules, evidence, models, and constraints. Automatic relevance inference is not trusted merely because an LLM proposes it; the method and benchmark must be explicit.

### 5.2 Applicability

Can this information be used for this task?

A valid source may still be inapplicable because it covers the wrong object, location, time, state, scale, or operating condition. Applicability should rely on explicit scope metadata and declared operators rather than silent assumptions.

### 5.3 Sufficiency

Do we know enough to perform the next requested task step?

Missing information must remain a context gap. `Unknown` must not be coerced to `false`, and missing critical context must not be hidden by fluent Agent output.

### 5.4 Resolution

How fine must the task context be?

Finer is not automatically better. GeoTask prefers the coarsest sufficient spatial and temporal resolution and refines only where a declared task requirement or decision sensitivity justifies the cost.

## 6. Existing Core capabilities are foundations, not the product definition

The following existing capabilities remain important:

- canonical spatial/temporal objects, CRS, coordinate order, units, and boundary semantics;
- deterministic spatiotemporal operators;
- task/assertion representation;
- Evidence, provenance, unknown/conflict semantics;
- Observation and bounded World State snapshots;
- State Transition, Impact Graph, and incremental reevaluation;
- Artifact validation and deterministic replay;
- Control/Authorization boundaries.

Their role is reframed:

- object/space/time contracts ensure Task Context has computable semantics;
- Evidence and verification protect context quality;
- World State is one bounded context representation when state snapshots are required;
- Impact limits rework when relevant context changes;
- Control protects downstream action boundaries;
- Replay explains how the context and result were produced.

No existing Artifact is promoted to the universal center merely because it is mature.

## 7. Context is not a prompt dump

Task Context is not synonymous with all tokens visible to an LLM.

A GeoTask Task Context should be inspectable and bounded. Important items should preserve explicit object/scope/source/resolution semantics so that an Agent or domain model can understand why they were included and what they do not cover.

LLM context remains a delivery mechanism. GeoTask context is a task-level physical-world contract.

## 8. Tool result is not automatically task context

A map lookup, sensor reading, web result, model output, human note, or database record is a **Context Candidate** until its relevance and applicability to the task are established.

An external provider cannot make itself relevant or authoritative merely by asserting that it is.

## 9. Coarsest sufficient resolution

Spatial and temporal scale must not become an after-the-fact excuse for a poor result.

Resolution should be declared or selected before the downstream task result is accepted. Refinement must have an explicit reason, such as:

- the current resolution fails a task requirement;
- uncertainty at the current resolution can cross a task threshold;
- a critical local rule/data condition cannot be evaluated at the coarse scale.

If finer resolution cannot change the relevant task outcome within declared tolerance, refinement should stop.

## 10. Minimum sufficient context must be measurable

GeoTask must not prove value by feature count, Artifact count, GT number, or the size of a World State.

The next product phase should measure:

- Critical Context Miss Rate;
- Context Reduction Ratio;
- Context Preparation Cost;
- Resolution Efficiency;
- Task Outcome Regret;
- human override/rework where real reference outcomes exist.

A useful context engine should reduce preparation cost while keeping critical misses below an acceptable threshold.

## 11. Decision responsibility remains outside Core

Better context does not guarantee a correct decision.

Data can be wrong, models can fail, rules can be incomplete, objectives can be misspecified, and the future can remain uncertain. GeoTask must not turn contextual sufficiency into a claim of legal, operational, or professional responsibility.

The domain system and authorized human/organization remain responsible for the final decision and real-world action.

`eligible != authorized != executed != successful` remains a valid invariant, but it is a downstream boundary rather than GeoTask's primary identity.

## 12. Core and industry systems retain separate ownership

GeoTask Core owns generic task-context contracts and deterministic semantics. Industry systems own authoritative domain data, business objects, proprietary rules, professional models, workflows, and real actions.

When an industry System of Record already exists, GeoTask references or consumes bounded context from it rather than creating a competing truth database.

Cross-line Promotion Gate discipline remains in force: industry success is evidence for a reusable abstraction, not an automatic Core feature.

## 13. Next engineering proof

The next Reference Scenario should begin with an under-specified physical-world task and prove context construction rather than only state maintenance.

The initial candidate is a low-altitude mission-preparation task:

```text
user task
→ TaskFrame
→ explicit ContextRequirements
→ ContextCandidates
→ relevance/applicability checks
→ context gap / resolution refinement
→ bounded TaskContext
→ handoff to external route/risk model
```

The public Core may start with explicit caller-declared requirements and candidate bindings. Automatic search, relevance discovery, value-of-information optimization, and decision-sensitive adaptive resolution should be added only after a benchmark demonstrates that they improve task-context economics without increasing critical misses.

## 14. Architecture discipline

Default choices for the next phase:

- task-first over world-first;
- bounded context over complete world representation;
- explicit scope over silent inference;
- sufficient over complete;
- coarsest sufficient resolution over maximum resolution;
- measurable context cost over feature accumulation;
- deterministic checks where possible;
- unknown over fabricated certainty;
- additive compatibility over unnecessary rewrite;
- Tool last: Agent runtime, GIS engine, model provider, and domain system remain replaceable carriers.
