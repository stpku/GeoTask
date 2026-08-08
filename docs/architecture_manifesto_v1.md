# GeoTask Architecture Manifesto v1

**Date:** 2026-08-07  
**Status:** product/architecture positioning source

## 1. Three-layer positioning

GeoTask separates what exists today from what the project is building toward.

- **Current public fact:** GeoTask is an open verifiable spatiotemporal task protocol and deterministic Core for AI agents.
- **Near-term product goal:** compose the existing Evidence, World State, Verification Provider, Impact, Control and Artifact capabilities into a trusted world-state runtime reference implementation.
- **Long-term vision:** become a reusable trusted task/state infrastructure layer for high-consequence AI agents operating against changing physical-world state.

The long-term label **Trusted World-State Runtime** is a product direction, not a claim that the current public repository is already a complete production runtime.

## 2. The missing layer between Agent and reality

LLMs and Agent frameworks can interpret language, reason, plan and call tools. Those capabilities do not by themselves establish:

- what the current real-world state is;
- which facts are supported by which evidence;
- whether evidence is stale, conflicting or missing;
- which prior conclusions become invalid after state changes;
- whether a result is merely eligible, actually authorized, released, sent or executed.

GeoTask exists to make these distinctions explicit and machine-verifiable.

## 3. Context is not World State

An LLM context is information currently visible to a model. A World State is a formal representation with explicit object identity/reference, time, source/provenance, validity, version/revision and verification semantics.

A statement appearing in context does not make it a current world fact.

## 4. Tool result is not verified fact

An API, sensor, model or human response produces an Observation or candidate claim. Its output can be accepted into a task/world-state decision only under explicit source, validity, applicability and verification rules.

No provider may increase its own trust merely by asserting that its result is authoritative.

## 5. Unknown is not False

Missing or unverified evidence must remain explicit. GeoTask preserves fail-closed outcomes such as `unverifiable` and conflict states rather than coercing them into convenient booleans.

This is not an implementation detail. It is a safety and decision-quality invariant.

## 6. Change must propagate through declared dependency

GeoTask must answer not only “is the current result valid?” but also:

> When one observation, evidence item or state path changes, which claims, outputs, decisions, reports or controls must be reevaluated, and which unaffected results may be reused?

The target is bounded, explainable impact—not automatic global recomputation.

## 7. Eligibility is not execution

GeoTask keeps the following distinctions explicit:

```text
plan can be generated
≠ technical conditions satisfied
≠ evidence complete
≠ authorization conditions satisfied
≠ output eligible for release
≠ command sent
≠ real-world action executed
```

Public Core may verify and gate these states. It does not silently cross the boundary into production side effects.

## 8. Core and industry systems have different ownership

GeoTask Core owns generic contracts and deterministic verification semantics. Industry systems own their business objects, authoritative databases, proprietary rules, operational workflows and real writes/actions.

When an industry system already has a System of Record, GeoTask consumes bounded snapshots/references and produces verification/impact/control artifacts. It does not create a competing business truth.

Lowa-GT is the first planned industry reference integration under this rule.

### Cross-line Promotion Gate

GeoTask Core, Lowa Product and Lowa-GT Integration remain three independent lines: **Lowa Product owns business facts, Lowa-GT Integration validates boundaries/candidates, and GeoTask Core owns generic abstractions.** Successful Integration work is evidence for a Promotion Candidate, not an implicit Core change.

Any transfer of capability ownership across those lines requires the explicit [`Cross-Line Promotion Gate v0.1`](reference/cross-line-promotion-gate-v0.1.md). Normal consumption of an already-owned Core contract is not promotion; moving a schema, semantic rule, implementation responsibility or compatibility commitment into another line is. No passing demo, benchmark, GT number or Integration commit silently counts as `PROMOTE`.

## 9. Open capability, controlled trust

GeoTask should support providers, operators, packs and third-party capabilities, but an extension cannot directly announce final truth or authorization.

A trustworthy extension must declare evidence, method/version, applicable scope, validity, failure conditions, uncertainty and dependencies. GeoTask's trust/control layer remains responsible for evaluating whether the result is usable in the current task.

## 10. Product maturity is not GT count

GeoTask maintains two tracks:

- **Capability Track (GT):** proves individual technical capabilities.
- **Product Track (P0–P5):** measures architecture clarity, Reference Agent completeness, developer usability, industry reuse, external ecosystem validation and commercial validation.

GT42 does not imply P4 or P5 maturity. New GT numbers are justified only when an end-to-end product or real integration exposes a genuinely missing reusable primitive.

## 11. Near-term proof

The first end-to-end Reference Agent is a fictional facility-assessment-update workflow:

```text
new evidence
→ state update
→ verify conflict/freshness/missing evidence
→ bounded impact
→ bounded reevaluation
→ human review/control gate
→ report update becomes eligible
→ report remains unpublished until an external workflow actually performs the action
```

The first real industry proof will mirror the same chain in Lowa-GT in read-only/shadow mode.

## 12. Architecture discipline

When a proposed feature conflicts with this manifesto, the project must record an explicit architectural decision rather than silently weakening the boundary.

The default choices remain: deterministic where possible, explicit over inferred, fail-closed over optimistic, bounded over global, replayable over opaque, and eligible-not-executed over implied side effects.